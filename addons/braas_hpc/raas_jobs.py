# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# (c) IT4Innovations, VSB-TUO

import functools
import logging
import tempfile
import os
from pathlib import Path, PurePath
import typing
import json

################################
import time
################################

import bpy
from bpy.types import AddonPreferences, Operator, WindowManager, Scene, PropertyGroup, Panel
from bpy.props import StringProperty, EnumProperty, PointerProperty, BoolProperty, IntProperty

from bpy.types import Header, Menu

import pathlib
import json

import time

################################

from . import async_loop
from . import raas_server
from . import raas_pref
from . import raas_config
from . import raas_connection

################################
log = logging.getLogger(__name__)
################################
class JobTaskInfo:
    def __init__(self, job_cores, ClusterNodeTypeId, CommandTemplateId):
        self.job_cores = job_cores
        self.ClusterNodeTypeId = ClusterNodeTypeId
        self.CommandTemplateId = CommandTemplateId

async def CreateJobTask3Dep(context, 
                            token, 
                            job_task1: JobTaskInfo, 
                            job_task2: JobTaskInfo,
                            job_task3: JobTaskInfo,
                            FileTransferMethodId, 
                            ClusterId):

    blender_job_info_new = context.scene.raas_blender_job_info_new
    job_type = blender_job_info_new.job_type

    pref = raas_pref.preferences()
    preset = pref.cluster_presets[context.scene.raas_cluster_presets_index]    

    job = None
    username = preset.raas_da_username
    use_xorg = str(job_type == 'ORIGEEVEE' or job_type == 'ORIGWORKBENCH')
    # use_mpi1 = raas_config.GetDAQueueMPIProcs(job_task1.CommandTemplateId)
    use_mpi1 = context.scene.raas_config_functions.call_get_da_queue_mpi_procs(job_task1.CommandTemplateId)
    use_mpi2 = context.scene.raas_config_functions.call_get_da_queue_mpi_procs(job_task2.CommandTemplateId)
    use_mpi3 = context.scene.raas_config_functions.call_get_da_queue_mpi_procs(job_task3.CommandTemplateId)

    if blender_job_info_new.render_type == 'IMAGE':        
        job_arrays = None
        frame_start = blender_job_info_new.frame_current
        frame_end = blender_job_info_new.frame_current
        #frame_step = str(blender_job_info_new.frame_step)
        max_jobs = 1
        custom_job_arrays = ''
    else:
        frame_start = blender_job_info_new.frame_start
        frame_end = blender_job_info_new.frame_end
        #frame_step = str(blender_job_info_new.frame_step)       
        max_jobs = blender_job_info_new.max_jobs
        custom_job_arrays = blender_job_info_new.job_arrays
        # if use_mpi2 == 0:
        #     # job_arrays = '%d-%d:%d' % (blender_job_info_new.frame_start,
        #     #                            blender_job_info_new.frame_end, blender_job_info_new.frame_step)
        # else:
        #     # job_arrays = '%d-%d:%d' % (blender_job_info_new.frame_start,
        #     #                            blender_job_info_new.frame_end, blender_job_info_new.frame_step * use_mpi2)

        if len(custom_job_arrays) == 0:
            if max_jobs > (frame_end - frame_start + 1):
                max_jobs = (frame_end - frame_start + 1)        

            if max_jobs < 1:
                job_arrays = None
                max_jobs = 1
            else:
                job_arrays = '%d-%d' % (1, max_jobs)
        else:
            job_arrays = custom_job_arrays

    frame_start = str(frame_start)
    frame_end = str(frame_end)
    max_jobs = str(max_jobs)

    use_mpi1 = str(use_mpi1)
    use_mpi2 = str(use_mpi2)
    use_mpi3 = str(use_mpi3)

    blender_param = raas_connection.convert_path_to_linux(blender_job_info_new.blendfile)
    blender_version = raas_config.GetBlenderClusterVersion()

    job_walltime = blender_job_info_new.job_walltime * 60

    task1 = {
        "Name": blender_job_info_new.job_name,
        "MinCores": job_task1.job_cores,
        "MaxCores": job_task1.job_cores,
        "WalltimeLimit": 1800,
        "StandardOutputFile": 'stdout',
        "StandardErrorFile": 'stderr',
        "ProgressFile": 'stdprog',
        "LogFile": 'stdlog',
        "ClusterNodeTypeId":  job_task1.ClusterNodeTypeId,
        "CommandTemplateId": job_task1.CommandTemplateId,
        "Priority": 4,
        "EnvironmentVariables": [
            {
                "Name": "job_project",
                "Value": blender_job_info_new.job_project
            },
            {
                "Name": "job_email",
                "Value": blender_job_info_new.job_email
            },
            {
                "Name": "frame_start",
                "Value": frame_start
            },
            {
                "Name": "frame_end",
                "Value": frame_end
            },
            {
                "Name": "username",
                "Value": username
            },
            {
                "Name": "blender_version",
                "Value": blender_version
            },
            {
                "Name": "use_xorg",
                "Value": use_xorg
            },
            {
                "Name": "use_mpi",
                "Value": use_mpi1
            },
            {
                "Name": "allocation_name",
                "Value": blender_job_info_new.job_allocation
            },
            {
                "Name": "max_jobs",
                "Value": max_jobs
            },
            {
                "Name": "job_arrays",
                "Value": custom_job_arrays
            }, 
        ],
        "TemplateParameterValues": [
            {
                "CommandParameterIdentifier": "inputParam",
                "ParameterValue": blender_param
            }
        ]
    }

    task2 = {
        "Name": blender_job_info_new.job_name,
        "MinCores": job_task2.job_cores,
        "MaxCores": job_task2.job_cores,
        "WalltimeLimit": job_walltime,
        "StandardOutputFile": 'stdout',
        "StandardErrorFile": 'stderr',
        "ProgressFile": 'stdprog',
        "LogFile": 'stdlog',
        "ClusterNodeTypeId":  job_task2.ClusterNodeTypeId,
        "CommandTemplateId": job_task2.CommandTemplateId,
        "Priority": 4,
        "JobArrays": job_arrays,
        "DependsOn": [
                        task1
        ],
        "EnvironmentVariables": [
            {
                "Name": "job_project",
                "Value": blender_job_info_new.job_project
            },
            {
                "Name": "job_email",
                "Value": blender_job_info_new.job_email
            },
            {
                "Name": "frame_start",
                "Value": frame_start
            },
            {
                "Name": "frame_end",
                "Value": frame_end
            },
            {
                "Name": "blender_version",
                "Value": blender_version
            },
            {
                "Name": "use_xorg",
                "Value": use_xorg
            },
            {
                "Name": "use_mpi",
                "Value": use_mpi2
            },
            {
                "Name": "allocation_name",
                "Value": blender_job_info_new.job_allocation
            },
            {
                "Name": "username",
                "Value": username
            },
            {
                "Name": "max_jobs",
                "Value": max_jobs
            },
            {
                "Name": "job_arrays",
                "Value": custom_job_arrays
            }, 
        ],
        "TemplateParameterValues": [
            {
                "CommandParameterIdentifier": "inputParam",
                "ParameterValue": blender_param
            }
        ]
    }

    task3 = {
        "Name": blender_job_info_new.job_name,
        "MinCores": job_task3.job_cores,
        "MaxCores": job_task3.job_cores,
        "WalltimeLimit": job_walltime,
        "StandardOutputFile": 'stdout',
        "StandardErrorFile": 'stderr',
        "ProgressFile": 'stdprog',
        "LogFile": 'stdlog',
        "ClusterNodeTypeId":  job_task3.ClusterNodeTypeId,
        "CommandTemplateId": job_task3.CommandTemplateId,
        "Priority": 4,
        "DependsOn": [
                        task2
        ],
        "EnvironmentVariables": [
            {
                "Name": "job_project",
                "Value": blender_job_info_new.job_project
            },
            {
                "Name": "job_email",
                "Value": blender_job_info_new.job_email
            },
            {
                "Name": "frame_start",
                "Value": frame_start
            },
            {
                "Name": "frame_end",
                "Value": frame_end
            },
            {
                "Name": "blender_version",
                "Value": blender_version
            },
            {
                "Name": "use_xorg",
                "Value": use_xorg
            },
            {
                "Name": "use_mpi",
                "Value": use_mpi3
            },
            {
                "Name": "allocation_name",
                "Value": blender_job_info_new.job_allocation
            },
            {
                "Name": "max_jobs",
                "Value": max_jobs
            },
            {
                "Name": "job_arrays",
                "Value": custom_job_arrays
            },            
        ],
        "TemplateParameterValues": [
            {
                "CommandParameterIdentifier": "inputParam",
                "ParameterValue": blender_param
            }
        ]
    }

    job = {
        "Name":  blender_job_info_new.job_name,
        "MinCores": job_task1.job_cores,
        "MaxCores": job_task1.job_cores,
        "Priority": 4,
        "Project":  blender_job_info_new.job_project,
        "FileTransferMethodId":  FileTransferMethodId,
        "ClusterId":  ClusterId,
        "EnvironmentVariables":  None,
        "WaitingLimit": 0,
        "WalltimeLimit": job_walltime,
        "Tasks":  [
            task1,
            task2,
            task3
        ]
    }

    data = {
        "JobSpecification": job,
        "SessionCode": token
    }

    item = context.scene.raas_submitted_job_info_ext_new

    # Id : bpy.props.IntProperty(name="Id")
    item.Id = 0
    # Name : bpy.props.StringProperty(name="Name")
    item.Name = blender_job_info_new.job_name
    # State : bpy.props.EnumProperty(items=JobStateExt_items,name="State")
    item.State = "CONFIGURING"
    # Priority : bpy.props.EnumProperty(items=JobPriorityExt_items,name="Priority",default='AVERAGE')
    item.Priority = "AVERAGE"
    # Project : bpy.props.StringProperty(name="Project Name")
    item.Project = blender_job_info_new.job_project
    # CreationTime : bpy.props.StringProperty(name="Creation Time")
    # SubmitTime : bpy.props.StringProperty(name="Submit Time")
    # StartTime : bpy.props.StringProperty(name="Start Time")
    # EndTime : bpy.props.StringProperty(name="End Time")
    # TotalAllocatedTime : bpy.props.FloatProperty(name="totalAllocatedTime")
    # AllParameters : bpy.props.StringProperty(name="allParameters")
    item.AllParameters = raas_server.json_dumps(data)
    # Tasks: bpy.props.StringProperty(name="Tasks")

