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
import asyncio

################################
import time
################################

import bpy
from bpy.types import AddonPreferences, Operator, WindowManager, Scene, PropertyGroup, Panel
from bpy.props import StringProperty, EnumProperty, PointerProperty, BoolProperty, IntProperty

from bpy.types import Header, Menu

from . import async_loop
from . import raas_server
from . import raas_pref
from . import raas_jobs
from . import raas_config

import pathlib
import json

log = logging.getLogger(__name__)

################################

def redraw(self, context):
    if context.area is None:
        return
    context.area.tag_redraw() 

# def show_message_box(message = "", title = "BRaaS-HPC", type = 'ERROR'):

#     def draw(self, context):
#         self.layout.label(message)

#     bpy.context.window_manager.popup_menu(draw, title = title, icon = type)

#     #self.report({type}, message)

################################    

def get_cluster_presets():
    presets = []  # to be returned in EnumProperty
    for preset in raas_pref.preferences().cluster_presets:
        presets.append(('%s, %s, %s' % (preset.cluster_name, preset.allocation_name, preset.partition_name), '', ''))
    return presets

def get_pref_storage_dir():
    pref = raas_pref.preferences()
    return pref.raas_job_storage_path

def get_ssh_key_file():
    ssh_key_local = Path(tempfile.gettempdir()) / 'server_key'
    return ssh_key_local 

def get_job_local_storage(job_name):
    local_storage = Path(get_pref_storage_dir()) / job_name
    return local_storage     

def get_job_local_storage_in(job_name):
    local_storage_in = Path(get_pref_storage_dir()) / job_name / 'in'
    return local_storage_in    

def get_job_local_storage_out(job_name):
    local_storage_out = Path(get_pref_storage_dir()) / job_name / 'out'
    return local_storage_out  

def get_job_local_storage_log(job_name):
    local_storage_log = Path(get_pref_storage_dir()) / job_name / 'log'
    return local_storage_log     

def get_job_remote_storage_in(job_name):
    remote_storage_in = Path('in')
    return remote_storage_in   

def get_job_remote_storage(job_name):
    remote_storage_out = Path('.')
    return remote_storage_out

def get_job_remote_storage_out(job_name):
    remote_storage_out = Path('out')
    return remote_storage_out

def get_job_remote_storage_log(job_name):
    remote_storage_log = Path('log')
    return remote_storage_log    

def convert_path_to_linux(path)->str:
    p = str(path)
    return p.replace("\\","/")

def get_blendfile_fullpath(context):
    path = bpy.path.abspath(context.scene.raas_blender_job_info_new.blendfile_dir) + '/' \
        + context.scene.raas_blender_job_info_new.blendfile
    return path

def is_verbose_debug():
    import bpy
    return bpy.app.debug_value == 256

def get_project_group(context):
    pref = raas_pref.preferences()
    project_group = pref.raas_project_group
    if len(project_group) == 0:
        if context.scene.raas_cluster_presets_index > -1 and len(pref.cluster_presets) > 0:
            preset = pref.cluster_presets[context.scene.raas_cluster_presets_index]
            project_group = preset.raas_da_username

    if len(project_group) == 0:
        import getpass        
        project_group = getpass.getuser()

    if len(pref.raas_project_group) == 0:
        pref.raas_project_group = project_group

    return project_group

def get_direct_access_remote_storage(context):
    pref = raas_pref.preferences()
    project_group = get_project_group(context)

    pid_name, pid_queue, pid_dir = raas_config.GetCurrentPidInfo(
        context, raas_pref.preferences())

    return raas_config.GetDAClusterPath(context, pid_dir, pid_name.lower()) \
        + '/' + project_group + '/' + context.scene.raas_blender_job_info_new.cluster_type.lower()

# def get_project_group_path(context):
#     pref = raas_pref.preferences()
#     project_group = get_project_group(context)

#     pid_name, pid_queue, pid_dir = raas_config.GetCurrentPidInfo(
#         context, raas_pref.preferences())

#     return raas_config.GetDAClusterPath(context, pid_dir, pid_name.lower()) \
#         + '/' + project_group

def CmdCreateProjectGroupFolder(context):
    cmd = 'mkdir -p ' + get_direct_access_remote_storage(context)
    return cmd
################################

class RaasButtonsPanel:
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"

    @classmethod
    def poll(cls, context):
        return context.engine == 'CYCLES'

class RAAS_PT_simplify(RaasButtonsPanel, Panel):
    bl_label = "BRaaS-HPC"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        #pass         
        layout = self.layout
        box = layout.box()
        #box.enabled = False

        row = box.row(align=True)
        row.enabled = False
        row.prop(context.window_manager, 'raas_status', text = 'Status')

        # Show current status of Raas.
        raas_status = context.window_manager.raas_status

        row = box.row(align=True)
        if raas_status in {'IDLE', 'ERROR' ,'DONE'}:
            row.enabled = False
        else:
            row.enabled = True

        row.prop(context.window_manager, 'raas_progress',
                    text=context.window_manager.raas_status_txt)
        row.operator(RAAS_OT_abort.bl_idname, text='', icon='CANCEL')

        # check values
        pref = raas_pref.preferences()
        #pid_name, pid_queue, pid_dir = raas_config.GetCurrentPidInfo(context, pref)

        if context.scene.raas_cluster_presets_index > -1 and len(pref.cluster_presets) > 0:
            preset = pref.cluster_presets[context.scene.raas_cluster_presets_index]

            if preset.raas_ssh_library == 'PARAMIKO':
                    if len(preset.raas_da_username) == 0 \
                        or not pref.raas_scripts_installed or len(pref.cluster_presets) < 1:
                        box.label(text='BRaaS-HPC is not set in preferences', icon='ERROR')
            else:
                if len(pref.cluster_presets) < 1 or not pref.raas_scripts_installed:
                    box.label(text='BRaaS-HPC is not set in preferences', icon='ERROR')
    
        if not pref.dependencies_installed:
            box.label(text='Dependencies are not installed', icon='ERROR')                

class AuthenticatedRaasOperatorMixin:
    """Checks credentials, to be used at the start of async_execute().

    Sets self.user_id to the current user's ID, and self.db_user to the user info dict,
    if authentication was succesful; sets both to None if not.
    """

    async def authenticate(self, context) -> bool:
        from . import raas_pref

        addon_prefs = raas_pref.preferences()
        if context.scene.raas_cluster_presets_index > -1 and len(addon_prefs.cluster_presets) > 0:
            preset = addon_prefs.cluster_presets[context.scene.raas_cluster_presets_index]
            if not addon_prefs.check_valid_settings(preset):
                return False        

        self.token = 'direct'
        return True
      

#############################################################################               
####################################JobManagement############################
#############################################################################   
		# Configuring = 1,
		# Submitted = 2,
		# Queued = 4,
		# Running = 8,
		# Finished = 16,
		# Failed = 32,
		# Canceled = 64


JobStateExt_items = [
    ("CONFIGURING", "Configuring", "", 1),
    ("SUBMITTED", "Submitted", "", 2),
    ("QUEUED", "Queued", "", 4),
    ("RUNNING", "Running", "", 8),
    ("FINISHED", "Finished", "", 16),
    ("FAILED", "Failed", "", 32),
    ("CANCELED", "Canceled", "", 64),
]	

JobPriorityExt_items = [
    ("CONFIGURING", "Configuring", "", 0),
    ("VERYLOW", "VeryLow", "", 1),
    ("LOW", "Low", "", 2),
    ("BELOWAVERAGE", "BelowAverage", "", 3),
    ("AVERAGE", "Average", "", 4),
    ("ABOVEAVERAGE", "AboveAverage", "", 5),
    ("HIGH", "High", "", 6),
    ("VERYHIGH", "VeryHigh", "", 7),
    ("CRITICAL", "Critical", "", 8),
]	

TaskStateExt_items = [
    ("CONFIGURING", "Configuring", "", 1),
    ("SUBMITTED", "Submitted", "", 2),
    ("QUEUED", "Queued", "", 4),
    ("RUNNING", "Running", "", 8),
    ("FINISHED", "Finished", "", 16),
    ("FAILED", "Failed", "", 32),
    ("CANCELED", "Canceled", "", 64),
]	

RenderType_items = [
    ("IMAGE", "Image", ""),
    ("ANIMATION", "Animation", ""),
]

FileType_items = [
    ("DEFAULT", "Packed .blend file", "Libraries packed into a single .blend file"),
    ("OTHER", "Sources in directory", "Select a .blend file together with directory with dependencies."),
]
  
####################################ListJobsForCurrentUser####################
def set_blendfile_dir(self, value):
    try:
        for file in os.listdir(bpy.path.abspath(self.blendfile_dir)):
            if file.endswith(".blend"):
                self.blendfile = file
                return None
    except:
        pass                

    return None


def clear_jobs_list(self, context):
    """
        Clears raas_list_jobs.
    """

    context.scene.raas_list_jobs.clear()
    return None   

class RAAS_PG_BlenderJobInfo(PropertyGroup):

    job_name : bpy.props.StringProperty(name="JobName")
    job_email : bpy.props.StringProperty(name="Email")
    job_project : bpy.props.StringProperty(name="Project Name",maxlen=25)
    job_walltime : bpy.props.IntProperty(name="Walltime [minutes]",default=30,min=1,max=2880)
    job_walltime_pre : bpy.props.IntProperty(name="Walltime Preprocessing [minutes]",default=10,min=1,max=2880)
    job_walltime_post : bpy.props.IntProperty(name="Walltime Postprocessing [minutes]",default=10,min=1,max=2880)    
    #job_nodes : bpy.props.IntProperty(name="Nodes",default=1,min=1,max=8)
    max_jobs : bpy.props.IntProperty(name="Max Jobs",default=100,min=1,max=10000)
    job_arrays : bpy.props.StringProperty(name="Job arrays", default='')

    job_type : bpy.props.EnumProperty(items=raas_config.JobQueue_items,name="Type of Job (resources)")
    job_remote_dir : bpy.props.StringProperty(name="Remote directory", options={'TEXTEDIT_UPDATE'})
    job_allocation : bpy.props.StringProperty(name="Allocation project name")  
    job_partition : bpy.props.StringProperty(name="Queue/Partition name") 

    frame_start : bpy.props.IntProperty(name="FrameStart")
    frame_end : bpy.props.IntProperty(name="FrameEnd")
    frame_current : bpy.props.IntProperty(name="FrameCurrent")
    #frame_step : bpy.props.IntProperty(name="FrameStep")

    render_type : bpy.props.EnumProperty(items=RenderType_items,name="Type")  
    cluster_type : bpy.props.EnumProperty(items=raas_config.Cluster_items,name="Cluster", update=clear_jobs_list)
    file_type : bpy.props.EnumProperty(items=FileType_items,name="File")    
    blendfile_dir : bpy.props.StringProperty(name="Dir", subtype='DIR_PATH', update=set_blendfile_dir)
    blendfile : bpy.props.StringProperty(name="Blend", default='')

