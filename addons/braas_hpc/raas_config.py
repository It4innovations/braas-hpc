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

"""RaaS config."""

import bpy

Cluster_items_dict = {
    "BARBORA": "Barbora",
    "KAROLINA": "Karolina",
    "LUMI": "Lumi",
    "LEONARDO": "Leonardo",
    "MARENOSTRUM5GPP": "MareNostrum 5 GPP",
    "MARENOSTRUM5ACC": "MareNostrum 5 ACC",
    "MARENOSTRUM5DATA": "MareNostrum 5 (Data Transfer)",
    "POLARIS": "Polaris",
    "AURORA": "Aurora",
    "VISTA": "Vista",
    "FRONTERA": "Frontera",
    "CS": "IT4I Complementary Systems",
}

Cluster_items = [
    ("BARBORA", "Barbora", ""),
    ("KAROLINA", "Karolina", ""),
    ("LUMI", "Lumi", ""),
    ("LEONARDO", "Leonardo", ""),
    ("MARENOSTRUM5GPP", "MareNostrum 5 GPP", ""),
    ("MARENOSTRUM5ACC", "MareNostrum 5 ACC", ""),
    ("MARENOSTRUM5DATA", "MareNostrum 5 (Data Transfer)", ""),
    ("POLARIS", "Polaris", ""),
    ("AURORA", "Aurora", ""),
    ("VISTA", "Vista", ""),
    ("FRONTERA", "Frontera", ""),
    ("CS", "IT4I Complementary Systems", ""),
]

## Partitions available on Barbora
Barbora_partitions = [
    ("qcpu", "qcpu", ""),
    ("qgpu", "qgpu", ""),
    ("qcpu_biz", "qcpu_biz", ""),
    ("qgpu_biz", "qgpu_biz", ""),
    ("qcpu_exp", "qcpu_exp", ""),
    ("qgpu_exp", "qgpu_exp", ""),
    ("qcpu_free", "qcpu_free", ""),
    ("qgpu_free", "qgpu_free", ""),
    ("qcpu_long", "qcpu_long", ""),
    ("qcpu_preempt", "qcpu_preempt", ""),
    ("qgpu_preempt", "qgpu_preempt", ""),
    ("qdgx", "qdgx", ""),
    ("qfat", "qfat", ""),
    ("qviz", "qviz", "")
]

## Partitions available on Karolina
Karolina_partitions = [
    ("qcpu", "qcpu", ""),
    ("qgpu", "qgpu", ""),
    ("qcpu_biz", "qcpu_biz", ""),
    ("qgpu_biz", "qgpu_biz", ""),
    ("qcpu_exp", "qcpu_exp", ""),
    ("qgpu_exp", "qgpu_exp", ""),
    ("qcpu_free", "qcpu_free", ""),
    ("qgpu_free", "qgpu_free", ""),
    ("qcpu_long", "qcpu_long", ""),
    ("qcpu_preempt", "qcpu_preempt", ""),
    ("qgpu_preempt", "qgpu_preempt", ""),
    ("qfat", "qfat", ""),
    ("qviz", "qviz", "")
]

## Partitions available on Lumi (partitions by node only)
Lumi_partitions = [
    ("standard-g", "standard-g (LUMI-G)", ""),  # Lumi-G
    ("standard", "standard (LUMI-C)", "")  # Lumi-C
]

## Partitions available on Leonardo
Leonardo_partitions = [
    ("boost_usr_prod", "boost_usr_prod", ""),
]

Marenostrum5gpp_partitions = [
    ("gp_bsccase", "gp_bsccase", ""),
    ("gp_bsccs", "gp_bsccs", ""),
    ("gp_bsces", "gp_bsces", ""),
    ("gp_bscls", "gp_bscls", ""),
    ("gp_data", "gp_data", ""),
    ("gp_debug", "gp_debug", ""),
    ("gp_ehpc", "gp_ehpc", ""),
    ("gp_hbm", "gp_hbm", ""),
    ("gp_interactive", "gp_interactive", ""),
    ("gp_resa", "gp_resa", ""),
    ("gp_resb", "gp_resb", ""),
    ("gp_resc", "gp_resc", ""),
    ("gp_training", "gp_training", ""),
]

Marenostrum5acc_partitions = [
    ("acc_bsccase", "acc_bsccase", ""),
    ("acc_bsccs", "acc_bsccs", ""),
    ("acc_bsces", "acc_bsces", ""),
    ("acc_bscls", "acc_bscls", ""),
    ("acc_debug", "acc_debug", ""),
    ("acc_ehpc", "acc_ehpc", ""),
    ("acc_interactive", "acc_interactive", ""),
    ("acc_resa", "acc_resa", ""),
    ("acc_resb", "acc_resb", ""),
    ("acc_resc", "acc_resc", ""),
    ("acc_training", "acc_training", ""),
]

Marenostrum5data_partitions = [
]