def CmdCreatePBSJob(context):
    """
        Creates a command that correctly submits PBS jobs.
    """
    item = context.scene.raas_submitted_job_info_ext_new
    data = json.loads(item.AllParameters)

    job = data['JobSpecification']
    job_name = job['Name']
    job_project = job['Project']
    tasks = job['Tasks']
    cluster_id = job['ClusterId']

    cmd = ''
    task_id = 0
    for task in tasks:
        cluster_node_type_id = task['ClusterNodeTypeId']
        command_template_id = task['CommandTemplateId']
        # cores, script = raas_config.GetDAQueueScript(cluster_id, command_template_id)
        cores, script = context.scene.raas_config_functions.call_get_da_queue_script(cluster_id, command_template_id)

        # pid_name, pid_queue, pid_dir = raas_config.GetCurrentPidInfo(context, raas_pref.preferences())
        pid_name, pid_queue, pid_dir = context.scene.raas_config_functions.call_get_current_pid_info(context, raas_pref.preferences())

        file = task['TemplateParameterValues'][0]['ParameterValue']

        # ncpus = int(cores)
        nodes = 1  # int(task['MaxCores'] / cores)

        envs = task['EnvironmentVariables']
        job_env = ''

        if len(envs) > 0:
            for env in envs:
                job_env = job_env + env['Name'] + '=' + env['Value'] + ','

        work_dir = raas_connection.get_direct_access_remote_storage(
            context) + '/' + job_name

        work_dir_stderr = work_dir + '/' + task['StandardErrorFile']
        work_dir_stdout = work_dir + '/' + task['StandardOutputFile']

        mm, ss = divmod(task['WalltimeLimit'], 60)
        hh, mm = divmod(mm, 60)

        walltime = str(hh) + ':' + str(mm) + ':' + str(ss)

        job_array = ''
        if 'JobArrays' in task:
            if not task['JobArrays'] is None:
                job_array = ' -J ' + task['JobArrays']

        depends_on = ''
        if 'DependsOn' in task:
            depends_on = ' -W depend=afterany:$_' + str(task_id - 1)
            job_env = job_env + 'depends_on=\"$_' + str(task_id - 1) + '\",'

        job_env = job_env + 'work_dir=' + work_dir

        custom_flags = ''
        if command_template_id in [16, 26, 17, 27]:  # eevee on barbora or karolina
            custom_flags += ' -l xorg=True '

        if cluster_id in [7]: # POLARIS
            custom_flags += ' -l filesystems=home:eagle '

        if cluster_id in [8]: # AURORA
            custom_flags += ' -l filesystems=flare '

        #pid = raas_config.GetDAOpenCallProject(pid_name)
        pid = context.scene.raas_config_functions.call_get_da_open_call_project(pid_name)

        ## -P \"' + job_project +
        cmd = cmd + '_' + str(task_id) + '=$(echo \' ' + script + ' ' + file + ' \' | qsub ' + \
            ' -A ' + pid + ' -v ' + \
            job_env + ' -l select=' + str(nodes) + \
            ' -N \"' + job_project + '\" -l walltime=' + walltime + ' -e ' + work_dir_stderr + \
            ' -o ' + work_dir_stdout + ' -q ' + pid_queue + job_array + \
                    depends_on + custom_flags + ');echo $_' + str(task_id) + ';'

        task_id = task_id + 1

    print(cmd)
    return cmd


