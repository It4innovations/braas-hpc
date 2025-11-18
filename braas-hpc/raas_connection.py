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

import os
import platform
import socket
import subprocess
import threading
import time
import shutil
from contextlib import closing

################################
import time
################################

import bpy
# from bpy.types import AddonPreferences, Operator, WindowManager, Scene, PropertyGroup, Panel
# from bpy.props import StringProperty, EnumProperty, PointerProperty, BoolProperty, IntProperty

# from bpy.types import Header, Menu

from . import async_loop
from . import raas_server
from . import raas_pref
from . import raas_jobs
from . import raas_config

import pathlib
import json

#############################################################################
def is_verbose_debug():
    return bpy.app.debug_value == 256

def get_ssh_key_file():
    ssh_key_local = Path(tempfile.gettempdir()) / 'server_key'
    return ssh_key_local

def get_cluster_presets():
    presets = []  # to be returned in EnumProperty
    for preset in raas_pref.preferences().cluster_presets:
        presets.append(('%s, %s, %s' % (preset.cluster_name, preset.allocation_name, preset.partition_name), '', ''))
    return presets

def get_pref_storage_dir():
    pref = raas_pref.preferences()
    return pref.raas_job_storage_path

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

############################################################################
class SSHTunnel:
    """
    SSH tunnel management using native OpenSSH.
    - start/stop
    - health check, optional auto-restart
    - configurable SSH options
    """
    def __init__(
        self,
        user_host: str,                 # e.g. "user@remote-host"
        local_host: str = "127.0.0.1",
        local_port: int = 5000,
        remote_host: str = "127.0.0.1",
        remote_port: int = 6000,
        identity_file: str | None = None,
        auto_restart: bool = True,
        check_interval_sec: float = 5.0,
        ssh_path: str | None = None,    # path to ssh binary, default is found in PATH
        extra_ssh_opts: list[str] | None = None
    ):
        self.user_host = user_host
        self.local_host = local_host
        self.local_port = int(local_port)
        self.remote_host = remote_host
        self.remote_port = int(remote_port)
        self.identity_file = identity_file
        self.auto_restart = auto_restart
        self.check_interval_sec = check_interval_sec
        self.ssh_path = ssh_path or shutil.which("ssh") or "ssh"
        self.extra_ssh_opts = extra_ssh_opts or []

        self._proc: subprocess.Popen | None = None
        self._watcher: threading.Thread | None = None
        self._stop_evt = threading.Event()

        if not shutil.which(self.ssh_path):
            raise RuntimeError(f"OpenSSH client '{self.ssh_path}' was not found in PATH.")

    @staticmethod
    def _is_port_listening(host: str, port: int, timeout: float = 0.2) -> bool:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.settimeout(timeout)
            try:
                return s.connect_ex((host, port)) == 0
            except OSError:
                return False

    def _build_cmd(self) -> list[str]:
        cmd = [
            self.ssh_path,
            "-N",                     # no remote command (just the tunnel)
            "-T",                     # no TTY
            "-o", "ExitOnForwardFailure=yes",
            "-o", "ServerAliveInterval=20",
            "-o", "ServerAliveCountMax=3",
            "-o", "Compression=no",
            #"-c",  "aes128-gcm@openssh.com",  # fast cipher (on ARM without AES-NI consider chacha20-poly1305)
            "-L", f"{self.local_host}:{self.local_port}:{self.remote_host}:{self.remote_port}",
        ]
        # ControlMaster can speed up repeated connections; not always available (Windows OpenSSH sometimes lacks it).
        # Safe to leave disabled; if desired, uncomment:
        # cmd += ["-M", "-S", f"/tmp/ssh-ctrl-{self.local_port}", "-o", "ControlPersist=10m"]

        if self.identity_file:
            cmd += ["-i", self.identity_file]

        # Add extra options (e.g., ProxyJump, Port, etc.)
        cmd += self.extra_ssh_opts

        cmd.append(self.user_host)
        return cmd

    def start(self, wait_ready_timeout: float = 10.0):
        if self._proc and self._proc.poll() is None:
            return  # already running

        # if the port is already taken, raise a meaningful error
        if self._is_port_listening(self.local_host, self.local_port):
            raise RuntimeError(
                f"Local port {self.local_host}:{self.local_port} is already in use – choose a different one or close the existing tunnel first."
            )

        cmd = self._build_cmd()
        # On Windows, hide the terminal window
        creationflags = 0x08000000 if platform.system() == "Windows" else 0

        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=creationflags,
            text=True
        )

        # Wait until the tunnel is actually listening
        deadline = time.time() + wait_ready_timeout
        while time.time() < deadline:
            if self._is_port_listening(self.local_host, self.local_port):
                break
            # if ssh already failed, grab its error output
            if self._proc.poll() is not None:
                _, err = self._proc.communicate(timeout=0.2)
                raise RuntimeError(f"SSH tunnel failed to start:\n{err}")
            time.sleep(0.1)
        else:
            self.stop()
            raise TimeoutError(
                f"SSH tunnel did not become ready within {wait_ready_timeout}s. Check your connection or SSH keys."
            )

        # watcher (optional auto-restart)
        self._stop_evt.clear()
        if self.auto_restart:
            self._watcher = threading.Thread(target=self._watch_loop, daemon=True)
            self._watcher.start()

    def _watch_loop(self):
        # Periodically check: 1) ssh process is alive, 2) port is still listening
        while not self._stop_evt.wait(self.check_interval_sec):
            proc_dead = (self._proc is None) or (self._proc.poll() is not None)
            port_dead = not self._is_port_listening(self.local_host, self.local_port)
            if proc_dead or port_dead:
                self._restart()

    def _restart(self):
        self._kill_proc()
        try:
            self.start(wait_ready_timeout=10.0)
        except Exception:
            # short backoff loop; avoid excessive logging
            time.sleep(max(self.check_interval_sec, 2.0))

    def _kill_proc(self):
        if self._proc is None:
            return
        try:
            # attempt graceful shutdown
            self._proc.terminate()
            try:
                self._proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        finally:
            self._proc = None

    def stop(self):
        self._stop_evt.set()
        if self._watcher and self._watcher.is_alive():
            self._watcher.join(timeout=2.0)
        self._watcher = None
        self._kill_proc()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.stop()