Polaris_partitions = [
    ("debug", "debug", ""),
    ("debug-scaling", "debug-scaling", ""),
    ("prod", "prod", ""),    
    ("preemptable", "preemptable", ""),
    ("demand", "demand", ""),
]

Aurora_partitions = [
    ("debug", "debug", ""),
    ("debug-scaling", "debug-scaling", ""),
    ("prod", "prod", ""),
]

## Partitions available on VISTA
Vista_partitions = [
    ("gh", "gh", ""),
    ("gh-dev", "gh-dev", ""),
]

Frontera_partitions = [
    ("small", "small", ""),
    ("development", "development", ""),
    ("flex", "flex", ""),
]

Cs_partitions = [  
    ("p00-arm", "p00-arm", ""),
    ("p01-arm", "p01-arm", ""),
    ("p02-intel", "p02-intel", ""),
    ("p03-amd", "p03-amd", ""),
    ("p04-edge", "p04-edge", ""),
    ("p05-synt", "p05-synt", ""),
    ("p06-arm", "p06-arm", ""),
    ("p07-power", "p07-power", ""),
    ("p08-amd", "p08-amd", ""),
    ("p10-intel", "p10-intel", ""),
    ("p11-grace", "p11-grace", ""),
]

# -> JobTypes
JobQueue_items = [
    ("JOB_CPU", "CPU", ""),    
    ("JOB_GPU", "GPU", ""),

]

JobQueue_items_dict = {
    "JOB_CPU": "CPU",    
    "JOB_GPU": "GPU",

}

from . import raas_jobs
from . import raas_connection
##################################################################
ssh_library_items = [
    ("PARAMIKO", "Paramiko", ""),
    ("SYSTEM", "System", ""),
    ("ASYNCSSH", "AsyncSSH", ""),
]

account_types_items = [
    ("EDUID", "e-INFRA CZ (eduID.cz)", ""),    
    ("IT4I", "IT4I", ""),
]
##################################################################
def GetBlenderClusterVersion():
    return (str(bpy.app.version_string)).replace(' ', '_')
##################################################################