def CmdCreateSLURMJob(context):
    """Creates a command to submit a Slurm job on cluster.

    Args:
        context (_type_): Blender context.

    Returns:
        str: Slurm command.
    """
    item = context.scene.raas_submitted_job_info_ext_new
    data = json.loads(item.AllParameters)

    job = data['JobSpecification']
    job_name = job['Name']
    job_project = job['Project']
    tasks = job['Tasks']
    cluster_id = job['ClusterId']

    cmd = ''
    task_id = 0
    for task in tasks:
        cluster_node_type_id = task['ClusterNodeTypeId']
        command_template_id = task['CommandTemplateId']
        #cores, script = raas_config.GetDAQueueScript(cluster_id, command_template_id)
        cores, script = context.scene.raas_config_functions.call_get_da_queue_script(cluster_id, command_template_id)

        # pid_name, pid_queue, pid_dir = raas_config.GetCurrentPidInfo(context, raas_pref.preferences())
        pid_name, pid_queue, pid_dir = context.scene.raas_config_functions.call_get_current_pid_info(context, raas_pref.preferences())

        file = task['TemplateParameterValues'][0]['ParameterValue']

        # ncpus = int(cores)
        nodes = 1  # int(task['MaxCores'] / cores)

        envs = task['EnvironmentVariables']
        job_env = ''

        if len(envs) > 0:
            for env in envs:
                job_env = job_env + env['Name'] + '=' + env['Value'] + ','

        work_dir = raas_connection.get_direct_access_remote_storage(
            context) + '/' + job_name

        work_dir_stderr = work_dir + '/' + task['StandardErrorFile']
        work_dir_stdout = work_dir + '/' + task['StandardOutputFile']

        mm, ss = divmod(task['WalltimeLimit'], 60)
        hh, mm = divmod(mm, 60)

        walltime = str(hh) + ':' + str(mm) + ':' + str(ss)

        job_array = ''
        if 'JobArrays' in task:
            if not task['JobArrays'] is None:
                job_array = '--array=' + task['JobArrays']

        depends_on = ''
        if 'DependsOn' in task:
            depends_on = ' --dependency=afterok:${_' + str(task_id - 1) + '##* }'
            job_env = job_env + 'depends_on=\"$_' + str(task_id - 1) + '\",'

        job_env = job_env + 'work_dir=' + work_dir

        xorg_true = ''
        if command_template_id in [16, 26, 17, 27]:  # eevee on barbora or karolina
            xorg_true = ' --comment="use:xorg=True" '

        add_resources = ''  # gpu or fpga, not cpu
        if command_template_id in [14, 16, 17, 24, 26, 27, 34, 36, 37, 44, 46, 47]:  # Barbora/Karolina/Leonardo, gpu and eevee
            add_resources = ' --gres=gpu:1'  # fixed number of GPUs

        if 'gpu' in pid_queue and context.scene.raas_blender_job_info_new.cluster_type == 'KAROLINA':
            add_resources += ' --gpus 1'  # fixed number of GPUs

        if context.scene.raas_blender_job_info_new.cluster_type == 'MARENOSTRUM5ACC':
            add_resources += ' -c 20 --gres=gpu:1'  # fixed number of GPUs

        if context.scene.raas_blender_job_info_new.cluster_type == 'MARENOSTRUM5ACC' or context.scene.raas_blender_job_info_new.cluster_type == 'MARENOSTRUM5GPP':
            add_resources += ' -q ' + pid_queue  # fix QoS

        cmd = cmd + '_' + str(task_id) + '=$(echo \' ' + script + ' ' + file + ' \' | sbatch --account ' + \
            raas_config.GetDAOpenCallProject(pid_name) + ' --export=' + job_env + ' --nodes=' + \
            str(nodes) + ' --job-name \"' + job_project + '\" --time=' + walltime + ' --partition=' + pid_queue + \
            add_resources + ' ' + job_array + ' --error=' + work_dir_stderr + ' --output=' + work_dir_stdout + \
            depends_on + xorg_true + ' ' + script + ' ' + file + '); echo ${_' + str(task_id) + '##* };'

        task_id = task_id + 1

    return cmd