#############################################################################
class RaasSession:
    def __init__(self):
        self.paramiko_ssh_clients = {}

        self.server = None
        self.username = None
        self.key_file = None
        self.key_file_password = None
        self.password = None 
        self.password_2fa = None
        self.use_password = None
        self.ssh_tunnel = None

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

    def paramiko_create_session(self, password, password_2fa=None):
        import paramiko
        class Interactive2FASSHClient(paramiko.SSHClient):
            """Custom SSH client that handles 2FA authentication"""
            
            def __init__(self, password=None, totp_code=None):
                super().__init__()
                self.password = password
                self.totp_code = totp_code
                
            def _auth(self, username, *args, **kwargs):
                """Override the authentication method to handle 2FA"""        
                
                # First try the original authentication
                try:
                    if not self.totp_code is None:
                        raise paramiko.AuthenticationException("Trigger 2FA interactive auth")
                    
                    return super()._auth(username, *args, **kwargs)
                except paramiko.AuthenticationException as e:
                    # If original auth fails and we have 2FA code, try interactive auth
                    if self.totp_code and self._transport:
                        try:
                            # Use interactive authentication for 2FA
                            def auth_handler(title, instructions, prompt_list):
                                responses = []
                                for prompt_text, echo in prompt_list:
                                    prompt_lower = prompt_text.lower()
                                    
                                    # Check for password prompts
                                    if any(keyword in prompt_lower for keyword in ['password', 'passphrase']) and not echo:
                                        responses.append(self.password or '')
                                    # Check for 2FA prompts
                                    elif any(keyword in prompt_lower for keyword in ['verification', 'authenticator', 'token', 'code', '2fa', 'totp']):
                                        responses.append(self.totp_code or '')
                                    else:
                                        # Default to TOTP code for unknown prompts
                                        responses.append(self.totp_code or '')
                                
                                return responses
                            
                            # Try interactive authentication
                            self._transport.auth_interactive(username, auth_handler)
                            return
                        except Exception as interactive_ex:
                            raise paramiko.AuthenticationException(f"2FA authentication failed: {interactive_ex}")
                    
                    # Re-raise original exception if no 2FA handling
                    raise e        

        if not password is None:
            if self.use_password:
                self.password = password
            else:
                self.key_file_password = password

        if not password_2fa is None or len(password_2fa) > 0:
            self.password_2fa = password_2fa
        else:
            self.password_2fa = None
 
        ssh = None
        try: 
            #ssh = paramiko.SSHClient()
            ssh = Interactive2FASSHClient(password=self.password, totp_code=self.password_2fa)           
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
        
    def show_dialog(self, server, username, key_file, key_file_password, password, use_password, use_password_2fa):
        if not self.paramiko_is_alive(server):
            self.paramiko_close(server)

            self.server = server
            self.username = username
            self.key_file = key_file
            self.key_file_password = key_file_password
            self.password = password
            self.password_2fa = None
            self.use_password = use_password

            if self.check_password() and not use_password_2fa:
                self.paramiko_create_session(None, None)
            else:
                bpy.ops.wm.raas_password_input('INVOKE_DEFAULT')
                raise Exception("Password required")
            
    def create_ssh_tunnel(self, key_file, destination, node, port1, port2):
        """create_ssh_tunnel"""

        if not self.ssh_tunnel is None:
            self.ssh_tunnel.stop()
            self.ssh_tunnel = None

        self.ssh_tunnel = SSHTunnel(
            user_host=destination,
            local_port=port1,
            remote_host=node,
            remote_port=port2,
            identity_file=key_file,
            auto_restart=True
        )

        self.ssh_tunnel.start()

    def close_ssh_tunnel(self):
        """close_ssh_tunnel"""

        if not self.ssh_tunnel is None:
            self.ssh_tunnel.stop()
            self.ssh_tunnel = None