async def CreateJob(context, token):
        blender_job_info_new = context.scene.raas_blender_job_info_new
        job_type = blender_job_info_new.job_type

        if blender_job_info_new.cluster_type == 'BARBORA':    

            if 'JOB_CPU' in job_type:
                await raas_jobs.CreateJobTask3Dep(context, token, raas_jobs.JobTaskInfo(36, 11, 10), raas_jobs.JobTaskInfo(36, 11, 11), raas_jobs.JobTaskInfo(36, 11, 12), 2, 1)
        
            elif 'JOB_GPU' in job_type:
                await raas_jobs.CreateJobTask3Dep(context, token, raas_jobs.JobTaskInfo(24, 12, 13), raas_jobs.JobTaskInfo(24, 12, 14), raas_jobs.JobTaskInfo(24, 12, 15), 2, 1)

        elif blender_job_info_new.cluster_type == 'KAROLINA':    

            if 'JOB_CPU' in job_type:
                await raas_jobs.CreateJobTask3Dep(context, token, raas_jobs.JobTaskInfo(128, 21, 20), raas_jobs.JobTaskInfo(128, 21, 21), raas_jobs.JobTaskInfo(128, 21, 22), 2, 2)                
        
            elif 'JOB_GPU' in job_type:
                await raas_jobs.CreateJobTask3Dep(context, token, raas_jobs.JobTaskInfo(128, 22, 23), raas_jobs.JobTaskInfo(128, 22, 24), raas_jobs.JobTaskInfo(128, 22, 25), 2, 2)

        elif blender_job_info_new.cluster_type == 'LUMI':    

            if 'JOB_CPU' in job_type:
                # context, token, jobNodes, clusterNodeTypeId, CommandTemplateId, ..., FileTranferMethodId, ClusterId 
                await raas_jobs.CreateJobTask3Dep(context, token, raas_jobs.JobTaskInfo(128, 31, 30), raas_jobs.JobTaskInfo(128, 31, 31), raas_jobs.JobTaskInfo(128, 31, 32), 2, 3)                
        
            elif 'JOB_GPU' in job_type:
                await raas_jobs.CreateJobTask3Dep(context, token, raas_jobs.JobTaskInfo(128, 32, 33), raas_jobs.JobTaskInfo(128, 32, 34), raas_jobs.JobTaskInfo(128, 32, 35), 2, 3)                               


        elif blender_job_info_new.cluster_type == 'LEONARDO':    

            if 'JOB_CPU' in job_type:
                # context, token, jobNodes, clusterNodeTypeId, CommandTemplateId, ..., FileTranferMethodId, ClusterId 
                await raas_jobs.CreateJobTask3Dep(context, token, raas_jobs.JobTaskInfo(32, 41, 40), raas_jobs.JobTaskInfo(32, 41, 41), raas_jobs.JobTaskInfo(32, 41, 42), 2, 4)
        
            elif 'JOB_GPU' in job_type:
                await raas_jobs.CreateJobTask3Dep(context, token, raas_jobs.JobTaskInfo(32, 41, 43), raas_jobs.JobTaskInfo(32, 41, 44), raas_jobs.JobTaskInfo(32, 41, 45), 2, 4)

        elif blender_job_info_new.cluster_type == 'MARENOSTRUM5GPP':    

            if 'JOB_CPU' in job_type:
                # context, token, jobNodes, clusterNodeTypeId, CommandTemplateId, ..., FileTranferMethodId, ClusterId 
                await raas_jobs.CreateJobTask3Dep(context, token, raas_jobs.JobTaskInfo(32, 51, 50), raas_jobs.JobTaskInfo(32, 51, 51), raas_jobs.JobTaskInfo(32, 51, 52), 2, 5)
        
            elif 'JOB_GPU' in job_type:
                await raas_jobs.CreateJobTask3Dep(context, token, raas_jobs.JobTaskInfo(32, 51, 53), raas_jobs.JobTaskInfo(32, 51, 54), raas_jobs.JobTaskInfo(32, 51, 55), 2, 5)

        elif blender_job_info_new.cluster_type == 'MARENOSTRUM5ACC':    

            if 'JOB_CPU' in job_type:
                # context, token, jobNodes, clusterNodeTypeId, CommandTemplateId, ..., FileTranferMethodId, ClusterId 
                await raas_jobs.CreateJobTask3Dep(context, token, raas_jobs.JobTaskInfo(32, 61, 60), raas_jobs.JobTaskInfo(32, 61, 61), raas_jobs.JobTaskInfo(32, 61, 62), 2, 6)
        
            elif 'JOB_GPU' in job_type:
                await raas_jobs.CreateJobTask3Dep(context, token, raas_jobs.JobTaskInfo(32, 61, 63), raas_jobs.JobTaskInfo(32, 61, 64), raas_jobs.JobTaskInfo(32, 61, 65), 2, 6)

        elif blender_job_info_new.cluster_type == 'POLARIS':    

            if 'JOB_CPU' in job_type:
                # context, token, jobNodes, clusterNodeTypeId, CommandTemplateId, ..., FileTranferMethodId, ClusterId 
                await raas_jobs.CreateJobTask3Dep(context, token, raas_jobs.JobTaskInfo(64, 71, 70), raas_jobs.JobTaskInfo(64, 71, 71), raas_jobs.JobTaskInfo(64, 71, 72), 2, 7)
        
            elif 'JOB_GPU' in job_type:
                await raas_jobs.CreateJobTask3Dep(context, token, raas_jobs.JobTaskInfo(64, 71, 73), raas_jobs.JobTaskInfo(64, 71, 74), raas_jobs.JobTaskInfo(64, 71, 75), 2, 7)

        elif blender_job_info_new.cluster_type == 'AURORA':    

            if 'JOB_CPU' in job_type:
                # context, token, jobNodes, clusterNodeTypeId, CommandTemplateId, ..., FileTranferMethodId, ClusterId 
                await raas_jobs.CreateJobTask3Dep(context, token, raas_jobs.JobTaskInfo(32, 81, 80), raas_jobs.JobTaskInfo(32, 81, 81), raas_jobs.JobTaskInfo(32, 81, 82), 2, 8)
        
            elif 'JOB_GPU' in job_type:
                await raas_jobs.CreateJobTask3Dep(context, token, raas_jobs.JobTaskInfo(32, 81, 83), raas_jobs.JobTaskInfo(32, 81, 84), raas_jobs.JobTaskInfo(32, 81, 85), 2, 8)


        elif blender_job_info_new.cluster_type == 'VISTA':    

            if 'JOB_CPU' in job_type:
                # context, token, jobNodes, clusterNodeTypeId, CommandTemplateId, ..., FileTranferMethodId, ClusterId 
                await raas_jobs.CreateJobTask3Dep(context, token, raas_jobs.JobTaskInfo(72, 91, 90), raas_jobs.JobTaskInfo(72, 91, 91), raas_jobs.JobTaskInfo(72, 91, 92), 2, 9)
        
            elif 'JOB_GPU' in job_type:
                await raas_jobs.CreateJobTask3Dep(context, token, raas_jobs.JobTaskInfo(72, 91, 93), raas_jobs.JobTaskInfo(72, 91, 94), raas_jobs.JobTaskInfo(72, 91, 95), 2, 9)


        elif blender_job_info_new.cluster_type == 'FRONTERA':

            if 'JOB_CPU' in job_type:
                # context, token, jobNodes, clusterNodeTypeId, CommandTemplateId, ..., FileTranferMethodId, ClusterId 
                await raas_jobs.CreateJobTask3Dep(context, token, raas_jobs.JobTaskInfo(32, 101, 100), raas_jobs.JobTaskInfo(32, 101, 101), raas_jobs.JobTaskInfo(32, 101, 102), 2, 10)
        
            elif 'JOB_GPU' in job_type:
                await raas_jobs.CreateJobTask3Dep(context, token, raas_jobs.JobTaskInfo(32, 101, 103), raas_jobs.JobTaskInfo(32, 101, 104), raas_jobs.JobTaskInfo(32, 101, 105), 2, 10)


        elif blender_job_info_new.cluster_type == 'CS':

            if 'JOB_CPU' in job_type:
                # context, token, jobNodes, clusterNodeTypeId, CommandTemplateId, ..., FileTranferMethodId, ClusterId 
                await raas_jobs.CreateJobTask3Dep(context, token, raas_jobs.JobTaskInfo(32, 111, 110), raas_jobs.JobTaskInfo(32, 111, 111), raas_jobs.JobTaskInfo(32, 111, 112), 2, 11)
        
            elif 'JOB_GPU' in job_type:
                await raas_jobs.CreateJobTask3Dep(context, token, raas_jobs.JobTaskInfo(32, 111, 113), raas_jobs.JobTaskInfo(32, 111, 114), raas_jobs.JobTaskInfo(32, 111, 115), 2, 11)