def CmdCreateJob(context):
    #scheduler = raas_config.GetSchedulerFromContext(context)
    scheduler = context.scene.raas_config_functions.call_get_scheduler_from_context(context)


    if scheduler == 'SLURM':
        return CmdCreateSLURMJob(context)
    elif scheduler == 'PBS':
        return CmdCreatePBSJob(context)
    else:
        raise ValueError("Unknown scheduler type: {}".format(scheduler))


def CmdCreateStatPBSJobFile(context, pbs_jobs):
    """
        Creates a command to checks PBS jobs.
    """
    item = context.scene.raas_submitted_job_info_ext_new
    data = json.loads(item.AllParameters)

    job = data['JobSpecification']
    job_name = job['Name']

    cmd = ''

    pbs_jobs = pbs_jobs.split('\n')
    pbs_job = pbs_jobs[1]

    if len(pbs_job) > 0:
        job_log = raas_connection.get_direct_access_remote_storage(
            context) + '/' + job_name + '.job'
        cmd = cmd + 'qstat -fx ' + pbs_job + ' > ' + job_log + ';'        

    return cmd


def CmdCreateStatSLURMJobFile(context, slurm_jobs):
    """Creates a command that requests job's status on cluster and writes it to a particular file.

    Args:
        context (_type_): Blender context.
        slurm_jobs (str): Slurm jobs (their IDs) in a string, divided by '\n'.

    Returns:
        str: Command.
    """
    item = context.scene.raas_submitted_job_info_ext_new
    data = json.loads(item.AllParameters)

    job = data['JobSpecification'] 
    job_name = job['Name']

    cmd = ''

    slurm_jobs = slurm_jobs.split('\n')  # e,g., '2752\n2753\n2754\n'
    slurm_job = slurm_jobs[1]  # avoid the init and finish scripts

    if len(slurm_jobs) > 0:
        job_log = raas_connection.get_direct_access_remote_storage(
            context) + '/' + job_name + '.job'
        # grep -v omits logging of such as slurmID.batch tasks
        cmd = cmd + 'sacct -j ' + slurm_job + ' --format=JobID%20,Jobname%50,state,Submit,start,end | grep -v "\." > ' \
            + job_log + ';'

    return cmd