class RAAS_PG_SubmittedTaskInfoExt(PropertyGroup):
    Id : bpy.props.IntProperty(name="Id")
    Name : bpy.props.StringProperty(name="Name")    

class RAAS_PG_SubmittedJobInfoExt(PropertyGroup):
    Id : bpy.props.IntProperty(name="Id")
    Name : bpy.props.StringProperty(name="Name")
    State : bpy.props.EnumProperty(items=JobStateExt_items,name="State")
    Priority : bpy.props.EnumProperty(items=JobPriorityExt_items,name="Priority",default='AVERAGE')
    Project : bpy.props.StringProperty(name="Project Name")
    CreationTime : bpy.props.StringProperty(name="Creation Time")
    SubmitTime : bpy.props.StringProperty(name="Submit Time")
    StartTime : bpy.props.StringProperty(name="Start Time")
    EndTime : bpy.props.StringProperty(name="End Time")
    TotalAllocatedTime : bpy.props.FloatProperty(name="totalAllocatedTime")
    AllParameters : bpy.props.StringProperty(name="allParameters")
    Tasks: bpy.props.StringProperty(name="Tasks")
    ClusterName: bpy.props.StringProperty(name="Cluster Name")

    #statePre : bpy.props.StringProperty(name="State Pre")
    #stateRen : bpy.props.StringProperty(name="State Ren")
    #statePost : bpy.props.StringProperty(name="State Post")