##################################################################
def GetServer(pid):
    return "" # TODO

##################################################################
def GetServerFromType(cluster_type):
    if cluster_type == 'BARBORA':
        return 'barbora.it4i.cz'

    elif cluster_type == 'KAROLINA':
        return 'karolina.it4i.cz'
    
    elif cluster_type == 'LUMI':
        return 'lumi.csc.fi'
    
    elif cluster_type == 'LEONARDO':
        return 'login.leonardo.cineca.it'
    
    elif cluster_type == 'MARENOSTRUM5GPP':
        return 'glogin2.bsc.es'

    elif cluster_type == 'MARENOSTRUM5ACC':
        return 'alogin2.bsc.es'
    
    elif cluster_type == 'MARENOSTRUM5DATA':
        return 'transfer2.bsc.es'

    elif cluster_type == 'POLARIS':
        return 'polaris.alcf.anl.gov'
    
    elif cluster_type == 'AURORA':
        return 'aurora.alcf.anl.gov'
    
    elif cluster_type == 'VISTA':
        return 'vista.tacc.utexas.edu'
    
    elif cluster_type == 'FRONTERA':
        return 'frontera.tacc.utexas.edu'
    
    elif cluster_type == 'CS':
        return 'login.cs.it4i.cz'    
    
def GetSchedulerFromContext(context):
    blender_job_info_new = context.scene.raas_blender_job_info_new
    cluster_type = blender_job_info_new.cluster_type

    if cluster_type == 'BARBORA':
        return 'SLURM'

    elif cluster_type == 'KAROLINA':
        return 'SLURM'
    
    elif cluster_type == 'LUMI':
        return 'SLURM'
    
    elif cluster_type == 'LEONARDO':
        return 'SLURM'
    
    elif cluster_type == 'MARENOSTRUM5GPP':
        return 'SLURM'

    elif cluster_type == 'MARENOSTRUM5ACC':
        return 'SLURM'
    
    elif cluster_type == 'MARENOSTRUM5DATA':
        return 'NONE'

    elif cluster_type == 'POLARIS':
        return 'PBS'
    
    elif cluster_type == 'AURORA':
        return 'PBS'
    
    elif cluster_type == 'VISTA':
        return 'SLURM'
    
    elif cluster_type == 'FRONTERA':
        return 'SLURM'
    
    elif cluster_type == 'CS':
        return 'SLURM'    

def GetDAServer(context):
    blender_job_info_new = context.scene.raas_blender_job_info_new
    return GetServerFromType(blender_job_info_new.cluster_type)

def GetDAClusterPath(context, project_dir, pid):
    #blender_job_info_new = context.scene.raas_blender_job_info_new
    #if blender_job_info_new.cluster_type == 'BARBORA' or blender_job_info_new.cluster_type == 'KAROLINA':    
    return project_dir + '/braas-hpc/direct'


def GetDAOpenCallProject(pid):
    return pid

def GetDAQueueMPIProcs(CommandTemplateId):
    # BARBORA
    if CommandTemplateId == 16:
        return 4
    # KAROLINA
    elif CommandTemplateId == 26:  
        return 8
    # LUMI
    elif CommandTemplateId == 36:  
        return 8
    # LEONARDO
    elif CommandTemplateId == 46:  
        return 4 # GPUs   
    # "MARENOSTRUM5GPP": "MareNostrum 5 GPP",
    elif CommandTemplateId == 56:  
        return 0 # GPUs
    # "MARENOSTRUM5ACC": "MareNostrum 5 ACC",
    elif CommandTemplateId == 66:  
        return 4 # GPUs   
    # "POLARIS": "Polaris",
    elif CommandTemplateId == 76:  
        return 4 # GPUs   
    # "AURORA": "Aurora",
    elif CommandTemplateId == 86:  
        return 4 # GPUs
    # "VISTA": "Vista",
    elif CommandTemplateId == 96:
        return 1 # GPUs
    # "FRONTERA": "Frontera",
    elif CommandTemplateId == 106:
        return 4 # GPUs    
    elif CommandTemplateId == 116:
        return 2 # GPUs

    else:
        return 0