def CmdCreateStatJobFile(context, slurm_jobs):
    #scheduler = raas_config.GetSchedulerFromContext(context)
    scheduler = context.scene.raas_config_functions.call_get_scheduler_from_context(context)

    if scheduler == 'SLURM':
        return CmdCreateStatSLURMJobFile(context, slurm_jobs)
    elif scheduler == 'PBS':
        return CmdCreateStatPBSJobFile(context, slurm_jobs)
    else:
        raise ValueError("Unknown scheduler type: {}".format(scheduler))


########################################################################################
def slurm_map_slurm_status(slurm_status):
    """
    Maps Slurm statuses to the inner ones.
    Args:
        slurm_status (_str_): _Slurm status._

    Returns:
        _int_: _Inner status code._
    """

    # JobStateExt_items = [
    #     ("CONFIGURING", "Configuring", "", 1),
    #     ("SUBMITTED", "Submitted", "", 2),
    #     ("QUEUED", "Queued", "", 4),
    #     ("RUNNING", "Running", "", 8),
    #     ("FINISHED", "Finished", "", 16),
    #     ("FAILED", "Failed", "", 32),
    #     ("CANCELED", "Canceled", "", 64),
    # ]
    # See https://docs.it4i.cz/general/slurm-job-submission-and-execution/#quick-overview-of-common-batch-job-options
    status = 1  #  "CONFIGURING"
    if slurm_status == 'RUNNING' \
        or slurm_status == 'COMPLETING' \
            or slurm_status == 'SUSPENDED' \
                or slurm_status == 'RESIZING' \
                    or slurm_status == 'STAGE_OUT':
        status = 8
    elif slurm_status == 'PENDING' \
        or slurm_status == 'CONFIGURING' \
            or slurm_status == 'REQUEUE_HOLD' \
                or slurm_status == 'REQUEUED' \
                    or slurm_status == 'REQUEUE_FED':
        status = 4
    elif slurm_status == 'CANCELLED' or slurm_status == 'REVOKED':
        status = 64
    elif slurm_status == 'COMPLETED':
        status = 16
    else:
        status = 32  # Failed
    
    return status