class RAAS_UL_SubmittedJobInfoExt(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        layout.label(text=('%d' % item.Id))
        #layout.label(text=item.Name)
        layout.label(text=item.Project)

        cluster_name = ''
        if item.ClusterName in raas_config.Cluster_items_dict:
            cluster_name = raas_config.Cluster_items_dict[item.ClusterName]
        layout.label(text=cluster_name)        

        if item.State != 'CONFIGURING':
            layout.label(text=item.State)
        else:
            layout.label(text='')

    def filter_items(self, context, data, propname):
        """Filter and order items in the list."""

        filtered = []
        ordered = []

        items = getattr(data, propname)

        helpers = bpy.types.UI_UL_list
        filtered = helpers.filter_items_by_name(self.filter_name,
                                        self.bitflag_filter_item,
                                        items, "Name", reverse=False)

        return filtered, ordered             
        

#############################################################################
class RaasSession:
    def __init__(self):
        self.paramiko_ssh_clients = {}

        self.server = None
        self.username = None
        self.key_file = None
        self.key_file_password = None
        self.password = None 
        self.use_password = None

    def paramiko_is_alive(self, server=None):
        """Check if SSH connection is alive for a specific server"""
        if server is None:
            server = self.server
            
        if server not in self.paramiko_ssh_clients:
            return False
            
        ssh_client = self.paramiko_ssh_clients[server]
        if ssh_client is None:
            return False

        transport = ssh_client.get_transport()
        if transport is None:
            return False

        return transport.is_active()
    
    def paramiko_close(self, server=None):
        """Close SSH connection for a specific server or all servers"""
        if server is None:
            # Close all connections
            for srv, ssh_client in self.paramiko_ssh_clients.items():
                if ssh_client is not None:
                    ssh_client.close()
            self.paramiko_ssh_clients.clear()
        else:
            # Close specific server connection
            if server in self.paramiko_ssh_clients:
                ssh_client = self.paramiko_ssh_clients[server]
                if ssh_client is not None:
                    ssh_client.close()
                del self.paramiko_ssh_clients[server]

    def paramiko_get_ssh(self, server=None):
        """Get SSH client for a specific server"""
        if server is None:
            server = self.server
            
        return self.paramiko_ssh_clients.get(server)
    
    def paramiko_set_ssh(self, ssh, server=None):
        """Set SSH client for a specific server"""
        if server is None:
            server = self.server
            
        self.paramiko_ssh_clients[server] = ssh

    def check_password(self):
        if self.use_password:
            return not self.password is None and len(self.password) > 0
        else:
            return not self.key_file_password is None and len(self.key_file_password) > 0

    def paramiko_create_session(self, password):
        import paramiko

        # pref = raas_pref.preferences()
        # preset = pref.cluster_presets[bpy.context.scene.raas_cluster_presets_index]    
            
        # key_file = preset.raas_private_key_path
        # username = preset.raas_da_username
        # password = preset.raas_private_key_password

        if not password is None:
            if self.use_password:
                self.password = password
            else:
                self.key_file_password = password

        ssh = None
        try: 
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.load_system_host_keys()

            if self.use_password:
                # Connect with username + password
                ssh.connect(
                    hostname=self.server,
                    username=self.username,
                    password=self.password,   # <-- instead of pkey
                    look_for_keys=False,      # don’t try ~/.ssh/id_rsa
                    allow_agent=False         # don’t use ssh-agent
                )                
            else:                
                # try:
                #     key = paramiko.RSAKey.from_private_key_file(self.key_file, self.key_file_password)
                # except:
                #     key = paramiko.Ed25519Key.from_private_key_file(self.key_file, self.key_file_password)
                from io import StringIO
                try:
                    #key = paramiko.RSAKey.from_private_key_file(key_file, password)

                    if self.key_file_password is None or len(self.key_file_password) == 0:
                        key = paramiko.RSAKey.from_private_key_file(self.key_file)
                    else:
                        key = paramiko.RSAKey.from_private_key_file(self.key_file, self.key_file_password)

                except Exception as e:
                    #key = paramiko.Ed25519Key.from_private_key_file(key_file, password)                
                    if self.key_file_password is None or len(self.key_file_password) == 0:
                        key = paramiko.Ed25519Key.from_private_key_file(self.key_file)
                    else:
                        key = paramiko.Ed25519Key.from_private_key_file(self.key_file, self.key_file_password)                

                ssh.connect(self.server, username=self.username, pkey=key)

            ssh.get_transport().set_keepalive(30)  # send keepalive every 30s

            # Store the SSH client in the dict with server as key
            self.paramiko_ssh_clients[self.server] = ssh

        except Exception as e:
            self.paramiko_ssh_clients[self.server] = None

            if ssh is not None:
                ssh.close()           

            raise Exception("paramiko ssh command failed:  %s: %s" % (e.__class__, e))
        
    def show_dialog(self, server, username, key_file, key_file_password, password, use_password):
        if not self.paramiko_is_alive(server):
            self.paramiko_close(server)

            self.server = server
            self.username = username
            self.key_file = key_file
            self.key_file_password = key_file_password
            self.password = password
            self.use_password = use_password

            if self.check_password():
                self.paramiko_create_session(None)
            else:
                bpy.ops.wm.raas_password_input('INVOKE_DEFAULT')
                raise Exception("Password required")

class RAAS_PASSWORD_OT_input(bpy.types.Operator):
    bl_idname = "wm.raas_password_input"
    bl_label = "Enter Password"

    password: bpy.props.StringProperty(
        name="Password",
        description="Enter your password",
        subtype='PASSWORD'  # <-- masks input in Blender 3.2+
    ) # type: ignore

    server: bpy.props.StringProperty(
        name="Server"
    ) # type: ignore    

    def draw(self, context):
        layout = self.layout

        box = layout

        # raas_box = box.column()
        # path_split = raas_box.split(**raas_pref.factor(0.25), align=True)
        # path_split.label(text='Local Storage Path:')
        # path_box = path_split.row(align=True)
        # path_box.prop(self, 'raas_job_storage_path', text='')
        # props = path_box.operator(
        #     'raas.explore_file_path', text='', icon='DISK_DRIVE')
        # props.path = self.raas_job_storage_path

        # Display server name
        session = context.scene.raas_session
        if session and session.server:
            #layout.label(text=f"Server: {session.server}")
            self.server = session.server

            box1 = box.split(**raas_pref.factor(0.25), align=True)
            box1.label(text='Server:')
            box1_row = box1.row(align=True)
            box1_row.enabled = False
            box1_row.prop(self, 'server', text='')

        box1 = box.split(**raas_pref.factor(0.25), align=True)
        box1.label(text='Password:')
        box1_row = box1.row(align=True)
        box1_row.prop(self, 'password', text='')

    def execute(self, context):
        self.report({'INFO'}, f"Password entered (hidden): {len(self.password)} chars")
        # pref = raas_pref.preferences()
        # preset = pref.cluster_presets[bpy.context.scene.raas_cluster_presets_index]            
        # preset.raas_da_password = self.password

        bpy.context.scene.raas_session.paramiko_create_session(self.password)

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
#############################################################################    
async def _ssh_tunnel(key_file, destination, port1, port2):
        """ Execute an ssh command """
        cmd = [
            'ssh',
            '-N',
            '-i', key_file,            
            '-L', port1,
            '-L', port2,
            destination,
            '&',
        ]
        #             '-q',             '-o', 'StrictHostKeyChecking=no',

        import asyncio
        #loop = asyncio.get_event_loop()
        #, stdin=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        #process = await asyncio.create_subprocess_exec(*cmd, loop=loop)
        process = await asyncio.create_subprocess_exec(*cmd)
        await process.wait()

        if process.returncode != 0 and is_verbose_debug() == True:
            print("ssh command failed: %s" % cmd)

async def connect_to_client(context, fileTransfer, job_id: int, token: str) -> None:
    """connect_to_client"""       

    data = {
        "SubmittedJobInfoId": job_id,
        "SessionCode": token
    }

    #allocated_nodes_ips = await raas_server.post("JobManagement/GetAllocatedNodesIPs", data)
    info_job = await raas_server.post("JobManagement/GetCurrentInfoForJob", data)
    all_params = info_job['AllParameters']
    allocated_nodes_ips = ''
    for line in all_params.split('\n'):
        if "exec_vnode" in line:
            allocated_nodes_ips = line.split('(')
            allocated_nodes_ips = allocated_nodes_ips[1].split(':')
            break

    print(allocated_nodes_ips)

    serverHostname = fileTransfer['ServerHostname']
    sharedBasepath = fileTransfer['SharedBasepath']
    credentials = fileTransfer['Credentials']
    username = credentials['UserName']

    key_file = str(get_ssh_key_file())
    destination = '%s@%s' % (username, serverHostname)
    print('connect to server')

    allocated_nodes_ips = allocated_nodes_ips[0]
    if 'mic' in allocated_nodes_ips:
        allocated_nodes_ips = '%s.head' % allocated_nodes_ips
    port1 = '7000:%s:7000' % (allocated_nodes_ips)
    port2 = '7001:%s:7001' % (allocated_nodes_ips)

    await _ssh_tunnel(key_file, destination, port1, port2)

##################################################################################
##################################################################################    
async def _ssh_async(key_file, server, username, command):
    """ Execute an ssh command """

    if username is None:
        user_server = '%s' % (server)
    else:
        user_server = '%s@%s' % (username, server)        

    if key_file is None:
        cmd = [
            'ssh',
            user_server, command
        ]
    else:
        cmd = [
            'ssh',
            '-i',  key_file,
            user_server, command
        ]

    # import asyncio
    # loop = asyncio.get_event_loop()
    # process = await asyncio.create_subprocess_exec(*cmd, 
    #     loop=loop,
    #     stdout=asyncio.subprocess.PIPE,
    #     stderr=asyncio.subprocess.PIPE)
        
    import asyncio
    process = await asyncio.create_subprocess_exec(
        *cmd, 
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)        

    #await process.wait()
    #password = '{}\n'.format(password).encode()
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        if stdout:
            print(f'[stdout]\n{stdout.decode()}')
        if stderr:
            print(f'[stderr]\n{stderr.decode()}')        

        raise Exception("ssh command failed: %s" % cmd)

    return str(stdout.decode())

def _ssh_sync(key_file, server, username, command):
    """ Execute an ssh command """

    if username is None:
        user_server = '%s' % (server)
    else:
        user_server = '%s@%s' % (username, server)        

    if key_file is None:
        cmd = [
            'ssh',
            user_server, command
        ]
    else:
        cmd = [
            'ssh',
            '-i',  key_file,
            user_server, command
        ]

    import subprocess
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    # stdout=proc.stdout.read()
    # stderr=proc.stderr.read()
    stdout, stderr = process.communicate()

    if process.returncode != 0:
        if stdout:
            print(str(stdout.decode()))
        if stderr:
            print(str(stderr.decode()))        

        raise Exception("ssh command failed: %s" % cmd)

    return str(stdout.decode())    

# async def _ssh_system(server, command):
#     """ Execute an ssh command """
#     cmd = [
#         'ssh',
#         server, command
#     ]

#     import asyncio
#     loop = asyncio.get_event_loop()
#     process = await asyncio.create_subprocess_exec(*cmd, 
#         loop=loop,
#         stdin=asyncio.subprocess.PIPE,
#         stdout=asyncio.subprocess.PIPE,
#         stderr=asyncio.subprocess.PIPE)

#     #await process.wait()
#     # password = '{}\n'.format(password).encode()
#     stdout, stderr = await process.communicate()

#     if process.returncode != 0:
#         if stdout:
#             print(f'[stdout]\n{stdout.decode()}')
#         if stderr:
#             print(f'[stderr]\n{stderr.decode()}')        

#         raise Exception("ssh command failed: %s" % cmd)

#     return str(stdout.decode())    

def _paramiko_ssh(server, username, key_file, key_file_password, password, use_password, command):
        """ Execute an paramiko ssh command """

        import paramiko
        #from io import StringIO
        #from base64 import b64decode
        #from scp import SCPClient

        bpy.context.scene.raas_session.show_dialog(server, username, key_file, key_file_password, password, use_password)

        #ssh = None
        result = None
        try: 
            # ssh = paramiko.SSHClient()
            # ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            # try:
            #     key = paramiko.RSAKey.from_private_key_file(key_file, password)
            # except:
            #     key = paramiko.Ed25519Key.from_private_key_file(key_file, password)

            #ssh.connect(server, username=username, pkey=key)
            ssh = bpy.context.scene.raas_session.paramiko_get_ssh(server)
            stdin, stdout, stderr = ssh.exec_command(command)
            result = stdout.readlines()
            error = stderr.readlines()            

            if len(error) > 0 and (len(error) > 1 or 'load bsc' not in error[0]):
                raise Exception(str(error))

            #ssh.close()    

        except Exception as e:
            # if scp is not None:
            #     scp.close()

            # if ssh is not None:
            #     ssh.close()
            #bpy.context.scene.raas_session.create_session(None)

            raise Exception("paramiko ssh command failed:  %s: %s" % (e.__class__, e))    

        return ''.join(result)

async def ssh_command(server, command, preset):
    if command  is None:
        return None
    
    #pref = raas_pref.preferences()
    #preset = pref.cluster_presets[bpy.context.scene.raas_cluster_presets_index]    
            
    username = preset.raas_da_username
    key_file = preset.raas_private_key_path
    key_file_password = preset.raas_private_key_password
    password = preset.raas_da_password
    use_password = preset.raas_da_use_password
    
    if preset.raas_ssh_library == 'PARAMIKO':
        return _paramiko_ssh(server, username, key_file, key_file_password, password, use_password, command)
    else:
        return await _ssh_async(None, server, None, command)

def ssh_command_sync(server, command, preset):
    if command  is None:
        return None
        
    #pref = raas_pref.preferences()
    #preset = pref.cluster_presets[bpy.context.scene.raas_cluster_presets_index]    
        
    username = preset.raas_da_username
    key_file = preset.raas_private_key_path
    key_file_password = preset.raas_private_key_password
    password = preset.raas_da_password
    use_password = preset.raas_da_use_password
    
    if preset.raas_ssh_library == 'PARAMIKO':
        return _paramiko_ssh(server, username, key_file, key_file_password, password, use_password, command)
    else:
        return _ssh_sync(None, server, None, command)
                  
####################################FileTransfer#############################
#############################################################################  

async def _scp_async(key_file, source, destination):
        """ Execute an scp command """

        if key_file is None:
            cmd = [
                'scp',
                '-o', 'StrictHostKeyChecking=no',
                '-q',
                '-B',
                '-r',
                source, destination
            ]            
        else:
            cmd = [
                'scp',
                '-i',  key_file,
                '-o', 'StrictHostKeyChecking=no',
                '-q',
                '-B',
                '-r',
                source, destination
            ]

        import asyncio
        #loop = asyncio.get_event_loop()
        process = await asyncio.create_subprocess_exec(*cmd, 
            #loop=loop,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)

        #await process.wait()
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            if stdout:
                print(f'[stdout]\n{stdout.decode()}')
            if stderr:
                print(f'[stderr]\n{stderr.decode()}')        

            if is_verbose_debug() == True:
                raise Exception("scp command failed: %s" % cmd)
            else:
                raise Exception("scp command failed: %s -> %s" % (source, destination))

def _paramiko_put(server, username, key_file, key_file_password, password, use_password, source, destination):
        """ Execute an paramiko command """

        import paramiko
        from io import StringIO
        from base64 import b64decode
        from scp import SCPClient

        bpy.context.scene.raas_session.show_dialog(server, username, key_file, key_file_password, password, use_password)

        ssh = None
        scp = None
        try: 
            # ssh = paramiko.SSHClient()
            # ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            # # if password is None:
            # #     key = paramiko.RSAKey.from_private_key(StringIO(privateKey))
            # # else:
            # #     key = paramiko.RSAKey.from_private_key_file(privateKey, password)

            # try:
            #     #key = paramiko.RSAKey.from_private_key_file(key_file, password)

            #     if password is None:
            #         key = paramiko.RSAKey.from_private_key(StringIO(privateKey))
            #     else:
            #         key = paramiko.RSAKey.from_private_key_file(privateKey, password)

            # except:
            #     #key = paramiko.Ed25519Key.from_private_key_file(key_file, password)                
            #     if password is None:
            #         key = paramiko.Ed25519Key.from_private_key(StringIO(privateKey))
            #     else:
            #         key = paramiko.Ed25519Key.from_private_key_file(privateKey, password)

            # ssh.connect(serverHostname, username=username, pkey=key)
            ssh = bpy.context.scene.raas_session.paramiko_get_ssh(server)
            scp = SCPClient(ssh.get_transport())
            scp.put(source, recursive=True, remote_path=destination)       
            #scp.close()    

        except Exception as e:
            # if scp is not None:
            #     scp.close()

            # if ssh is not None:
            #     ssh.close()

            raise Exception("paramiko command failed:  %s: %s" % (e.__class__, e))


def _paramiko_get(server, username, key_file, key_file_password, password, use_password, source, destination):
        """ Execute an paramiko command """

        import paramiko
        from io import StringIO
        from base64 import b64decode
        from scp import SCPClient

        bpy.context.scene.raas_session.show_dialog(server, username, key_file, key_file_password, password, use_password)

        ssh = None
        scp = None
        try: 
            # ssh = paramiko.SSHClient()
            # ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            # # if password is None:
            # #     key = paramiko.RSAKey.from_private_key(StringIO(privateKey))
            # # else:
            # #     key = paramiko.RSAKey.from_private_key_file(privateKey, password)

            # try:
            #     #key = paramiko.RSAKey.from_private_key_file(key_file, password)
            #     if password is None:
            #         key = paramiko.RSAKey.from_private_key(StringIO(privateKey))
            #     else:
            #         key = paramiko.RSAKey.from_private_key_file(privateKey, password)                
            # except:
            #     #key = paramiko.Ed25519Key.from_private_key_file(key_file, password)
            #     if password is None:
            #         key = paramiko.Ed25519Key.from_private_key(StringIO(privateKey))
            #     else:
            #         key = paramiko.Ed25519Key.from_private_key_file(privateKey, password)                

            # ssh.connect(serverHostname, username=username, pkey=key)
            ssh = bpy.context.scene.raas_session.paramiko_get_ssh(server)
            scp = SCPClient(ssh.get_transport())
            scp.get(source, local_path=destination, recursive=True)
            #scp.close()

        except Exception as e:
            # if scp is not None:
            #     scp.close()

            # if ssh is not None:
            #     ssh.close()

            raise Exception("paramiko command failed:  %s: %s" % (e.__class__, e))        


async def start_transfer_files(context, job_id: int, token: str) -> None:
    """Start Transfer files."""   

    return None


async def end_transfer_files(context, fileTransfer, job_id: int, token: str) -> None:
    """End Transfer files."""    

    return None
  

async def transfer_files(context, fileTransfer, job_local_dir: str, job_remote_dir: str, job_id: int, token: str, to_cluster) -> None:
    """Transfer files."""

    prefs = raas_pref.preferences()
    preset = prefs.cluster_presets[bpy.context.scene.raas_cluster_presets_index]

    serverHostname = raas_config.GetDAServer(context)
    cmd = CmdCreateProjectGroupFolder(context)
    
    await ssh_command(serverHostname, cmd, preset)

    sharedBasepath = get_direct_access_remote_storage(context)    
    
    username = preset.raas_da_username
    key_file = preset.raas_private_key_path
    key_file_password = preset.raas_private_key_password
    password = preset.raas_da_password
    use_password = preset.raas_da_use_password

    # check job_local_dir
    if to_cluster == False:
        job_local_dir_check = Path(job_local_dir)
        job_local_dir_check.mkdir(parents=True, exist_ok=True)
    
    if preset.raas_ssh_library == 'PARAMIKO':
        if to_cluster == True:
            source = job_local_dir
            destination = '%s/%s' % (str(sharedBasepath), job_remote_dir)
            print('copy from %s to server' % (job_local_dir))
            #await _paramiko_put(pkey, serverHostname, username, password, source, destination)
            await asyncio.to_thread(_paramiko_put, serverHostname, username, key_file, key_file_password, password, use_password, source, destination)
        else:
            destination = job_local_dir
            source = '%s/%s' % (str(sharedBasepath), job_remote_dir)
            print('copy from server to: %s' % (job_local_dir))
            #await _paramiko_get(pkey, serverHostname, username, password, source, destination)
            await asyncio.to_thread(_paramiko_get, serverHostname, username, key_file, key_file_password, password, use_password, source, destination)

    else:       
        if to_cluster == True:
            source = job_local_dir
            destination = '%s:%s/%s' % (serverHostname, str(sharedBasepath), job_remote_dir)
            print('copy from %s to server' % (job_local_dir))
        else:
            destination = job_local_dir
            source = '%s:%s/%s' % (serverHostname, str(sharedBasepath), job_remote_dir)
            print('copy from server to: %s' % (job_local_dir))

        await _scp_async(None, source, destination)
            

async def transfer_files_to_cluster(context, fileTransfer, job_local_dir: str, job_remote_dir: str, job_id: int, token: str) -> None:
    """Transfer files."""

    await transfer_files(context, fileTransfer, job_local_dir, job_remote_dir, job_id, token, True)

async def transfer_files_from_cluster(context, fileTransfer, job_remote_dir: str, job_local_dir: str, job_id: int, token: str) -> None:
    """Transfer files."""

    await transfer_files(context, fileTransfer, job_local_dir, job_remote_dir, job_id, token, False)

##################################################################################  
class RAAS_OT_download_files(
                        async_loop.AsyncModalOperatorMixin,
                        AuthenticatedRaasOperatorMixin,                         
                        Operator):
    """download_files"""
    bl_idname = 'raas.download_files'
    bl_label = 'Download Files'

    log = logging.getLogger('%s.RAAS_OT_download_files' % __name__)

    async def async_execute(self, context):

        if not await self.authenticate(context):
            self.quit()
            return 

        idx = context.scene.raas_list_jobs_index 

        if idx != -1 and len(context.scene.raas_list_jobs) > 0:
            try:
                item = context.scene.raas_list_jobs[idx]

                fileTransfer = await start_transfer_files(context, item.Id, self.token)
 
                remote_storage_out = convert_path_to_linux(item.Name) + '/out'
                local_storage_out = get_job_local_storage(item.Name)
                
                await transfer_files_from_cluster(context, fileTransfer, remote_storage_out, str(local_storage_out), item.Id, self.token)    

                remote_storage_log = convert_path_to_linux(item.Name) + '/log'
                local_storage_log = get_job_local_storage(item.Name)
                
                await transfer_files_from_cluster(context, fileTransfer, remote_storage_log, str(local_storage_log), item.Id, self.token)  

                await end_transfer_files(context, fileTransfer, item.Id, self.token)
            
            except Exception as e:
                import traceback
                traceback.print_exc()

                self.report({'ERROR'}, "Problem with downloading files: %s: %s" % (e.__class__, e))
                context.window_manager.raas_status = "ERROR"
                context.window_manager.raas_status_txt = "There is an error! Check Info Editor!"

        self.quit()

class RAAS_OT_connect_to_client(
                        async_loop.AsyncModalOperatorMixin,
                        AuthenticatedRaasOperatorMixin,                         
                        Operator):
    """connect_to_client"""
    bl_idname = 'raas.connect_to_client'
    bl_label = 'Connect to client'

    #stop_upon_exception = True
    log = logging.getLogger('%s.RAAS_OT_connect_to_client' % __name__)

    async def async_execute(self, context):

        if not await self.authenticate(context):
            self.quit()
            return 

        idx = context.scene.raas_list_jobs_index 

        if idx != -1:
            try:
                item = context.scene.raas_list_jobs[idx]

                fileTransfer = await start_transfer_files(context, item.Id, self.token)
                
                await connect_to_client(context, fileTransfer, item.Id, self.token)

            except Exception as e:
                #print('Problem with downloading files:')
                #print(e)
                import traceback
                traceback.print_exc()

                self.report({'ERROR'}, "Problem with connecting to the client: %s: %s" % (e.__class__, e))
                context.window_manager.raas_status = "ERROR"
                context.window_manager.raas_status_txt = "There is an error! Check Info Editor!"


        self.quit()  


class RAAS_OT_dash_barbora(
                        async_loop.AsyncModalOperatorMixin,
                        AuthenticatedRaasOperatorMixin,                         
                        Operator):
    """dash_barbora"""
    bl_idname = 'raas.dash_barbora'
    bl_label = 'Dashboard of the Barbora cluster'

    async def async_execute(self, context):
        import webbrowser
        webbrowser.open('https://extranet.it4i.cz/dash/barbora', new=2)

        self.quit()

class RAAS_OT_dash_karolina(
                        async_loop.AsyncModalOperatorMixin,
                        AuthenticatedRaasOperatorMixin,                         
                        Operator):
    """dash_karolina"""
    bl_idname = 'raas.dash_karolina'
    bl_label = 'Dashboard of the Karolina cluster'

    async def async_execute(self, context):
        import webbrowser
        webbrowser.open('https://extranet.it4i.cz/dash/karolina', new=2)

        self.quit()


# class RAAS_OT_dash_grafana(
#         async_loop.AsyncModalOperatorMixin,
#         AuthenticatedRaasOperatorMixin,
#         Operator):
#     """dash_grafana"""
#     bl_idname = 'raas.dash_grafana'
#     bl_label = 'Dashboard of the clusters'

#     async def async_execute(self, context):
#         import webbrowser
#         webbrowser.open('https://extranet.it4i.cz/grafana', new=2)

#         self.quit()

class RAAS_OT_submit_job(
                        async_loop.AsyncModalOperatorMixin,
                        AuthenticatedRaasOperatorMixin,                         
                        Operator):
    """submit_job"""
    bl_idname = 'raas.submit_job'
    bl_label = 'Submit job'

    #stop_upon_exception = True
    log = logging.getLogger('%s.RAAS_OT_submit_job' % __name__)

    # quit_after_submit = BoolProperty()

    async def async_execute(self, context):  
        try:
            update_job_info_preset(context)
            # Refuse to start if the file hasn't been saved. It's okay if
            # it's dirty, but we do need a filename and a location.
            if context.scene.raas_blender_job_info_new.file_type == 'DEFAULT':
                if not os.path.exists(context.blend_data.filepath):
                    self.report({'ERROR'}, 'Please save your Blend file before using the braas-hpc addon.')
                    context.window_manager.raas_status = "ERROR"
                    context.window_manager.raas_status_txt = "There is an error! Check Info Editor!"

                    self.quit()
                    return

                #context.scene.raas_blender_job_info_new.blendfile_path = context.blend_data.filepath
            else:
                if not os.path.exists(get_blendfile_fullpath(context)):
                    self.report({'ERROR'}, 'Blend file does not exist.')
                    context.window_manager.raas_status = "ERROR"
                    context.window_manager.raas_status_txt = "There is an error! Check Info Editor!"

                    self.quit()
                    return

            if not await self.authenticate(context):
                self.quit()
                return            

            #scene = context.scene
            prefs = raas_pref.preferences()

            if prefs.cluster_presets[context.scene.raas_cluster_presets_index].is_active == False:
                self.report({'ERROR'}, 'Selected configuration is not active.')
                context.window_manager.raas_status = "ERROR"
                context.window_manager.raas_status_txt = "There is an error! Check Info Editor!"

                self.quit()
                return

            # Check the configuration was selected
            if context.scene.raas_blender_job_info_new.cluster_type == "" or \
                context.scene.raas_blender_job_info_new.job_partition == "" or \
                    context.scene.raas_blender_job_info_new.job_allocation == "":                
                self.report({'ERROR'}, 'Select a configuration (cluster, partition, allocation).')
                context.window_manager.raas_status = "ERROR"
                context.window_manager.raas_status_txt = "There is an error! Check Info Editor!"

                self.quit()
                return

            # Check or create a project name (task)
            if context.scene.raas_blender_job_info_new.job_project is None or \
                len(context.scene.raas_blender_job_info_new.job_project) == 0:
                context.scene.raas_blender_job_info_new.job_project = Path(context.blend_data.filepath).stem

            context.scene.raas_blender_job_info_new.job_project = context.scene.raas_blender_job_info_new.job_project.replace(" ","_").replace("\\","_").replace("/","_").replace("'","_").replace('"','_')

            # Name directories
            from datetime import datetime
            dt = datetime.now().isoformat('-').replace(':', '').replace('.', '')
            unique_dir = '%s-%s' % (dt[0:19], context.scene.raas_blender_job_info_new.job_project)
            outdir = Path(prefs.raas_job_storage_path) / unique_dir / 'in'
            outdir.mkdir(parents=True)

            if context.scene.raas_blender_job_info_new.file_type == 'DEFAULT':
                # Save to a different file, specifically for Raas.
                context.window_manager.raas_status = 'SAVING'
                filepath = await self._save_blendfile(context, outdir)
                context.scene.raas_blender_job_info_new.blendfile = filepath.name

            else: #OTHER
                filepath = Path(get_blendfile_fullpath(context)).with_suffix('.blend')        

            if context.scene.raas_blender_job_info_new.file_type == 'DEFAULT':
                # BAT-pack the files to the destination directory.
                missing_sources = await self.bat_pack(filepath, context.scene.raas_blender_job_info_new.job_project, outdir)

                # remove files
                self.log.info("Removing temporary file %s", filepath)
                filepath.unlink()                
            else:
                missing_sources = None

                from distutils.dir_util import copy_tree
                copy_tree(bpy.path.abspath(context.scene.raas_blender_job_info_new.blendfile_dir), str(outdir))

            # Image/animation info
            #context.scene.raas_blender_job_info_new.frame_step = context.scene.frame_step
            context.scene.raas_blender_job_info_new.frame_start = context.scene.frame_start
            context.scene.raas_blender_job_info_new.frame_end = context.scene.frame_end
            context.scene.raas_blender_job_info_new.frame_current = context.scene.frame_current

            context.scene.raas_blender_job_info_new.job_name = unique_dir
            job_type = prefs.cluster_presets[context.scene.raas_cluster_presets_index].job_type
            context.scene.raas_blender_job_info_new.job_type = job_type

            if context.scene.raas_blender_job_info_new.job_type == 'GPUINTERACTIVE':
                context.scene.raas_blender_job_info_new.job_project = 'INTERACTIVE'    

            # Do a final report.
            if missing_sources:
                names = (ms.name for ms in missing_sources)
                self.report({'WARNING'}, 'Raas job created with missing files: %s' %
                            '; '.join(names
                            ))

            await raas_config.CreateJob(context, self.token)  
            
            blender_job_info_new = context.scene.raas_blender_job_info_new

            local_storage_in = str(get_job_local_storage(blender_job_info_new.job_name))
            remote_storage_in = convert_path_to_linux(get_job_remote_storage(blender_job_info_new.job_name))

            submitted_job_info_ext_new = context.scene.raas_submitted_job_info_ext_new

            fileTransfer = await start_transfer_files(context, submitted_job_info_ext_new.Id, self.token)
            await transfer_files_to_cluster(context, fileTransfer, local_storage_in, remote_storage_in, submitted_job_info_ext_new.Id, self.token)
            await end_transfer_files(context, fileTransfer, submitted_job_info_ext_new.Id, self.token)

            item = context.scene.raas_submitted_job_info_ext_new
            asyncio.gather(ListSchedulerJobsForCurrentUser(context, self.token))
            
            await asyncio.gather(SubmitJob(context, self.token))
            
            await ListSchedulerJobsForCurrentUser(context, self.token)

            self.report({'INFO'}, 'Please refresh the list of tasks.')

        except Exception as e:
            import traceback
            traceback.print_exc()

            self.report({'ERROR'}, "Problem with submitting of job: %s: %s" % (e.__class__, e))
            context.window_manager.raas_status = "ERROR"
            context.window_manager.raas_status_txt = "There is an error! Check Info Editor!"

        self.quit()

    async def _save_blendfile(self, context, outdir):
        """Save to a different file, specifically for Raas.

        We shouldn't overwrite the artist's file.
        We can compress, since this file won't be managed by SVN and doesn't need diffability.
        """

        render = context.scene.render

        # Remember settings we need to restore after saving.
        old_use_file_extension = render.use_file_extension
        old_use_overwrite = render.use_overwrite
        old_use_placeholder = render.use_placeholder

        disable_denoiser = False
        if disable_denoiser:
            use_denoising = [layer.cycles.use_denoising
                             for layer in context.scene.view_layers]
        else:
            use_denoising = []

        #check VDB
        # from . import bat_interface
        # vdb_list = bat_interface.copy_vdb(outdir)
        # for vdb in vdb_list:
        #     vdb[0].filepath = vdb[2]

        try:

            # The file extension should be determined by the render settings, not necessarily
            # by the setttings in the output panel.
            render.use_file_extension = True

            # Rescheduling should not overwrite existing frames.
            render.use_overwrite = False
            render.use_placeholder = False

            if disable_denoiser:
                for layer in context.scene.view_layers:
                    layer.cycles.use_denoising = False

            filepath = Path(context.blend_data.filepath).with_suffix('.braas-hpc.blend')

            # Step 1: First save the file
            self.log.info('Saving initial copy to temporary file %s', filepath)
            bpy.ops.wm.save_as_mainfile(filepath=str(filepath),
                                        compress=True,
                                        copy=True)
            
            # Step 2: Pack all external files into the blend file
            self.log.info('Packing external files into blend file')
            bpy.ops.file.pack_all()
            
            # Step 3: Save again with packed files
            self.log.info('Saving final copy with packed files to %s', filepath)
            bpy.ops.wm.save_as_mainfile(filepath=str(filepath),
                                        compress=True,
                                        copy=True)
        finally:
            # Restore the settings we changed, even after an exception.
            # for vdb in vdb_list:
            #     vdb[0].filepath = vdb[1]

            render.use_file_extension = old_use_file_extension
            render.use_overwrite = old_use_overwrite
            render.use_placeholder = old_use_placeholder

            if disable_denoiser:
                for denoise, layer in zip(use_denoising, context.scene.view_layers):
                    layer.cycles.use_denoising = denoise

            #filepath_orig = Path(context.blend_data.filepath).with_suffix('.blend')
            #bpy.ops.wm.save_mainfile(filepath=str(context.blend_data.filepath))

        return filepath

    async def bat_pack(self, filepath, project, outdir):
        """BAT-packs the blendfile to the destination directory.

        Returns the path of the destination blend file.

        :param job_id: the job ID given to us by Raas Server.
        :param filepath: the blend file to pack (i.e. the current blend file)
        :returns: A tuple of:
            - The destination directory, or None if it does not exist on a
              locally-reachable filesystem (for example when sending files to
              a Shaman server).
            - The destination blend file, or None if there were errors BAT-packing,
            - A list of missing paths.
        """

        from datetime import datetime
        #from . import bat_interface

        prefs = raas_pref.preferences()

        #proj_abspath = bpy.path.abspath(prefs.raas_project_local_path)
        proj_abspath = bpy.path.abspath('//./')
        projdir = Path(proj_abspath).resolve()
        exclusion_filter = '*.vdb' #(prefs.raas_exclude_filter or '').strip()
        relative_only = False #prefs.raas_relative_only

        self.log.debug('projdir: %s', projdir)

        # dt = datetime.now().isoformat('-').replace(':', '').replace('.', '')
        # unique_dir = '%s-%s' % (dt[0:19], project)
        # outdir = Path(prefs.raas_job_storage_path) / unique_dir / 'in'

        self.log.debug('outdir : %s', outdir)

        # try:
        #     outdir.mkdir(parents=True)
        # except Exception as ex:
        #     self.log.exception('Unable to create output path %s', outdir)
        #     self.report({'ERROR'}, 'Unable to create output path: %s' % ex)
        #     self.quit()
        #     return outdir, None, []

        # try:
        #     outfile, missing_sources = await bat_interface.copy(
        #         bpy.context, filepath, projdir, outdir, exclusion_filter,
        #         relative_only=relative_only)
        # except bat_interface.FileTransferError as ex:
        #     self.log.error('Could not pack %d files, starting with %s',
        #                    len(ex.files_remaining), ex.files_remaining[0])
        #     self.report({'ERROR'}, 'Unable to pack %d files' % len(ex.files_remaining))
        #     bpy.context.window_manager.raas_status = "ERROR"
        #     bpy.context.window_manager.raas_status_txt = "There is an error! Check Info Editor!"

        #     self.quit()
        #     return None
        # except bat_interface.Aborted:
        #     self.log.warning('BAT Pack was aborted')
        #     self.report({'WARNING'}, 'Aborted Raas file packing/transferring')
        #     self.quit()
        #     return None

        # Step 4: Copy the packed file to the output directory        
        final_filepath = outdir / Path(filepath).name
        self.log.info('Copying packed file from %s to %s', filepath, final_filepath)
        import shutil
        shutil.copy2(str(filepath), str(final_filepath))

        missing_sources = None
        bpy.context.window_manager.raas_status = 'PARTIAL_DONE'
        return missing_sources

class RAAS_OT_abort(Operator):
    """Aborts a running Raas file packing/transfer operation.
    """
    bl_idname = 'raas.abort'
    bl_label = 'Abort'

    @classmethod
    def poll(cls, context):
        return context.window_manager.raas_status != 'ABORTING'

    def execute(self, context):
        context.window_manager.raas_status = 'ABORTING'
        # from . import bat_interface
        # bat_interface.abort()
        return {'FINISHED'}


class RAAS_OT_explore_file_path(Operator):
    """Opens the Raas job storage path in a file explorer.

    If the path cannot be found, this operator tries to open its parent.
    """

    bl_idname = 'raas.explore_file_path'
    bl_label = 'Open in file explorer'

    path: StringProperty(name='Path', description='Path to explore', subtype='DIR_PATH')

    def execute(self, context):
        import platform
        import pathlib

        # Possibly open a parent of the path
        to_open = pathlib.Path(self.path)
        while to_open.parent != to_open:  # while we're not at the root
            if to_open.exists():
                break
            to_open = to_open.parent
        else:
            self.report({'ERROR'}, 'Unable to open %s or any of its parents.' % self.path)
            context.window_manager.raas_status = "ERROR"
            context.window_manager.raas_status_txt = "There is an error! Check Info Editor!"

            return {'CANCELLED'}
        to_open = str(to_open)

        if platform.system() == "Windows":
            import os
            os.startfile(to_open)

        elif platform.system() == "Darwin":
            import subprocess
            subprocess.Popen(["open", to_open])

        else:
            import subprocess
            subprocess.Popen(["xdg-open", to_open])

        return {'FINISHED'}

# class RAAS_PT_MessageOfTheDay(RaasButtonsPanel, Panel):
#     bl_label = "Dashboards"
#     bl_parent_id = "RAAS_PT_simplify"

#     def draw(self, context):
#         layout = self.layout
#         box = layout.box()

#         # box.operator(RAAS_OT_dash_barbora.bl_idname,                                 
#         #                     text='Barbora', icon='WORLD')

#         # box.operator(RAAS_OT_dash_karolina.bl_idname,
#         #                     text='Karolina', icon='WORLD')

#         box.operator(RAAS_OT_dash_grafana.bl_idname,
#                             text='Grafana', icon='WORLD')                                                        

# class RAAS_PT_Report(RaasButtonsPanel, Panel):
#     bl_label = "Report"
#     bl_parent_id = "RAAS_PT_simplify"

#     def draw(self, context):
#         layout = self.layout
#         box = layout.box()

#         box.prop(context.scene, "raas_total_core_hours_usage")

#         box.operator(RAAS_OT_GetUserGroupResourceUsageReport.bl_idname,
#                             text='Core Hours Usage')


class RAAS_UL_ClusterPresets(bpy.types.UIList):
    '''Draws table items - allocation, cluster and partition name.'''
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if item.is_active:
            layout.label(text=item.allocation_name)
            layout.label(text=raas_config.Cluster_items_dict[item.cluster_name])
            layout.label(text=item.partition_name)
            layout.label(text=raas_config.JobQueue_items_dict[item.job_type])
        else:
            layout.label(text='NON-ACTIVE')
            layout.label(text=raas_config.Cluster_items_dict[item.cluster_name])
            layout.label(text=item.partition_name)
            layout.label(text=raas_config.JobQueue_items_dict[item.job_type])


    def filter_items(self, context, data, propname): 
        """Custom filter and order items in the list.""" 
        
        filtered = []
        ordered = []

        items = getattr(data, propname)
        filtered = [0] * len(items)

        for i, item in enumerate(items):
            if (self.filter_name.lower() in item.allocation_name.lower() or 
                self.filter_name.lower() in item.cluster_name.lower() or
                self.filter_name.lower() in item.partition_name.lower()):
                filtered[i] |= self.bitflag_filter_item

        return filtered, ordered

    
def update_job_info_preset(context):
    '''
        This method updates RAAS_PG_BlenderJobInfo (cluster, queue, allocation, directory).
        This has to be called before accessing the cluster! I.e, before submission and monitoring -> the table of 
        cluster presets controls what cluster to access.
    '''
    # Access the property group instance
    my_property_group = context.scene.raas_blender_job_info_new

    addon_prefs = raas_pref.preferences()
    if context.scene.raas_cluster_presets_index > -1 and len(addon_prefs.cluster_presets) > 0:
        preset = addon_prefs.cluster_presets[context.scene.raas_cluster_presets_index]
        # Update the property values
        my_property_group.job_remote_dir = preset.working_dir
        my_property_group.cluster_type = preset.cluster_name
        my_property_group.job_partition = preset.partition_name
        my_property_group.job_allocation = preset.allocation_name


class RAAS_PT_NewJob(RaasButtonsPanel, Panel):
    bl_label = "New Job"
    bl_parent_id = "RAAS_PT_simplify"

    def draw(self, context):
        layout = self.layout

        if context.window_manager.raas_status in {'IDLE', 'ERROR',  'DONE'}:
            layout.enabled = True
        else:
            layout.enabled = False          

        #prefs = raas_pref.preferences()

        #################################################

        # Header ----------------------------------------
        box = layout.box()
        row = box.row()   
        col = row.column()        
        col.label(text="Allocation")
        col = row.column()        
        col.label(text="Cluster")
        col = row.column()        
        col.label(text="Partition")
        col = row.column()        
        col.label(text="Type")

        # Content ----------------------------------------
        box = layout.box()
        paths_layout = box.column(align=True)
        blender_job_info_new = context.scene.raas_blender_job_info_new        
        job_info_col = paths_layout.column()
        
        # Table with HPCs
        addonprefs = raas_pref.preferences()
        job_info_col.template_list("RAAS_UL_ClusterPresets", "", addonprefs, "cluster_presets", 
                                   context.scene, "raas_cluster_presets_index")
        #if context.scene.raas_cluster_presets_index >= 0:
        #    blender_job_info_new.job_remote_dir = addonprefs.cluster_presets[context.scene.raas_cluster_presets_index].working_dir
        
        # Other settings
        #job_info_col.prop(blender_job_info_new, 'job_type')
        job_info_col.prop(blender_job_info_new, 'job_project')
        job_info_col.prop(blender_job_info_new, 'job_email')
        job_info_col.prop(blender_job_info_new, 'render_type')
        col = job_info_col.box()
        col = col.column(align=True)  
        col.prop(blender_job_info_new, 'file_type')
        if blender_job_info_new.file_type == 'OTHER':
            col.prop(blender_job_info_new, 'blendfile_dir')
            col.prop(blender_job_info_new, 'blendfile')                    
        
        col = job_info_col.column(align=True)              
        col.prop(blender_job_info_new, 'job_walltime')                      

        if blender_job_info_new.render_type == 'IMAGE':
            col = job_info_col.column(align=True)            
            col.prop(context.scene, 'frame_current')                            
        else:
            #col = job_info_col.column(align=True)
            col.prop(blender_job_info_new, 'max_jobs')                        
            col = job_info_col.column(align=True)   
            col.prop(context.scene, "frame_start")
            col.prop(context.scene, "frame_end")    
            #col.prop(context.scene, "frame_step")
            col = job_info_col.column(align=True)
            col.prop(blender_job_info_new, 'job_arrays')

        box.operator(RAAS_OT_submit_job.bl_idname,
                            text='Submit Job',
                            icon='RENDER_ANIMATION')


##########################################################################
async def GetCurrentInfoForJob(context, job_id: int, token: str) -> None:
    """GetCurrentInfoForJob"""       

    data = {
        "SubmittedJobInfoId": job_id,
        "SessionCode": token
    }

    info_job = await raas_server.post("JobManagement/GetCurrentInfoForJob", data)

    return  info_job  

class RAAS_OT_GetCurrentInfoForJob(
                        async_loop.AsyncModalOperatorMixin,
                        AuthenticatedRaasOperatorMixin,                         
                        Operator):  
    """GetCurrentInfoForJob"""
    bl_idname = 'raas.get_current_info_for_job'
    bl_label = 'Get Current Info For Job'

    async def async_execute(self, context):

        if not await self.authenticate(context):
            self.quit()
            return

        try:        
            await GetCurrentInfoForJob(context, self.token)
        except Exception as e:
            import traceback
            traceback.print_exc()

            self.report({'ERROR'}, "Problem with getting curent jobinfo: %s: %s" % (e.__class__, e))            
            context.window_manager.raas_status = "ERROR"
            context.window_manager.raas_status_txt = "There is an error! Check Info Editor!"

        self.quit()     
##########################################################################
async def GetUserGroupResourceUsageReport(context, token):
        data = {
                "GroupId": 1,
                "StartTime": "2000-01-01T12:00:00.000Z",
                "EndTime": "2100-01-01T12:00:00.000Z",
                "SessionCode" : token
        }

        resp_json = await raas_server.post("JobReporting/GetUserGroupResourceUsageReport", data)
        pass
        

class RAAS_OT_GetUserGroupResourceUsageReport(
                        async_loop.AsyncModalOperatorMixin,
                        AuthenticatedRaasOperatorMixin,                         
                        Operator):  
    """returns a resource usage for user group"""
    bl_idname = 'raas.get_user_group_resource_usage_report'
    bl_label = 'Get User Group Resource Usage Report'

    async def async_execute(self, context):

        if not await self.authenticate(context):
            self.quit()
            return        

        try:
            await GetUserGroupResourceUsageReport(context, self.token)
        except Exception as e:
            import traceback
            traceback.print_exc()

            self.report({'ERROR'}, "Problem with getting report: %s: %s" % (e.__class__, e))               
            context.window_manager.raas_status = "ERROR"
            context.window_manager.raas_status_txt = "There is an error! Check Info Editor!"


        self.quit() 

##########################################################################  
# async def ListJobsForCurrentUser(context, token):

#     # Id : bpy.props.IntProperty(name="Id")
#     # Name : bpy.props.StringProperty(name="Name")
#     # State : bpy.props.EnumProperty(items=JobStateExt_items,name="State")
#     # Priority : bpy.props.EnumProperty(items=JobPriorityExt_items,name="Priority",default='AVERAGE')
#     # Project : bpy.props.StringProperty(name="Project Name")
#     # CreationTime : bpy.props.StringProperty(name="Creation Time")
#     # SubmitTime : bpy.props.StringProperty(name="Submit Time")
#     # StartTime : bpy.props.StringProperty(name="Start Time")
#     # EndTime : bpy.props.StringProperty(name="End Time")
#     # TotalAllocatedTime : bpy.props.FloatProperty(name="totalAllocatedTime")
#     # AllParameters : bpy.props.StringProperty(name="allParameters")
#     # Tasks: bpy.props.StringProperty(name="Tasks")
#     # ClusterName: bpy.props.StringProperty(name="Cluster Name")
#     server = raas_config.GetDAServer(context)
#     cmd = CmdCreateProjectGroupFolder(context)
#     await ssh_command(server, cmd)
#     remote_path = get_direct_access_remote_storage(context)
#     # spusti se vzdalene
#     cmd = 'cd %s;grep --with-filename -e job_state -e ctime -e stime -e ftime *.job | cat' % (remote_path)
#     # klasicky vystup qstatu
#     try:
#         res = await ssh_command(server, cmd)    
#     except Exception:
#         print("No tasks to refresh in the selected project.")
#         return
#     # rozdeleno na radku, ale trochu jinak
#     #00:'2023-04-18-14073394-test.job:    job_state = H'
#     #01:'2023-04-18-14073394-test.job:    ctime = Tue Apr 18 14:07:49 2023'
#     #02:'2023-04-18-14073394-test.job:    ftime = Tue Apr 18 14:42:56 CEST 2023'
#     lines = res.split('\n')

#     #step = 4
#     index = 0
#     count = len(lines) - 1   
#     raas_list_jobs = []
#     raas_dict_jobs = {}        
#     for i in range(count):
#         line = lines[i]
#         if len(line) > 0:
#             if 'job_state' in line:
#                 #item = context.scene.raas_list_jobs.add()
#                 name = line.split(':')[0][:-4]
#                 if name in raas_dict_jobs: # {'2023-04-18-14073394-test': {'Id': 0, 'Name': '2023-04-18-14073394-test', 'Project': 'test'}}
#                     item = raas_dict_jobs[name]
#                 else:
#                     item = {}
#                     raas_dict_jobs[name] = item
#                     raas_list_jobs.append(item)

#                     item['Id'] = index    
#                     item['Name'] = name
#                     item['Project'] = name[20:]
#                     item['ClusterName'] = context.scene.raas_blender_job_info_new.cluster_type
#                     index = index + 1

#                 state = line.split(' = ')
#                 if len(state) > 0:
#                     state = state[1]
#                 else:
#                     state = ''

#                 # JobStateExt_items = [
#                 #     ("CONFIGURING", "Configuring", "", 1),
#                 #     ("SUBMITTED", "Submitted", "", 2),
#                 #     ("QUEUED", "Queued", "", 4),
#                 #     ("RUNNING", "Running", "", 8),
#                 #     ("FINISHED", "Finished", "", 16),
#                 #     ("FAILED", "Failed", "", 32),
#                 #     ("CANCELED", "Canceled", "", 64),
#                 # ]

#                 item['State'] = 1 #"CONFIGURING"
#                 if state == 'R':
#                     item['State'] = 8 #"RUNNING"
#                 if state == 'Q' or state == 'H':
#                     item['State'] = 4 #"QUEUED"
#                 if state == 'E' or state == 'F':
#                     item['State'] = 16 #"FINISHED"
#                 if state == 'C':
#                     item['State'] = 64 #"CANCELED"

#             if 'ctime' in line:
#                 ctime = line.split(' = ')
#                 if len(ctime) > 0:
#                     ctime = ctime[1]
#                 else:
#                     ctime = ''

#                 item['CreationTime'] = ctime
#                 item['SubmitTime'] = ctime

#         if 'ftime' in line:
#             ftime = line.split(' = ')
#             if len(ftime) > 0:
#                 ftime = ftime[1]
#             else:
#                 ftime = ''
            
#             item['EndTime'] = ftime

#         if 'stime' in line:
#             stime = line.split(' = ')
#             if len(stime) > 0:
#                 stime = stime[1]
#             else:
#                 stime = ''

#             item['StartTime'] = stime

#     context.scene.raas_list_jobs.clear()
#     for key in reversed(raas_list_jobs):
#         item = context.scene.raas_list_jobs.add()
#         raas_server.fill_items(item, key)         

#     if context.scene.raas_list_jobs_index > len(context.scene.raas_list_jobs) - 1:
#         context.scene.raas_list_jobs_index = len(context.scene.raas_list_jobs) - 1
        

# async def ListSlurmJobsForCurrentUser(context, token):
#     """_Lists remote Slurm jobs_.

#     Args:
#         context (_bpy.context_): _Blender context_.
#         token (_type_): _Token_.
#     """

#     # Id : bpy.props.IntProperty(name="Id")
#     # Name : bpy.props.StringProperty(name="Name")
#     # State : bpy.props.EnumProperty(items=JobStateExt_items,name="State")
#     # Priority : bpy.props.EnumProperty(items=JobPriorityExt_items,name="Priority",default='AVERAGE')
#     # Project : bpy.props.StringProperty(name="Project Name")
#     # CreationTime : bpy.props.StringProperty(name="Creation Time")
#     # SubmitTime : bpy.props.StringProperty(name="Submit Time")
#     # StartTime : bpy.props.StringProperty(name="Start Time")
#     # EndTime : bpy.props.StringProperty(name="End Time")
#     # TotalAllocatedTime : bpy.props.FloatProperty(name="totalAllocatedTime")
#     # AllParameters : bpy.props.StringProperty(name="allParameters")
#     # Tasks: bpy.props.StringProperty(name="Tasks")
#     # ClusterName: bpy.props.StringProperty(name="Cluster Name")
#     server = raas_config.GetDAServer(context)
#     cmd = CmdCreateProjectGroupFolder(context)
#     await ssh_command(server, cmd)
#     remote_path = get_direct_access_remote_storage(context)

#     # the command is executed remotly - reads the *.job files in remote_path
#     cmd = 'cd %s;grep --with-filename "" *.job' % (remote_path)
#     # sacct output
#     try:
#         res = await ssh_command(server, cmd)   
#     except Exception:  # There are no files in the remote location -> no tasks have been submitted to the cluster
#         print("No tasks to refresh in the selected project.")
#         context.scene.raas_list_jobs.clear()
#         context.scene.raas_list_jobs_index = -1 
#         return
#     # Example of the read lines 
#     # - the first line is a header -> skip it
#     # - the second line is a separator -> skip it
#     # - only line no. 2 is essential
#     #00:'2023-04-18-14073394-test.job:    JobID           JobName      State              Submit               Start                 End 
#     #01:'2023-04-18-14073394-test.job:    ------------ ---------- ---------- ------------------- ------------------- ------------------- 
#     #02:'2023-04-18-14073394-test.job:    2601              test2  COMPLETED 2023-05-23T14:12:47 2023-05-23T14:12:47 2023-05-23T14:14:28

#     lines = res.split('\n')  # make lines

#     index = 0
#     raas_list_jobs = []
#     raas_dict_jobs = {}     

#     #for lineNo, line in enumerate(lines):
#     line_no = 0
#     while line_no != len(lines):
#         line = lines[line_no]
#         offset = 0
#         if len(line) > 0:
#             elements = line.split()
#             try:
#                 slurmId = elements[1].split('.')
#             except IndexError:
#                 pass  # If the row is somehow ruined, e.g., only a new line
#             else:
#                 tmp = ["----" in e for e in elements[1:]]
#                 onlyTrue = sum(tmp) // len(tmp[1:])  # Used to detect lines with ---- segments only
#                 name = elements[0].split(".")[0]  # '2023-04-18-14073394-test'
#                 item = {}

#                 # Is it a job array?
#                 if len(slurmId[0].split('_')) > 1:  # job array (123_1, 123_2, ...)
#                     final_status, offset = helper_read_slurm_job_array(lines[line_no:])
#                     if name in raas_dict_jobs:
#                         item = raas_dict_jobs[name]
#                     else:
#                         status = map_slurm_status(elements[3])
#                         item = helper_raas_dict_jobs(index, 
#                                                         name, 
#                                                         elements[2], 
#                                                         context.scene.raas_blender_job_info_new.cluster_type,
#                                                         final_status)
#                         raas_dict_jobs[name] = item
#                         raas_list_jobs.append(item)
#                         index = index + 1

#                     # Add additional values to item:
#                     item['CreationTime'] = elements[4]  # '2023-05-23T21:41:28'
#                     item['SubmitTime'] = elements[4]  # '2023-05-23T21:41:28'
#                     item['StartTime'] = elements[5]  # '2023-05-23T21:41:28'
#                     item['EndTime'] = elements[6]  # May be # '2023-05-23T21:41:28' or 'Unknown'
#                 # get the line with JobId as a number
#                 elif "JobID" not in elements[1] \
#                     and "----" not in elements[1] \
#                         and len(slurmId) == 1 \
#                         and len(elements) == 7:  # Slurm log has always 7 elements

#                     if name in raas_dict_jobs:
#                         item = raas_dict_jobs[name]
#                     else:
#                         status = map_slurm_status(elements[3])
#                         item = helper_raas_dict_jobs(index, 
#                                                      name, 
#                                                      elements[2], 
#                                                      context.scene.raas_blender_job_info_new.cluster_type,
#                                                      status)
#                         raas_dict_jobs[name] = item
#                         raas_list_jobs.append(item)
#                         index = index + 1

#                     # Add additional values to item:
#                     item['CreationTime'] = elements[4]  # '2023-05-23T21:41:28'
#                     item['SubmitTime'] = elements[4]  # '2023-05-23T21:41:28'
#                     item['StartTime'] = elements[5]  # '2023-05-23T21:41:28'
#                     item['EndTime'] = elements[6]  # May be # '2023-05-23T21:41:28' or 'Unknown'
#                 # Check the current line for this pattern: name.job ---- ----- ----- -----
#                 # Check whether the next line contains the same name 
#                 # -> if not: error
#                 # -> otherwise: OK    
#                 elif onlyTrue == 1 \
#                     and (line_no + 1) < len(lines) \
#                         and len(lines[line_no + 1]) > 0 \
#                         and lines[line_no + 1].split()[0].split('.')[0] != elements[0].split('.')[0]:

#                     if name in raas_dict_jobs:
#                         item = raas_dict_jobs[name]
#                     else:
#                         split_point = name.split('-')[3] 
#                         item = helper_raas_dict_jobs(index,
#                                                      name, 
#                                                      name.split(split_point + '-')[1],   # '2023-33-33-3436465-project-name'
#                                                      context.scene.raas_blender_job_info_new.cluster_type,
#                                                      2)  #  "SUBMITTED"
#                         raas_dict_jobs[name] = item
#                         raas_list_jobs.append(item)
#                         index = index + 1
#         line_no = line_no + 1 + offset

#     context.scene.raas_list_jobs.clear()
#     for key in reversed(raas_list_jobs):
#         item = context.scene.raas_list_jobs.add()
#         raas_server.fill_items(item, key)         

#     if context.scene.raas_list_jobs_index > len(context.scene.raas_list_jobs) - 1:
#         context.scene.raas_list_jobs_index = len(context.scene.raas_list_jobs) - 1

async def ListSlurmJobsForCurrentUser(context, token):
    """Lists remote Slurm jobs by parsing job files.

    Args:
        context: Blender context
        token: Authentication token    
    """
    
    prefs = raas_pref.preferences()
    preset = prefs.cluster_presets[bpy.context.scene.raas_cluster_presets_index]

    # Setup and execute remote command
    server = raas_config.GetDAServer(context)
    cmd = CmdCreateProjectGroupFolder(context)
    await ssh_command(server, cmd, preset)
    remote_path = get_direct_access_remote_storage(context)

    cmd = f'cd {remote_path};grep --with-filename "" *.job'
    
    try:
        res = await ssh_command(server, cmd, preset)
    except Exception:
        print("No tasks to refresh in the selected project.")
        context.scene.raas_list_jobs.clear()
        context.scene.raas_list_jobs_index = -1 
        return

    if not res.strip():
        context.scene.raas_list_jobs.clear()
        context.scene.raas_list_jobs_index = -1
        return

    # Parse job data
    jobs_data = raas_jobs.slurm_parse_slurm_job_lines(res, context.scene.raas_blender_job_info_new.cluster_type)
    
    # Update UI
    raas_jobs.update_job_list(context, jobs_data)

async def ListPBSJobsForCurrentUser(context, token):
    """Lists remote PBS jobs by parsing job files.

    Args:
        context: Blender context
        token: Authentication token
    """

    prefs = raas_pref.preferences()
    preset = prefs.cluster_presets[bpy.context.scene.raas_cluster_presets_index]
    
    # Setup and execute remote command
    server = raas_config.GetDAServer(context)
    cmd = CmdCreateProjectGroupFolder(context)
    await ssh_command(server, cmd, preset)
    remote_path = get_direct_access_remote_storage(context)

    cmd = f'cd {remote_path};grep --with-filename "" *.job'
    
    try:
        res = await ssh_command(server, cmd, preset)   
    except Exception:
        print("No tasks to refresh in the selected project.")
        context.scene.raas_list_jobs.clear()
        context.scene.raas_list_jobs_index = -1 
        return

    if not res.strip():
        context.scene.raas_list_jobs.clear()
        context.scene.raas_list_jobs_index = -1
        return

    # Parse job data
    jobs_data = raas_jobs.pbs_parse_pbs_job_lines(res, context.scene.raas_blender_job_info_new.cluster_type)
    
    # Update UI
    raas_jobs.update_job_list(context, jobs_data)

async def ListSchedulerJobsForCurrentUser(context, token):
    """Lists remote jobs by parsing job files based on the scheduler type.

    Args:
        context: Blender context
        token: Authentication token
    """
    #cluster_type = context.scene.raas_blender_job_info_new.cluster_type
    scheduler = raas_config.GetSchedulerFromContext(context)
    if scheduler == 'SLURM':
        await ListSlurmJobsForCurrentUser(context, token)
    elif scheduler == 'PBS':
        await ListPBSJobsForCurrentUser(context, token)
    else:
        raise ValueError(f"Unsupported scheduler type: {scheduler}")

class RAAS_OT_ListJobsForCurrentUser(
                        async_loop.AsyncModalOperatorMixin,
                        AuthenticatedRaasOperatorMixin,                         
                        Operator):  
    """returns a list of basic information describing all user jobs"""
    bl_idname = 'raas.list_jobs_for_current_user'
    bl_label = 'Refresh jobs'


    async def async_execute(self, context):
        update_job_info_preset(context)

        if not await self.authenticate(context):
            self.quit()
            return        

        try:
            await ListSchedulerJobsForCurrentUser(context, self.token)
        except Exception as e:
            import traceback
            traceback.print_exc()
    
            self.report({'ERROR'}, "Problem with refresh: %s: %s" % (e.__class__, e))               
            context.window_manager.raas_status = "ERROR"
            context.window_manager.raas_status_txt = "There is an error! Check Info Editor!"


        self.quit()           

##########################################################################

async def SubmitJob(context, token):
        #item = context.scene.raas_submitted_job_info_ext_new

        prefs = raas_pref.preferences()
        preset = prefs.cluster_presets[bpy.context.scene.raas_cluster_presets_index]

        server = raas_config.GetDAServer(context)        
        cmd = raas_jobs.CmdCreateJob(context)
        if len(cmd) > 0:  # number of characters
            res = await ssh_command(server, cmd, preset)
            if len(res.split('\n')) - 1 < 3: # number of returned slurm ids
                raise Exception("ssh command (CmdCreateJob) failed: %s" % cmd)

            cmd = raas_jobs.CmdCreateStatJobFile(context, res)
            if len(cmd) > 0:
                await asyncio.sleep(3)
                res = await ssh_command(server, cmd, preset)
                    
     

async def CancelJob(context, token):
        idx = context.scene.raas_list_jobs_index 
        item = context.scene.raas_list_jobs[idx]

        prefs = raas_pref.preferences()
        preset = prefs.cluster_presets[bpy.context.scene.raas_cluster_presets_index]

        server = raas_config.GetDAServer(context)
        remote_path = get_direct_access_remote_storage(context)
        cmd = 'cat %s/%s.job | grep Id' % (remote_path, item.Name)
        res = await ssh_command(server, cmd, preset)
        if len(res) < 3:
            raise Exception("ssh command failed: %s" % cmd)

        jobs = res.split('\n')
        for job in jobs:
            if len(job) > 0:
                job_id = job.split(': ')[1]
                cmd = 'qdel -W force %s' % (job_id)
                res = await ssh_command(server, cmd, preset)

        cmd = "sed -i 's/job_state = R/job_state = C/g' %s/%s.job;sed -i 's/job_state = Q/job_state = C/g' %s/%s.job;echo '   ' ftime = $(date) >> %s/%s.job" % (remote_path, item.Name, remote_path, item.Name, remote_path, item.Name)
        res = await ssh_command(server, cmd, preset)


async def CancelSlurmJob(context, token):
        from datetime import datetime
        
        idx = context.scene.raas_list_jobs_index 
        item = context.scene.raas_list_jobs[idx]

        prefs = raas_pref.preferences()
        preset = prefs.cluster_presets[bpy.context.scene.raas_cluster_presets_index]

        server = raas_config.GetDAServer(context)
        remote_path = get_direct_access_remote_storage(context)
        cmd = 'grep "" %s/%s.job' % (remote_path, item.Name)
        res = await ssh_command(server, cmd, preset)

        lines = res.split('\n')  # make lines

        slurmId = None
        spaces = []  # number of spaces used in each element
        for line in lines:
            if len(line) > 0:
                elements = line.split()
                tmp = elements[0].split('.')
                if "----" in elements[0]:
                    for e in elements:
                        spaces.append(len(e))
                # get the line with JobId as a number
                if "JobID" != elements[0] and "----" not in elements[0] and len(tmp) == 1:
                    slurmId = tmp[0]
                if elements[2] in ['RUNNING', 'COMPLETING', 'SUSPENDED', 'RESIZING', 'STAGE_OUT',\
                                    'PENDING', 'CONFIGURING', 'REQUEUE_HOLD', 'REQUEUED', 'REQUEUE_FED']:
                    
                    elements[2] = 'CANCELLED'
                    elements[-1] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                    updatedLine = ""
                    for el, sp in zip(elements, spaces):
                        updatedLine = updatedLine + f"{el:>{sp}}{' '}"
                    cmd = "sed -i 's/%s/%s/g' %s/%s.job" % (line, updatedLine, remote_path, item.Name)
                    res = await ssh_command(server, cmd, preset)

        cmd = 'scancel -f %s' % (slurmId)
        res = await ssh_command(server, cmd, preset)


class RAAS_OT_CancelJob(
                        async_loop.AsyncModalOperatorMixin,
                        AuthenticatedRaasOperatorMixin,                         
                        Operator):

    """cancels a running job"""
    bl_idname = 'raas.cancel_job'
    bl_label = 'Cancel Job'

    async def async_execute(self, context):

        if not await self.authenticate(context):
            self.quit()
            return     

        try:
            item = context.scene.raas_submitted_job_info_ext_new
            await CancelSlurmJob(context, self.token)
            await ListSchedulerJobsForCurrentUser(context, self.token)     
        except Exception as e:
            import traceback
            traceback.print_exc()

            self.report({'ERROR'}, "Problem with canceling of job: %s: %s" % (e.__class__, e))              
            context.window_manager.raas_status = "ERROR"
            context.window_manager.raas_status_txt = "There is an error! Check Info Editor!"


        self.quit()                 

async def DeleteJob(context, token):
        idx = context.scene.raas_list_jobs_index 
        #try:
        item = context.scene.raas_list_jobs[idx]
     

class RAAS_OT_DeleteJob(
                        async_loop.AsyncModalOperatorMixin,
                        AuthenticatedRaasOperatorMixin,                         
                        Operator):

    """delete a running job"""
    bl_idname = 'raas.delete_job'
    bl_label = 'Delete Job'

    async def async_execute(self, context):

        if not await self.authenticate(context):
            self.quit()
            return     

        try:
            await DeleteJob(context, self.token)
            #await ListJobsForCurrentUser(context, self.token) 
            await ListSchedulerJobsForCurrentUser(context, self.token)
        except Exception as e:
            import traceback
            traceback.print_exc()

            self.report({'ERROR'}, "Problem with deleting of job: %s: %s" % (e.__class__, e))  
            context.window_manager.raas_status = "ERROR"
            context.window_manager.raas_status_txt = "There is an error! Check Info Editor!"


        self.quit()

class RAAS_PT_ListJobs(RaasButtonsPanel, Panel):
    bl_label = "Jobs"
    bl_parent_id = "RAAS_PT_simplify"

    def draw(self, context):
        layout = self.layout

        if context.window_manager.raas_status in {'IDLE', 'ERROR', 'DONE'}:
            layout.enabled = True
        else:
            layout.enabled = False        

        #header
        box = layout.box()

        row = box.row()   

        col = row.column()        
        col.label(text="Id")
        col = row.column()
        col.label(text="Project")        
        col = row.column()
        col.label(text="Cluster")        
        col = row.column()
        col.label(text="State")        
        
        #table
        row = layout.row()
        row.template_list("RAAS_UL_SubmittedJobInfoExt", "", context.scene, "raas_list_jobs", context.scene, "raas_list_jobs_index")

        #button
        row = layout.row()
        row.operator(RAAS_OT_ListJobsForCurrentUser.bl_idname, text='Refresh')
        row.operator(RAAS_OT_CancelJob.bl_idname, text='Cancel')

        idx = context.scene.raas_list_jobs_index        

        if idx != -1 and len(context.scene.raas_list_jobs) > 0:

            item = context.scene.raas_list_jobs[idx]   
            box = layout.box()
            box.enabled = False

            box.label(text=('Job: %d' % item.Id))
            box.prop(item, "Name")
            box.prop(item, "Project")
            box.prop(item, "SubmitTime")
            box.prop(item, "StartTime")
            box.prop(item, "EndTime")

            #row = box.column()            
            box.prop(item, "State")

            box = layout.box()

            local_storage = str(get_job_local_storage(item.Name))
            paths_layout = box.column(align=True)
            labeled_row = paths_layout.split(**raas_pref.factor(0.25), align=True)
            labeled_row.label(text='Storage Path:')
            prop_btn_row = labeled_row.row(align=True)
            prop_btn_row.label(text=local_storage)
            props = prop_btn_row.operator(RAAS_OT_explore_file_path.bl_idname,
                                        text='', icon='DISK_DRIVE')
            props.path = local_storage

            row = box.row()
            row.operator(RAAS_OT_download_files.bl_idname, text='Download results')

#################################################  

# RaasManagerGroup needs to be registered before classes that use it.
_rna_classes = []
_rna_classes.extend(
    cls for cls in locals().values()
    if (isinstance(cls, type)
        and cls.__name__.startswith('RAAS')
        and cls not in _rna_classes)
)


def register():
    #from ..utils import redraw

    for cls in _rna_classes:
        bpy.utils.register_class(cls)

    scene = bpy.types.Scene
    scene.raas_cluster_presets_index = bpy.props.IntProperty(default=-1, options={'SKIP_SAVE'})
    ################JobManagement#################
    scene.raas_list_jobs = bpy.props.CollectionProperty(type=RAAS_PG_SubmittedJobInfoExt, options={'SKIP_SAVE'})
    scene.raas_list_jobs_index = bpy.props.IntProperty(default=-1, options={'SKIP_SAVE'})
    scene.raas_blender_job_info_new = bpy.props.PointerProperty(type=RAAS_PG_BlenderJobInfo, options={'SKIP_SAVE'})
    scene.raas_submitted_job_info_ext_new = bpy.props.PointerProperty(type=RAAS_PG_SubmittedJobInfoExt, options={'SKIP_SAVE'})
    scene.raas_total_core_hours_usage = bpy.props.IntProperty(default=0)
    
    scene.raas_session = RaasSession()
    #################################       

    bpy.types.WindowManager.raas_status = EnumProperty(
        items=[
            ('IDLE', 'IDLE', 'Not doing anything.'),
            ('SAVING', 'SAVING', 'Saving your file.'),
            ('INVESTIGATING', 'INVESTIGATING', 'Finding all dependencies.'),
            ('TRANSFERRING', 'TRANSFERRING', 'Transferring all dependencies.'),
            ('COMMUNICATING', 'COMMUNICATING', 'Communicating with Raas Server.'),
            ('DONE', 'DONE', 'Not doing anything, but doing something earlier.'),
            ('ERROR', 'ERROR', 'Something is wrong.'),
            ('PARTIAL_DONE', 'PARTIAL_DONE', 'Partial done.'),
            ('ABORTING', 'ABORTING', 'User requested we stop doing something.'),
            #('ABORTED', 'ABORTED', 'We stopped doing something.'),
        ],
        name='raas_status',
        default='IDLE',
        description='Current status of the Raas add-on',
        update=redraw
        )

    bpy.types.WindowManager.raas_status_txt = StringProperty(
        name='Raas Status',
        default='',
        description='Textual description of what Raas is doing',
        update=redraw)

    bpy.types.WindowManager.raas_progress = IntProperty(
        name='Raas Progress',
        default=0,
        description='File transfer progress',
        subtype='PERCENTAGE',
        min=0,
        max=100,
        update=redraw)


def unregister():
    for cls in _rna_classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            log.warning('Unable to unregister class %r, probably already unregistered', cls)

    try:
        del bpy.types.WindowManager.raas_status
    except AttributeError:
        pass