# return cores,queue,script
def GetDAQueueScript(ClusterId, CommandTemplateId):
    # BARBORA
    if ClusterId == 1:
        if CommandTemplateId == 10 * ClusterId:
            return 36,'~/braas-hpc/scripts/barbora-slurm/job_init.sh'

        elif CommandTemplateId == 10 * ClusterId + 1:
            return 36,'~/braas-hpc/scripts/barbora-slurm/run_blender_cpu.sh'

        elif CommandTemplateId == 10 * ClusterId + 2:
            return 36,'~/braas-hpc/scripts/barbora-slurm/job_finish.sh'

        elif CommandTemplateId == 10 * ClusterId + 3:
            return 24,'~/braas-hpc/scripts/barbora-slurm/job_init.sh'

        elif CommandTemplateId == 10 * ClusterId + 4:
            return 24,'~/braas-hpc/scripts/barbora-slurm/run_blender_gpu.sh'

        elif CommandTemplateId == 10 * ClusterId + 5:
            return 24,'~/braas-hpc/scripts/barbora-slurm/job_finish.sh'
        

    # KAROLINA
    elif ClusterId == 2:     
        if CommandTemplateId == 10 * ClusterId:
            return 128,'~/braas-hpc/scripts/karolina-slurm/job_init.sh'

        elif CommandTemplateId == 10 * ClusterId + 1:
            return 128,'~/braas-hpc/scripts/karolina-slurm/run_blender_cpu.sh'

        elif CommandTemplateId == 10 * ClusterId + 2:
            return 128,'~/braas-hpc/scripts/karolina-slurm/job_finish.sh'

        elif CommandTemplateId == 10 * ClusterId + 3:
            return 128,'~/braas-hpc/scripts/karolina-slurm/job_init.sh'

        elif CommandTemplateId == 10 * ClusterId + 4:
            return 128,'~/braas-hpc/scripts/karolina-slurm/run_blender_gpu.sh'

        elif CommandTemplateId == 10 * ClusterId + 5:
            return 128,'~/braas-hpc/scripts/karolina-slurm/job_finish.sh'

                               
    # LUMI
    elif ClusterId == 3:     
        if CommandTemplateId == 10 * ClusterId:
            return 128,'~/braas-hpc/scripts/lumi-slurm/job_init.sh'

        elif CommandTemplateId == 10 * ClusterId + 1:
            return 128,'~/braas-hpc/scripts/lumi-slurm/run_blender_cpu.sh'

        elif CommandTemplateId == 10 * ClusterId + 2:
            return 128,'~/braas-hpc/scripts/lumi-slurm/job_finish.sh'

        elif CommandTemplateId == 10 * ClusterId + 3:
            return 128,'~/braas-hpc/scripts/lumi-slurm/job_init.sh'

        elif CommandTemplateId == 10 * ClusterId + 4:
            return 128,'~/braas-hpc/scripts/lumi-slurm/run_blender_gpu.sh'

        elif CommandTemplateId == 10 * ClusterId + 5:
            return 128,'~/braas-hpc/scripts/lumi-slurm/job_finish.sh'


    # LEONARDO
    elif ClusterId == 4:
        if CommandTemplateId == 10 * ClusterId:
            return 32,'~/braas-hpc/scripts/leonardo-slurm/job_init.sh'

        elif CommandTemplateId == 10 * ClusterId + 1:
            return 32,'~/braas-hpc/scripts/leonardo-slurm/run_blender_cpu.sh'

        elif CommandTemplateId == 10 * ClusterId + 2:
            return 32,'~/braas-hpc/scripts/leonardo-slurm/job_finish.sh'

        elif CommandTemplateId == 10 * ClusterId + 3:
            return 32,'~/braas-hpc/scripts/leonardo-slurm/job_init.sh'

        elif CommandTemplateId == 10 * ClusterId + 4:
            return 32,'~/braas-hpc/scripts/leonardo-slurm/run_blender_gpu.sh'

        elif CommandTemplateId == 10 * ClusterId + 5:
            return 32,'~/braas-hpc/scripts/leonardo-slurm/job_finish.sh'
        
    # "MARENOSTRUM5GPP": "MareNostrum 5 GPP",
    elif ClusterId == 5:
        if CommandTemplateId == 10 * ClusterId:
            return 32,'~/braas-hpc/scripts/marenostrum5gpp-slurm/job_init.sh'

        elif CommandTemplateId == 10 * ClusterId + 1:
            return 32,'~/braas-hpc/scripts/marenostrum5gpp-slurm/run_blender_cpu.sh'

        elif CommandTemplateId == 10 * ClusterId + 2:
            return 32,'~/braas-hpc/scripts/marenostrum5gpp-slurm/job_finish.sh'

        elif CommandTemplateId == 10 * ClusterId + 3:
            return 32,'~/braas-hpc/scripts/marenostrum5gpp-slurm/job_init.sh'

        elif CommandTemplateId == 10 * ClusterId + 4:
            return 32,'~/braas-hpc/scripts/marenostrum5gpp-slurm/run_blender_gpu.sh'

        elif CommandTemplateId == 10 * ClusterId + 5:
            return 32,'~/braas-hpc/scripts/marenostrum5gpp-slurm/job_finish.sh'

    # "MARENOSTRUM5ACC": "MareNostrum 5 ACC",
    elif ClusterId == 6:
        if CommandTemplateId == 10 * ClusterId:
            return 32,'~/braas-hpc/scripts/marenostrum5acc-slurm/job_init.sh'

        elif CommandTemplateId == 10 * ClusterId + 1:
            return 32,'~/braas-hpc/scripts/marenostrum5acc-slurm/run_blender_cpu.sh'

        elif CommandTemplateId == 10 * ClusterId + 2:
            return 32,'~/braas-hpc/scripts/marenostrum5acc-slurm/job_finish.sh'

        elif CommandTemplateId == 10 * ClusterId + 3:
            return 32,'~/braas-hpc/scripts/marenostrum5acc-slurm/job_init.sh'

        elif CommandTemplateId == 10 * ClusterId + 4:
            return 32,'~/braas-hpc/scripts/marenostrum5acc-slurm/run_blender_gpu.sh'

        elif CommandTemplateId == 10 * ClusterId + 5:
            return 32,'~/braas-hpc/scripts/marenostrum5acc-slurm/job_finish.sh'

    # "POLARIS": "Polaris",
    elif ClusterId == 7:
        if CommandTemplateId == 10 * ClusterId:
            return 64,'~/braas-hpc/scripts/polaris-pbs/job_init.sh'

        elif CommandTemplateId == 10 * ClusterId + 1:
            return 64,'~/braas-hpc/scripts/polaris-pbs/run_blender_cpu.sh'

        elif CommandTemplateId == 10 * ClusterId + 2:
            return 64,'~/braas-hpc/scripts/polaris-pbs/job_finish.sh'

        elif CommandTemplateId == 10 * ClusterId + 3:
            return 64,'~/braas-hpc/scripts/polaris-pbs/job_init.sh'

        elif CommandTemplateId == 10 * ClusterId + 4:
            return 64,'~/braas-hpc/scripts/polaris-pbs/run_blender_gpu.sh'

        elif CommandTemplateId == 10 * ClusterId + 5:
            return 64,'~/braas-hpc/scripts/polaris-pbs/job_finish.sh'

    # "AURORA": "Aurora",
    elif ClusterId == 8:
        if CommandTemplateId == 10 * ClusterId:
            return 32,'~/braas-hpc/scripts/aurora-pbs/job_init.sh'

        elif CommandTemplateId == 10 * ClusterId + 1:
            return 32,'~/braas-hpc/scripts/aurora-pbs/run_blender_cpu.sh'

        elif CommandTemplateId == 10 * ClusterId + 2:
            return 32,'~/braas-hpc/scripts/aurora-pbs/job_finish.sh'

        elif CommandTemplateId == 10 * ClusterId + 3:
            return 32,'~/braas-hpc/scripts/aurora-pbs/job_init.sh'

        elif CommandTemplateId == 10 * ClusterId + 4:
            return 32,'~/braas-hpc/scripts/aurora-pbs/run_blender_gpu.sh'

        elif CommandTemplateId == 10 * ClusterId + 5:
            return 32,'~/braas-hpc/scripts/aurora-pbs/job_finish.sh'

    # "VISTA": "Vista",
    elif ClusterId == 9:
        if CommandTemplateId == 10 * ClusterId:
            return 72,'~/braas-hpc/scripts/vista-slurm/job_init.sh'

        elif CommandTemplateId == 10 * ClusterId + 1:
            return 72,'~/braas-hpc/scripts/vista-slurm/run_blender_cpu.sh'

        elif CommandTemplateId == 10 * ClusterId + 2:
            return 72,'~/braas-hpc/scripts/vista-slurm/job_finish.sh'

        elif CommandTemplateId == 10 * ClusterId + 3:
            return 72,'~/braas-hpc/scripts/vista-slurm/job_init.sh'

        elif CommandTemplateId == 10 * ClusterId + 4:
            return 72,'~/braas-hpc/scripts/vista-slurm/run_blender_gpu.sh'

        elif CommandTemplateId == 10 * ClusterId + 5:
            return 72,'~/braas-hpc/scripts/vista-slurm/job_finish.sh'
        
    # "FRONTERA": "Frontera",
    elif ClusterId == 10:
        if CommandTemplateId == 10 * ClusterId:
            return 32,'~/braas-hpc/scripts/frontera-slurm/job_init.sh'

        elif CommandTemplateId == 10 * ClusterId + 1:
            return 32,'~/braas-hpc/scripts/frontera-slurm/run_blender_cpu.sh'

        elif CommandTemplateId == 10 * ClusterId + 2:
            return 32,'~/braas-hpc/scripts/frontera-slurm/job_finish.sh'

        elif CommandTemplateId == 10 * ClusterId + 3:
            return 32,'~/braas-hpc/scripts/frontera-slurm/job_init.sh'

        elif CommandTemplateId == 10 * ClusterId + 4:
            return 32,'~/braas-hpc/scripts/frontera-slurm/run_blender_gpu.sh'

        elif CommandTemplateId == 10 * ClusterId + 5:
            return 32,'~/braas-hpc/scripts/frontera-slurm/job_finish.sh'
        
    # "CS": "CS",
    elif ClusterId == 11:
        if CommandTemplateId == 10 * ClusterId:
            return 32,'~/braas-hpc/scripts/cs-slurm/job_init.sh'

        elif CommandTemplateId == 10 * ClusterId + 1:
            return 32,'~/braas-hpc/scripts/cs-slurm/run_blender_cpu.sh'

        elif CommandTemplateId == 10 * ClusterId + 2:
            return 32,'~/braas-hpc/scripts/cs-slurm/job_finish.sh'

        elif CommandTemplateId == 10 * ClusterId + 3:
            return 32,'~/braas-hpc/scripts/cs-slurm/job_init.sh'

        elif CommandTemplateId == 10 * ClusterId + 4:
            return 32,'~/braas-hpc/scripts/cs-slurm/run_blender_gpu.sh'

        elif CommandTemplateId == 10 * ClusterId + 5:
            return 32,'~/braas-hpc/scripts/cs-slurm/job_finish.sh'
                
    else:
        return None, None