def slurm_helper_raas_dict_jobs(id, name, project, cluster_name, state = None):
    """_Creates a dictionary and fills it with chosen task details_.

    Args:
        id (_int_): _Task inner ID_.
        name (_str_): _Full task name_.
        project (_str_): _Inner task name_.
        cluster_name (_str_): _Cluster name_.
        state (_str_, optional): _Task status_. Defaults to None.

    Returns:
        _dict_: _Task dictionary._
    """
    item = {}
    item['Id'] = id    
    item['Name'] = name
    item['Project'] = project
    item['ClusterName'] = cluster_name
    if state is not None:
        item['State'] = state
    return item

def slurm_helper_read_slurm_job_array(lines):
    """_Parses lines and calculates the status of the job array_.

    Args:
        lines (_list_): _Lines to read and parse_.

    Returns:
        _tuple_: _Tuple of the calculated status and a number of read lines_.
    """
    index = 0
    line = lines[index]  # Get the first line and parse it
    elements = line.split()
    slurm_id = elements[1].split('.')  # list
    job_statuses = []
    out_of_range = False

    while(not out_of_range \
            and "JobID" not in elements[1] \
                and "----" not in elements[1] \
                    and len(slurm_id[0].split('_')) == 2 \
                        and len(elements) == 7): 
        if len(slurm_id) != 2:  # For sure, if there is redundant slurm_id.batch or slurm_id.extern
            # Get job status
            job_statuses.append(elements[3])
        # Get a next line and read slurmId
        index += 1
        try:
            line = lines[index]  # may throw index error
            elements = line.split()
            slurm_id = elements[1].split('.') # may throw index error when a blank line is read
        except IndexError:
            out_of_range = True
            

    # Process job_statuses
    final_status = 1
    if 'FAILED' in job_statuses \
        or 'NODE_FAIL' in job_statuses \
            or 'OUT_OF_MEMORY' in job_statuses \
                or 'PREEMPTED' in job_statuses \
                    or 'TIMEOUT' in job_statuses \
                    or 'SIGNALING' in job_statuses:
        final_status = 32  # Failed
    elif 'CANCELLED' in job_statuses or 'REVOKED' in job_statuses:
        final_status = 64
    elif 'RUNNING' in job_statuses:
        final_status = 8
    elif 'PENDING' in job_statuses or 'REQUEUED' in job_statuses or 'CONFIGURING' in job_statuses:
        final_status = 4
    # converting a list to a set removes all duplicate values - anything greater than 1 is wrong    
    elif 'COMPLETED' == job_statuses[0] and len(set(job_statuses)) == 1:
        final_status = 16
        
    return final_status, index

def slurm_parse_slurm_job_lines(output, cluster_type):
    """Parse Slurm job output lines into job data structures.
    
    Args:
        output: Raw command output
        cluster_type: Type of cluster
        
    Returns:
        List of job dictionaries
    """
    lines = [line for line in output.split('\n') if line.strip()]
    if not lines:
        return []
    
    jobs_data = []
    jobs_dict = {}
    job_index = 0
    line_idx = 0
    
    while line_idx < len(lines):
        line = lines[line_idx]
        elements = line.split()
        
        if len(elements) < 2:
            line_idx += 1
            continue
            
        try:
            job_name = elements[0].split(".")[0]
            slurm_id_parts = elements[1].split('.')
        except IndexError:
            line_idx += 1
            continue
        
        # Skip header and separator lines
        if slurm_is_header_or_separator_line(elements):
            line_idx += 1
            continue
            
        # Process different types of job entries
        job_data, lines_consumed = slurm_process_job_entry(
            lines[line_idx:], job_name, elements, slurm_id_parts, 
            cluster_type, jobs_dict, job_index
        )
        
        if job_data:
            if job_name not in jobs_dict:
                jobs_dict[job_name] = job_data
                jobs_data.append(job_data)
                job_index += 1
            else:
                # Update existing job data
                jobs_dict[job_name].update(job_data)
        
        line_idx += lines_consumed

    return jobs_data


def slurm_is_header_or_separator_line(elements):
    """Check if line is a header or separator line."""
    return (len(elements) > 1 and 
            ("JobID" in elements[1] or "----" in elements[1]))