# async def _ssh_tunnel(key_file, destination, port1, port2):
#         """ Execute an ssh command """
#         cmd = [
#             'ssh',
#             '-N',
#             '-i', key_file,            
#             '-L', port1,
#             '-L', port2,
#             destination,
#             '&',
#         ]
#         #             '-q',             '-o', 'StrictHostKeyChecking=no',

#         import asyncio
#         #loop = asyncio.get_event_loop()
#         #, stdin=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
#         #process = await asyncio.create_subprocess_exec(*cmd, loop=loop)
#         process = await asyncio.create_subprocess_exec(*cmd)
#         await process.wait()

#         if process.returncode != 0 and is_verbose_debug() == True:
#             print("ssh command failed: %s" % cmd)

# async def connect_to_client(context, fileTransfer, job_id: int, token: str) -> None:
#     """connect_to_client"""       

#     data = {
#         "SubmittedJobInfoId": job_id,
#         "SessionCode": token
#     }

#     #allocated_nodes_ips = await raas_server.post("JobManagement/GetAllocatedNodesIPs", data)
#     info_job = await raas_server.post("JobManagement/GetCurrentInfoForJob", data)
#     all_params = info_job['AllParameters']
#     allocated_nodes_ips = ''
#     for line in all_params.split('\n'):
#         if "exec_vnode" in line:
#             allocated_nodes_ips = line.split('(')
#             allocated_nodes_ips = allocated_nodes_ips[1].split(':')
#             break

#     print(allocated_nodes_ips)

#     serverHostname = fileTransfer['ServerHostname']
#     sharedBasepath = fileTransfer['SharedBasepath']
#     credentials = fileTransfer['Credentials']
#     username = credentials['UserName']

#     key_file = str(get_ssh_key_file())
#     destination = '%s@%s' % (username, serverHostname)
#     print('connect to server')

#     allocated_nodes_ips = allocated_nodes_ips[0]
#     if 'mic' in allocated_nodes_ips:
#         allocated_nodes_ips = '%s.head' % allocated_nodes_ips
#     port1 = '7000:%s:7000' % (allocated_nodes_ips)
#     port2 = '7001:%s:7001' % (allocated_nodes_ips)

#     await _ssh_tunnel(key_file, destination, port1, port2)

async def connect_to_client(context, fileTransfer, job_id: int, token: str) -> None:
    """connect_to_client"""   



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

def _paramiko_ssh(server, username, key_file, key_file_password, password, use_password, use_password_2fa, command):
        """ Execute an paramiko ssh command """

        import paramiko
        #from io import StringIO
        #from base64 import b64decode
        #from scp import SCPClient

        bpy.context.scene.raas_session.show_dialog(server, username, key_file, key_file_password, password, use_password, use_password_2fa)

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
    use_password_2fa = preset.raas_use_2FA
    
    if preset.raas_ssh_library == 'PARAMIKO':
        return _paramiko_ssh(server, username, key_file, key_file_password, password, use_password, use_password_2fa, command)
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
    use_password_2fa = preset.raas_use_2FA
    
    if preset.raas_ssh_library == 'PARAMIKO':
        return _paramiko_ssh(server, username, key_file, key_file_password, password, use_password, use_password_2fa, command)
    else:
        return _ssh_sync(None, server, None, command)
                  
####################################FileTransfer#############################

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

def _paramiko_put(server, username, key_file, key_file_password, password, use_password, use_password_2fa, source, destination):
        """ Execute an paramiko command """

        import paramiko
        from io import StringIO
        from base64 import b64decode
        from scp import SCPClient

        bpy.context.scene.raas_session.show_dialog(server, username, key_file, key_file_password, password, use_password, use_password_2fa)

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


def _paramiko_get(server, username, key_file, key_file_password, password, use_password, use_password_2fa, source, destination):
        """ Execute an paramiko command """

        import paramiko
        from io import StringIO
        from base64 import b64decode
        from scp import SCPClient

        bpy.context.scene.raas_session.show_dialog(server, username, key_file, key_file_password, password, use_password, use_password_2fa)

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
    use_password_2fa = preset.raas_use_2FA

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
            await asyncio.to_thread(_paramiko_put, serverHostname, username, key_file, key_file_password, password, use_password, use_password_2fa, source, destination)
        else:
            destination = job_local_dir
            source = '%s/%s' % (str(sharedBasepath), job_remote_dir)
            print('copy from server to: %s' % (job_local_dir))
            #await _paramiko_get(pkey, serverHostname, username, password, source, destination)
            await asyncio.to_thread(_paramiko_get, serverHostname, username, key_file, key_file_password, password, use_password, use_password_2fa, source, destination)

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