def GetGitAddonCommand(repository, branch):    
    return 'if [ -d ~/braas-hpc ] ; then rm -rf ~/braas-hpc ; fi ; git clone -q -b ' + branch + ' ' + repository

def GetBlenderInstallCommand(preset, url_link):
    # Split the URL by '/' and get the last part
    filename = url_link.split('/')[-1]

    # Remove the extension to get the desired string
    extracted_string = filename.replace('.tar.xz', '')
    #print(extracted_string)  # Output: blender-4.2.0-linux-x64

    return 'if [ -d ~/blender ] ; then rm -rf ~/blender ; fi ; \
        cd ~/ ; wget -O blender.tar.xz -q %s ; \
        tar -xf blender.tar.xz ; mv %s ~/blender ; rm blender.tar.xz ; \
            ' % (url_link, extracted_string)

def GetBlenderPatchCommand(preset, url_link):
    # Split the URL by '/' and get the last part
    #filename = url_link.split('/')[-1]

    # Remove the extension to get the desired string
    #extracted_string = filename.replace('.tar.xz', '')
    #print(extracted_string)  # Output: blender-4.2.0-linux-x64

    cmd = ''
    if preset.cluster_name == "AURORA":
        lib_so = 'https://code.it4i.cz/raas/blenderphi/-/raw/cycles-v4.5-aurora/bin/cycles/kernels/aurora/libcycles_kernel_oneapi_aot.so'
        cmd = 'if [ -d ~/blender ] ; then cd ~/blender/lib ; wget -O libcycles_kernel_oneapi_aot.so -q %s ; fi ; ' % lib_so
    
    return cmd