def slurm_process_job_entry(lines, job_name, elements, slurm_id_parts, cluster_type, jobs_dict, job_index):
    """Process a single job entry and return job data and lines consumed.
    
    Returns:
        Tuple of (job_data_dict, lines_consumed)
    """
    if len(elements) < 7:
        return None, 1
    
    # Check for job arrays
    if len(slurm_id_parts[0].split('_')) > 1:
        return slurm_process_job_array(lines, job_name, elements, cluster_type, job_index)
    
    # Check for regular job entries
    if (len(slurm_id_parts) == 1 and len(elements) == 7 and
        "JobID" not in elements[1] and "----" not in elements[1]):
        return slurm_process_regular_job(job_name, elements, cluster_type, job_index), 1
    
    # Check for submitted jobs (lines with only separators)
    if slurm_is_separator_only_line(elements, lines):
        return slurm_process_submitted_job(job_name, elements, cluster_type, job_index), 1
    
    return None, 1


def slurm_process_job_array(lines, job_name, elements, cluster_type, job_index):
    """Process job array entries."""
    final_status, lines_consumed = slurm_helper_read_slurm_job_array(lines)
    
    project_name = elements[2] if len(elements) > 2 else job_name.split('-')[-1]
    job_data = slurm_helper_raas_dict_jobs(job_index, job_name, project_name, cluster_type, final_status)
    
    # Add timing information if available
    if len(elements) >= 7:
        job_data.update({
            'CreationTime': elements[4],
            'SubmitTime': elements[4],
            'StartTime': elements[5],
            'EndTime': elements[6]
        })
    
    return job_data, lines_consumed


def slurm_process_regular_job(job_name, elements, cluster_type, job_index):
    """Process regular job entries."""
    status = slurm_map_slurm_status(elements[3])
    project_name = elements[2]
    
    job_data = slurm_helper_raas_dict_jobs(job_index, job_name, project_name, cluster_type, status)
    job_data.update({
        'CreationTime': elements[4],
        'SubmitTime': elements[4],
        'StartTime': elements[5],
        'EndTime': elements[6]
    })
    
    return job_data


def slurm_process_submitted_job(job_name, elements, cluster_type, job_index):
    """Process submitted job entries (jobs that haven't started yet)."""
    # Extract project name from job name
    name_parts = job_name.split('-')
    if len(name_parts) >= 4:
        project_name = '-'.join(name_parts[4:])  # Everything after the timestamp and ID
    else:
        project_name = job_name
    
    return slurm_helper_raas_dict_jobs(job_index, job_name, project_name, cluster_type, 2)  # SUBMITTED


def slurm_is_separator_only_line(elements, lines):
    """Check if current line contains only separators and next line is different job."""
    if len(elements) < 2:
        return False
        
    # Check if most elements contain separators
    separator_count = sum(1 for e in elements[1:] if "----" in e)
    has_separators = separator_count > len(elements[1:]) // 2
    
    if not has_separators or len(lines) < 2:
        return False
    
    # Check if next line is a different job
    next_elements = lines[1].split()
    if len(next_elements) < 1:
        return False
        
    current_job = elements[0].split('.')[0]
    next_job = next_elements[0].split('.')[0]
    
    return current_job != next_job

#########################################################################################

def update_job_list(context, jobs_data):
    """Update the UI job list with parsed job data."""
    context.scene.raas_list_jobs.clear()
    
    # Add jobs in reverse order (newest first)
    for job_data in reversed(jobs_data):
        item = context.scene.raas_list_jobs.add()
        raas_server.fill_items(item, job_data)
    
    # Ensure index is valid
    max_index = len(context.scene.raas_list_jobs) - 1
    if context.scene.raas_list_jobs_index > max_index:
        context.scene.raas_list_jobs_index = max_index


#########################################################################################

def pbs_parse_pbs_job_lines(output, cluster_type):
    """Parse PBS job output lines into job data structures.
    
    Args:
        output: Raw command output
        cluster_type: Type of cluster
        
    Returns:
        List of job dictionaries
    """
    lines = [line for line in output.split('\n') if line.strip()]
    if not lines:
        return []
    
    jobs_data = []
    jobs_dict = {}
    job_index = 0
    
    for line in lines:
        if not line.strip():
            continue
            
        # Extract job name and property
        parts = line.split(':', 1)
        if len(parts) < 2:
            continue
            
        job_file = parts[0]
        job_name = job_file.replace('.job', '')

        property_line = ''
        property_line = parts[1].strip() #+ ' ' + parts[2].strip()
        
        # Initialize job if not exists
        if job_name not in jobs_dict:
            jobs_dict[job_name] = pbs_create_pbs_job_dict(job_index, job_name, cluster_type)
            jobs_data.append(jobs_dict[job_name])
            job_index += 1
        
        job_data = jobs_dict[job_name]
        
        # Parse different properties
        pbs_parse_pbs_property(job_data, property_line)
    
    return jobs_data