# def DownloadBlenderLUMI():  
#     """Downloads the specific version of Blender and installs in the scratch location on cluster.""" 
#     #scratch = '/scratch/%s/%s' % (project_name, user_name)
#     blender_file='blender-4.0.2-linux-x64'
#     return 'if [ -d ~/blender ] ; then rm -rf ~/blender ; fi ; \
#         wget -nv https://ftp.nluug.nl/pub/graphics/blender/release/Blender4.0/%s.tar.xz ; \
#         tar -xf %s.tar.xz ; mv %s ~/blender ; rm %s.tar.xz ; \
#             patch ~/blender/4.0/scripts/addons/cycles/source/kernel/types.h < ~/braas-hpc/scripts/lumi-slurm/patch/types.patch \
#             ' % (blender_file, blender_file, blender_file, blender_file)

def GetCurrentPidInfo(context, preferences):
    blender_job_info_new = context.scene.raas_blender_job_info_new
    name = blender_job_info_new.job_allocation
    queue = blender_job_info_new.job_partition
    dir = blender_job_info_new.job_remote_dir

    return name, queue, dir

def SetPidDir(preset):
    if preset.cluster_name == "LUMI": # ugly but the code needs redesign
        preset.working_dir = "/scratch/" + preset.allocation_name
    elif preset.cluster_name == "LEONARDO": # ugly but the code needs redesign
        preset.working_dir = "/leonardo_scratch/fast/" + preset.allocation_name
    elif preset.cluster_name == "MARENOSTRUM5GPP" or preset.cluster_name == "MARENOSTRUM5ACC" or preset.cluster_name == "MARENOSTRUM5DATA": # ugly but the code needs redesign
        preset.working_dir = "/gpfs/scratch/" + preset.allocation_name.lower() + "/" + preset.raas_da_username
    elif preset.cluster_name == "POLARIS": # ugly but the code needs redesign
        preset.working_dir = "/grand/" + preset.allocation_name.lower() + "/" + preset.raas_da_username
    elif preset.cluster_name == "AURORA": # ugly but the code needs redesign
        preset.working_dir = "/lus/flare/projects/" + preset.allocation_name.lower() + "/" + preset.raas_da_username
    elif preset.cluster_name == "VISTA" or preset.cluster_name == "FRONTERA":
        cmd = 'echo $SCRATCH'
        if len(cmd) > 0:
            server = GetServerFromType(preset.cluster_name.upper())
            res = raas_connection.ssh_command_sync(server, cmd, preset)
            preset.working_dir = res.strip()
    elif preset.cluster_name == "BARBORA" or preset.cluster_name == "KAROLINA" or preset.cluster_name == "CS":  # IT4I clusters only
        cmd = 'it4i-get-project-dir ' + preset.allocation_name.upper()
        if len(cmd) > 0:
            server = GetServerFromType(preset.cluster_name.upper())
            res = raas_connection.ssh_command_sync(server, cmd, preset)
            preset.working_dir = res.strip()

    else:
        raise Exception("Unknown cluster name")
    

class RaasConfigFunctions:
    """Class that holds pointers to all functions"""
    
    def __init__(self):
        # Function pointers
        # self.get_blender_cluster_version = GetBlenderClusterVersion
        self.create_job = CreateJob
        # self.get_server = GetServer
        self.get_server_from_type = GetServerFromType
        self.get_scheduler_from_context = GetSchedulerFromContext
        self.get_da_server = GetDAServer
        self.get_da_cluster_path = GetDAClusterPath
        self.get_da_open_call_project = GetDAOpenCallProject
        self.get_da_queue_mpi_procs = GetDAQueueMPIProcs
        self.get_da_queue_script = GetDAQueueScript
        self.get_git_addon_command = GetGitAddonCommand
        self.get_blender_install_command = GetBlenderInstallCommand
        self.get_blender_patch_command = GetBlenderPatchCommand
        self.get_current_pid_info = GetCurrentPidInfo
        self.set_pid_dir = SetPidDir
    
    # Convenience methods that can be called on the instance
    # def call_get_blender_cluster_version(self):
    #     """Returns Blender cluster version string"""
    #     return self.get_blender_cluster_version()
    
    async def call_create_job(self, context, token):
        """Creates a job with the given context and token"""
        return await self.create_job(context, token)
    
    # def call_get_server(self, pid):
    #     """Gets server from PID"""
    #     return self.get_server(pid)
    
    def call_get_server_from_type(self, cluster_type):
        """Gets server from cluster type"""
        return self.get_server_from_type(cluster_type)
    
    def call_get_scheduler_from_context(self, context):
        """Gets scheduler from context"""
        return self.get_scheduler_from_context(context)
    
    def call_get_da_server(self, context):
        """Gets DA server from context"""
        return self.get_da_server(context)
    
    def call_get_da_cluster_path(self, context, project_dir, pid):
        """Gets DA cluster path"""
        return self.get_da_cluster_path(context, project_dir, pid)
    
    def call_get_da_open_call_project(self, pid):
        """Gets DA open call project"""
        return self.get_da_open_call_project(pid)
    
    def call_get_da_queue_mpi_procs(self, command_template_id):
        """Gets DA queue MPI processes count"""
        return self.get_da_queue_mpi_procs(command_template_id)
    
    def call_get_da_queue_script(self, cluster_id, command_template_id):
        """Gets DA queue script"""
        return self.get_da_queue_script(cluster_id, command_template_id)
    
    def call_get_git_addon_command(self, repository, branch):
        """Gets git addon command"""
        return self.get_git_addon_command(repository, branch)
    
    def call_get_blender_install_command(self, preset, url_link):
        """Gets Blender install command"""
        return self.get_blender_install_command(preset, url_link)
    
    def call_get_blender_patch_command(self, preset, url_link):
        """Gets Blender patch command"""
        return self.get_blender_patch_command(preset, url_link)
    
    def call_get_current_pid_info(self, context, preferences):
        """Gets current PID info"""
        return self.get_current_pid_info(context, preferences)
    
    def call_set_pid_dir(self, preset):
        """Sets PID directory"""
        return self.set_pid_dir(preset)