def pbs_create_pbs_job_dict(job_index, job_name, cluster_type):
    """Create initial PBS job dictionary."""
    # Extract project name from job name (after timestamp)
    name_parts = job_name.split('-')
    if len(name_parts) >= 4:
        project_name = '-'.join(name_parts[3:])
    else:
        project_name = job_name
    
    return {
        'Id': job_index,
        'Name': job_name,
        'Project': project_name,
        'ClusterName': cluster_type,
        'State': 1,  # Default to CONFIGURING
        'CreationTime': '',
        'SubmitTime': '',
        'StartTime': '',
        'EndTime': ''
    }


def pbs_parse_pbs_property(job_data, property_line):
    """Parse a single PBS property line and update job data."""
    
    if property_line.startswith('Job Id:'):
        # Extract PBS job ID
        job_id = property_line.split('Job Id:')[1].strip()
        job_data['PBS_JobId'] = job_id
        
    elif property_line.startswith('Job_Name ='):
        # Extract job name
        job_name = property_line.split('Job_Name =')[1].strip()
        job_data['PBS_JobName'] = job_name
        
    elif property_line.startswith('job_state ='):
        # Extract and map job state
        state = property_line.split('job_state =')[1].strip()
        job_data['State'] = pbs_map_pbs_status(state)
        
    elif property_line.startswith('ctime ='):
        # Creation time
        ctime = property_line.split('ctime =')[1].strip()
        job_data['CreationTime'] = ctime
        job_data['SubmitTime'] = ctime  # PBS uses ctime as submit time
        
    elif property_line.startswith('qtime ='):
        # Queue time (when job was queued)
        qtime = property_line.split('qtime =')[1].strip()
        job_data['StartTime'] = qtime
        
    elif property_line.startswith('mtime ='):
        # Modification time (often when job finished)
        mtime = property_line.split('mtime =')[1].strip()
        # if len(job_data['StartTime']) == 0:
        #     job_data['StartTime'] = mtime
        
        if job_data['State'] == 16:  # FINISHED
            job_data['EndTime'] = mtime
        
    # elif property_line.startswith('exec_host ='):
    #     # Execution host (indicates job started)
    #     exec_host = property_line.split('exec_host =')[1].strip()
    #     job_data['PBS_ExecHost'] = exec_host
    #     # If we have exec_host, job has started
    #     if not job_data.get('StartTime'):
    #         job_data['StartTime'] = job_data.get('SubmitTime', '')
            
    elif property_line.startswith('queue ='):
        # Queue name
        queue = property_line.split('queue =')[1].strip()
        job_data['PBS_Queue'] = queue
        
    elif property_line.startswith('Account_Name ='):
        # Account/Project name
        account = property_line.split('Account_Name =')[1].strip()
        job_data['PBS_Account'] = account
        
    elif property_line.startswith('resources_used.walltime ='):
        # Wall time used
        walltime = property_line.split('resources_used.walltime =')[1].strip()
        job_data['PBS_WalltimeUsed'] = walltime
        
    elif property_line.startswith('resources_used.ncpus ='):
        # Number of CPUs used
        ncpus = property_line.split('resources_used.ncpus =')[1].strip()
        job_data['PBS_NCpusUsed'] = ncpus


def pbs_map_pbs_status(pbs_status):
    """Map PBS job states to internal status codes.
    
    PBS job states:
    - Q: Queued
    - R: Running
    - H: Held
    - E: Exiting
    - F: Finished
    - C: Completed
    - S: Suspended
    - T: Transiting
    - W: Waiting
    
    Args:
        pbs_status: PBS status code
        
    Returns:
        Internal status code
    """
    # Internal status codes:
    # 1: CONFIGURING
    # 2: SUBMITTED  
    # 4: QUEUED
    # 8: RUNNING
    # 16: FINISHED
    # 32: FAILED
    # 64: CANCELED
    
    status_map = {
        'Q': 4,   # QUEUED
        'H': 4,   # QUEUED (held)
        'W': 4,   # QUEUED (waiting)
        'R': 8,   # RUNNING
        'S': 8,   # RUNNING (suspended, but still allocated)
        'T': 8,   # RUNNING (transiting)
        'E': 8,   # RUNNING (exiting)
        'C': 16,  # FINISHED (completed)
        'F': 16,  # FINISHED
    }
    
    return status_map.get(pbs_status.upper(), 1)  # Default to CONFIGURING