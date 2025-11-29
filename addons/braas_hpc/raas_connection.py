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
class SSHProcess:
    """
    Base class for SSH process management using native OpenSSH.
    Handles process lifecycle, monitoring, and automatic restart.
    """
    def __init__(
        self,
        user_host: str,
        identity_file: str | None = None,
        auto_restart: bool = True,
        check_interval_sec: float = 5.0,
        ssh_path: str | None = None,
        extra_ssh_opts: list[str] | None = None
    ):
        self.user_host = user_host
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

    def _build_cmd(self) -> list[str]:
        """Build SSH command. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement _build_cmd()")

    def _is_healthy(self) -> bool:
        """Check if the SSH process is healthy. Override in subclasses."""
        if self._proc is None:
            return False
        return self._proc.poll() is None

    def _kill_proc(self):
        """Terminate the SSH process."""
        if self._proc is None:
            return
        try:
            # Capture any remaining output before killing
            if self._proc.poll() is None:
                try:
                    out, err = self._proc.communicate(timeout=0.5)
                    if (out or err) and is_verbose_debug():
                        print(f"SSH process output before termination:\nSTDOUT: {out}\nSTDERR: {err}")
                except subprocess.TimeoutExpired:
                    pass
            
            # attempt graceful shutdown
            self._proc.terminate()
            try:
                out, err = self._proc.communicate(timeout=2.0)
                if (out or err) and is_verbose_debug():
                    print(f"SSH process final output:\nSTDOUT: {out}\nSTDERR: {err}")
            except subprocess.TimeoutExpired:
                self._proc.kill()
                try:
                    out, err = self._proc.communicate(timeout=0.5)
                    if (out or err) and is_verbose_debug():
                        print(f"SSH process output after kill:\nSTDOUT: {out}\nSTDERR: {err}")
                except:
                    pass
        finally:
            self._proc = None

    def _start_process(self):
        """Start the SSH process. Override in subclasses for custom behavior."""
        if self._proc and self._proc.poll() is None:
            return  # already running

        cmd = self._build_cmd()
        # On Windows, hide the terminal window
        creationflags = 0x08000000 if platform.system() == "Windows" else 0

        if is_verbose_debug():
            print(f"Starting SSH process: {' '.join(cmd)}")

        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=creationflags,
            text=True
        )
        
        if is_verbose_debug():
            print(f"SSH process started with PID: {self._proc.pid}")

    def _read_output(self):
        """Read and print any available output from the process."""
        if self._proc and self._proc.stdout:
            try:
                # Non-blocking read of available output
                import select
                if platform.system() != "Windows":
                    # Unix-like systems can use select
                    if select.select([self._proc.stdout], [], [], 0)[0]:
                        line = self._proc.stdout.readline()
                        if line and is_verbose_debug():
                            print(f"SSH stdout: {line.strip()}")
                # For Windows or when output is available
                if self._proc.stderr:
                    if platform.system() != "Windows":
                        if select.select([self._proc.stderr], [], [], 0)[0]:
                            line = self._proc.stderr.readline()
                            if line:
                                print(f"SSH stderr: {line.strip()}")
            except:
                pass

    def _watch_loop(self):
        """Monitor the SSH process and restart if needed."""
        while not self._stop_evt.wait(self.check_interval_sec):
            self._read_output()
            if not self._is_healthy():
                self._restart()

    def _restart(self):
        """Restart the SSH process."""
        self._kill_proc()
        try:
            self.start()
        except Exception:
            # short backoff loop; avoid excessive logging
            time.sleep(max(self.check_interval_sec, 2.0))

    def start(self):
        """Start the SSH process. Override in subclasses for custom initialization."""
        self._start_process()

        # watcher (optional auto-restart)
        self._stop_evt.clear()
        if self.auto_restart:
            self._watcher = threading.Thread(target=self._watch_loop, daemon=True)
            self._watcher.start()

    def stop(self):
        """Stop the SSH process and cleanup."""
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

    def __del__(self):
        self.stop()

class SSHCommand(SSHProcess):
    """
    SSH command execution using native OpenSSH.
    - Execute commands on remote host
    - Capture stdout/stderr
    - Support for long-running commands (infinite loops)
    """
    def __init__(
        self,
        user_host: str,                 # e.g. "user@remote-host"
        local_port: int,
        remote_host: str,
        remote_port: int,        
        command: str,                   # command to execute
        identity_file: str | None = None,
        ssh_path: str | None = None,    # path to ssh binary, default is found in PATH
        extra_ssh_opts: list[str] | None = None,
        auto_restart: bool = False      # Auto-restart for long-running commands
    ):
        super().__init__(
            user_host=user_host,
            identity_file=identity_file,
            auto_restart=auto_restart,
            check_interval_sec=5.0 if auto_restart else 0,
            ssh_path=ssh_path,
            extra_ssh_opts=extra_ssh_opts
        )
        self.command = command
        self.local_port = local_port
        self.remote_host = remote_host
        self.remote_port = remote_port

        self._stdout: str | None = None
        self._stderr: str | None = None
        self._returncode: int | None = None

    def _build_cmd(self) -> list[str]:
        cmd = [
            self.ssh_path,
            "-T",                     # no TTY
            "-o", "StrictHostKeyChecking=no",  # auto-accept host keys
            "-o", "UserKnownHostsFile=/dev/null",  # don't save host keys
            "-o", "ServerAliveInterval=20",
            "-o", "ServerAliveCountMax=3",
            "-L", f"{self.local_port}:{self.remote_host}:{self.remote_port}",
        ]

        if self.identity_file:
            cmd += ["-i", self.identity_file]

        # Add extra options (e.g., ProxyJump, Port, etc.)
        cmd += self.extra_ssh_opts

        cmd.append(self.user_host)
        # Wrap command in bash -c to properly handle shell metacharacters
        # cmd.append("bash")
        # cmd.append("-c")
        cmd.append(self.command)
        return cmd

    def start(self):
        """Start the SSH command process and keep it running (for long-running commands)."""
        super().start()

    def execute(self, timeout: float | None = None) -> tuple[str, str, int]:
        """
        Execute the SSH command synchronously and return (stdout, stderr, returncode).
        Use this for short-lived commands that complete.
        
        Args:
            timeout: Maximum time to wait for command completion
            
        Returns:
            Tuple of (stdout, stderr, returncode)
        """
        self._start_process()
        
        try:
            stdout, stderr = self._proc.communicate(timeout=timeout)
            self._stdout = stdout
            self._stderr = stderr
            self._returncode = self._proc.returncode
        except subprocess.TimeoutExpired:
            self._kill_proc()
            raise TimeoutError(f"SSH command timed out after {timeout}s")
        finally:
            self._proc = None
        
        return self._stdout, self._stderr, self._returncode

    @property
    def stdout(self) -> str | None:
        """Get stdout from last execution."""
        return self._stdout

    @property
    def stderr(self) -> str | None:
        """Get stderr from last execution."""
        return self._stderr

    @property
    def returncode(self) -> int | None:
        """Get return code from last execution."""
        return self._returncode
    
    def is_running(self) -> bool:
        """Check if the SSH command process is currently running."""
        return self._is_healthy()


class SSHCommandJump(SSHCommand):
    """
    SSH command execution through a jump host using ProxyJump.
    - Execute commands on remote host via jump host
    - Support for long-running commands (infinite loops)
    - Automatic ProxyJump configuration
    """
    def __init__(
        self,
        user_host: str,                 # e.g. "user@remote-host" (final destination)
        jump_host: str,                 # e.g. "user@jump-host" (intermediate host)
        local_port: int,
        remote_port: int,
        command: str,                   # command to execute
        identity_file: str | None = None,
        ssh_path: str | None = None,
        extra_ssh_opts: list[str] | None = None,
        auto_restart: bool = False
    ):
        # Don't call super().__init__ yet, we need to set jump_host first
        self.jump_host = jump_host
        self.local_port = int(local_port)
        self.remote_port = int(remote_port)
        #self.remote_host = remote_host       
        
        # Now call parent constructor
        super().__init__(
            user_host=user_host,
            local_port=local_port,
            remote_host="localhost",
            remote_port=remote_port,          
            command=command,
            identity_file=identity_file,
            ssh_path=ssh_path,
            extra_ssh_opts=extra_ssh_opts,
            auto_restart=auto_restart
        )

    def _build_cmd(self) -> list[str]:
        """Build SSH command with ProxyJump."""
        cmd = [
            self.ssh_path,
            "-T",                     # no TTY
            "-J", self.jump_host,     # ProxyJump through jump host
            "-o", "StrictHostKeyChecking=no",  # auto-accept host keys
            "-o", "UserKnownHostsFile=/dev/null",  # don't save host keys
            "-o", "ServerAliveInterval=20",
            "-o", "ServerAliveCountMax=3",
            "-L", f"{self.local_port}:localhost:{self.remote_port}",
        ]

        if self.identity_file:
            cmd += ["-i", self.identity_file]

        # Add extra options
        cmd += self.extra_ssh_opts

        cmd.append(self.user_host)
        # Wrap command in bash -c to properly handle shell metacharacters
        # cmd.append("bash")
        # cmd.append("-c")
        cmd.append(self.command)
        return cmd        

#############################################################################
class RaasSession:
    def __init__(self):
        self.paramiko_ssh_clients = {}  # Paramiko SSH clients
        self.asyncssh_ssh_clients = {}  # AsyncSSH clients
        self.ssh_client_type = 'PARAMIKO'  # Default to 'PARAMIKO' or 'ASYNCSSH'

        self.server = None
        self.username = None
        self.key_file = None
        self.key_file_password = None
        self.password = None 
        self.password_2fa = None
        self.use_password = None
        self.ssh_command_proc = None
        self.ssh_command_jump_proc = None

    def is_alive(self, server=None, client_type=None):
        """Check if SSH connection is alive for a specific server (supports both Paramiko and AsyncSSH)"""
        if server is None:
            server = self.server
        
        if client_type is None:
            client_type = self.ssh_client_type
            
        if client_type == 'PARAMIKO':
            if server not in self.paramiko_ssh_clients:
                return False
                
            ssh_client = self.paramiko_ssh_clients[server]
            if ssh_client is None:
                return False

            transport = ssh_client.get_transport()
            if transport is None:
                return False

            return transport.is_active()
        elif client_type == 'ASYNCSSH':
            if server not in self.asyncssh_ssh_clients:
                return False
                
            ssh_client = self.asyncssh_ssh_clients[server]
            if ssh_client is None:
                return False
            
            # AsyncSSH connection check
            return not ssh_client.is_closed()
        else:
            return False
    
    def paramiko_is_alive(self, server=None):
        """Check if Paramiko SSH connection is alive for a specific server (legacy method)"""
        return self.is_alive(server, client_type='PARAMIKO')
    
    def close(self, server=None, client_type=None):
        """Close SSH connection for a specific server or all servers (supports both Paramiko and AsyncSSH)"""
        if client_type is None:
            client_type = self.ssh_client_type
            
        if client_type == 'PARAMIKO':
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
        elif client_type == 'ASYNCSSH':
            if server is None:
                # Close all connections
                for srv, ssh_client in self.asyncssh_ssh_clients.items():
                    if ssh_client is not None:
                        ssh_client.close()
                self.asyncssh_ssh_clients.clear()
            else:
                # Close specific server connection
                if server in self.asyncssh_ssh_clients:
                    ssh_client = self.asyncssh_ssh_clients[server]
                    if ssh_client is not None:
                        ssh_client.close()
                    del self.asyncssh_ssh_clients[server]
    
    def paramiko_close(self, server=None):
        """Close Paramiko SSH connection for a specific server or all servers (legacy method)"""
        self.close(server, client_type='PARAMIKO')

    def get_ssh(self, server=None, client_type=None):
        """Get SSH client for a specific server (supports both Paramiko and AsyncSSH)"""
        if server is None:
            server = self.server
        
        if client_type is None:
            client_type = self.ssh_client_type
            
        if client_type == 'PARAMIKO':
            return self.paramiko_ssh_clients.get(server)
        elif client_type == 'ASYNCSSH':
            return self.asyncssh_ssh_clients.get(server)
        else:
            return None
    
    def set_ssh(self, ssh, server=None, client_type=None):
        """Set SSH client for a specific server (supports both Paramiko and AsyncSSH)"""
        if server is None:
            server = self.server
        
        if client_type is None:
            client_type = self.ssh_client_type
            
        if client_type == 'PARAMIKO':
            self.paramiko_ssh_clients[server] = ssh
        elif client_type == 'ASYNCSSH':
            self.asyncssh_ssh_clients[server] = ssh
    
    def paramiko_get_ssh(self, server=None):
        """Get Paramiko SSH client for a specific server (legacy method)"""
        return self.get_ssh(server, client_type='PARAMIKO')
    
    def paramiko_set_ssh(self, ssh, server=None):
        """Set Paramiko SSH client for a specific server (legacy method)"""
        self.set_ssh(ssh, server, client_type='PARAMIKO')

    def check_password(self):
        if self.use_password:
            return not self.password is None and len(self.password) > 0
        else:
            return not self.key_file_password is None and len(self.key_file_password) > 0

    def paramiko_create_session(self, password, password_2fa=None):
        import paramiko
        class Custom2FASSHClient(paramiko.SSHClient):
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
                        raise paramiko.AuthenticationException("Trigger 2FA auth")
                    
                    return super()._auth(username, *args, **kwargs)
                except paramiko.AuthenticationException as e:
                    # If original auth fails and we have 2FA code, try auth
                    if self.totp_code and self._transport:
                        try:
                            # Use authentication for 2FA
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
                            
                            # Try authentication
                            self._transport.auth_interactive(username, auth_handler)
                            return
                        except Exception as auth_ex:
                            raise paramiko.AuthenticationException(f"2FA authentication failed: {auth_ex}")
                    
                    # Re-raise original exception if no 2FA handling
                    raise e        

        if not password is None:
            if self.use_password:
                self.password = password
            else:
                self.key_file_password = password

        if not password_2fa is None and len(password_2fa) > 0:
            self.password_2fa = password_2fa
        else:
            self.password_2fa = None
 
        ssh = None
        try: 
            #ssh = paramiko.SSHClient()
            ssh = Custom2FASSHClient(password=self.password, totp_code=self.password_2fa)           
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
    
    async def asyncssh_create_session(self, password, password_2fa=None):
        """Create AsyncSSH session with 2FA support"""
        import asyncssh
        
        if not password is None:
            if self.use_password:
                self.password = password
            else:
                self.key_file_password = password

        if not password_2fa is None and len(password_2fa) > 0:
            self.password_2fa = password_2fa
        else:
            self.password_2fa = None
 
        ssh = None
        try:
            # Load client keys if needed
            client_keys = []
            if not self.use_password and self.key_file:
                try:
                    if self.key_file_password is None or len(self.key_file_password) == 0:
                        client_keys = [self.key_file]
                    else:
                        key = asyncssh.read_private_key(self.key_file, passphrase=self.key_file_password)
                        client_keys = [key]
                except Exception as e:
                    raise Exception(f"Failed to load SSH key: {e}")
            
            # Connect to server
            if self.use_password:
                # Handle 2FA with keyboard auth
                if self.password_2fa:
                    def kbdint_handler(name, instructions, prompts):
                        responses = []
                        for prompt_text, echo in prompts:
                            prompt_lower = prompt_text.lower()
                            if any(keyword in prompt_lower for keyword in ['password', 'passphrase']) and not echo:
                                responses.append(self.password or '')
                            elif any(keyword in prompt_lower for keyword in ['verification', 'authenticator', 'token', 'code', '2fa', 'totp']):
                                responses.append(self.password_2fa or '')
                            else:
                                responses.append(self.password_2fa or '')
                        return responses
                    
                    ssh = await asyncssh.connect(
                        self.server,
                        username=self.username,
                        password=self.password,
                        kbdint_handler=kbdint_handler,
                        known_hosts=None
                    )
                else:
                    ssh = await asyncssh.connect(
                        self.server,
                        username=self.username,
                        password=self.password,
                        known_hosts=None
                    )
            else:
                # Key-based authentication
                if self.password_2fa:
                    def kbdint_handler(name, instructions, prompts):
                        responses = []
                        for prompt_text, echo in prompts:
                            prompt_lower = prompt_text.lower()
                            if any(keyword in prompt_lower for keyword in ['verification', 'authenticator', 'token', 'code', '2fa', 'totp']):
                                responses.append(self.password_2fa or '')
                            else:
                                responses.append(self.password_2fa or '')
                        return responses
                    
                    ssh = await asyncssh.connect(
                        self.server,
                        username=self.username,
                        client_keys=client_keys,
                        kbdint_handler=kbdint_handler,
                        known_hosts=None
                    )
                else:
                    ssh = await asyncssh.connect(
                        self.server,
                        username=self.username,
                        client_keys=client_keys,
                        known_hosts=None
                    )
            
            # Store the SSH client in the dict with server as key
            self.asyncssh_ssh_clients[self.server] = ssh

        except Exception as e:
            self.asyncssh_ssh_clients[self.server] = None

            if ssh is not None:
                ssh.close()

            raise Exception("asyncssh ssh command failed:  %s: %s" % (e.__class__, e))
        
    def show_dialog(self, server, username, key_file, key_file_password, password, use_password, use_password_2fa, client_type=None):
        """Show password dialog and create SSH session (supports both Paramiko and AsyncSSH)"""
        if client_type is None:
            client_type = self.ssh_client_type
        
        if not self.is_alive(server, client_type):
            self.close(server, client_type)

            self.server = server
            self.username = username
            self.key_file = key_file
            self.key_file_password = key_file_password
            self.password = password
            self.password_2fa = None
            self.use_password = use_password
            self.ssh_client_type = client_type

            if self.check_password() and not use_password_2fa:
                if client_type == 'PARAMIKO':
                    self.paramiko_create_session(None, None)
                elif client_type == 'ASYNCSSH':
                    # Use existing event loop if available, otherwise create new one
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # If loop is running, schedule the coroutine
                            future = asyncio.ensure_future(self.asyncssh_create_session(None, None))
                            # Wait for completion (this is a hack, ideally should be handled differently)
                            while not future.done():
                                time.sleep(0.01)
                        else:
                            loop.run_until_complete(self.asyncssh_create_session(None, None))
                    except RuntimeError:
                        # No event loop in current thread, create new one
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            loop.run_until_complete(self.asyncssh_create_session(None, None))
                        finally:
                            loop.close()
            else:
                bpy.ops.wm.raas_password_input('INVOKE_DEFAULT')
                raise Exception("Password required")

    def create_ssh_command(self, key_file, destination, local_port, remote_host, remote_port, command):
        """create_ssh_command - Start a long-running SSH command process"""

        if not self.ssh_command_proc is None:
            self.ssh_command_proc.stop()
            self.ssh_command_proc = None

        self.ssh_command_proc = SSHCommand(
            user_host=destination,
            local_port=local_port,
            remote_host=remote_host,
            remote_port=remote_port,
            command=command,
            identity_file=key_file
        )

        # Start the command process (it will keep running in background)
        self.ssh_command_proc.start()

    def close_ssh_command(self):
        """close_ssh_command - Stop/kill the running SSH command process"""

        if not self.ssh_command_proc is None:
            self.ssh_command_proc.stop()
            self.ssh_command_proc = None

    def create_ssh_command_jump(self, key_file, jump_host, destination, local_port, remote_port, command):
        """create_ssh_command_jump - Start a long-running SSH command process through a jump host"""

        if not self.ssh_command_jump_proc is None:
            self.ssh_command_jump_proc.stop()
            self.ssh_command_jump_proc = None

        self.ssh_command_jump_proc = SSHCommandJump(
            user_host=destination,
            jump_host=jump_host,
            local_port=local_port,
            remote_port=remote_port,
            command=command,
            identity_file=key_file
        )

        # Start the command process (it will keep running in background)
        self.ssh_command_jump_proc.start()

    def close_ssh_command_jump(self):
        """close_ssh_command_jump - Stop/kill the running SSH command process with jump host"""

        if not self.ssh_command_jump_proc is None:
            self.ssh_command_jump_proc.stop()
            self.ssh_command_jump_proc = None

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

async def _ssh_async_jump(key_file, server1, server2, username, command):
    """ Execute an ssh command through a jump host (server1 -> server2) using ProxyJump """

    if username is None:
        user_server1 = '%s' % (server1)
        user_server2 = '%s' % (server2)
    else:
        user_server1 = '%s@%s' % (username, server1)
        user_server2 = '%s@%s' % (username, server2)

    if key_file is None:
        cmd = [
            'ssh',
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            '-J', user_server1,  # ProxyJump through server1
            user_server2,
            command
        ]
    else:
        cmd = [
            'ssh',
            '-i', key_file,
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            '-J', user_server1,  # ProxyJump through server1
            user_server2,
            command
        ]

    import asyncio
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        if stdout:
            print(f'[stdout]\n{stdout.decode()}')
        if stderr:
            print(f'[stderr]\n{stderr.decode()}')

        raise Exception("ssh jump command failed: %s" % cmd)

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
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            user_server, command
        ]
    else:
        cmd = [
            'ssh',
            '-i',  key_file,
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
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

async def _asyncssh_ssh_async(server, username, key_file, key_file_password, password, use_password, use_password_2fa, command):
        """ Execute an asyncssh ssh command (async version) """

        import asyncssh

        bpy.context.scene.raas_session.show_dialog(server, username, key_file, key_file_password, password, use_password, use_password_2fa, client_type='ASYNCSSH')

        try:
            # Get the SSH connection from the session
            conn = bpy.context.scene.raas_session.get_ssh(server, client_type='ASYNCSSH')
            
            if conn is None:
                raise Exception("AsyncSSH connection not available")

            # Execute command
            result = await conn.run(command, check=False)
            
            if result.exit_status != 0 and result.stderr:
                error_lines = result.stderr.strip().split('\n')
                if len(error_lines) > 1 or 'load bsc' not in error_lines[0]:
                    raise Exception(result.stderr)

            return result.stdout

        except Exception as e:
            raise Exception("asyncssh ssh command failed: %s: %s" % (e.__class__, e))

def _asyncssh_ssh(server, username, key_file, key_file_password, password, use_password, use_password_2fa, command):
        """ Execute an asyncssh ssh command (sync wrapper) """

        import asyncio

        # Use existing event loop if available, otherwise create new one
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running (in Blender context), we can't use run_until_complete
                # This should not happen if called from sync context
                raise RuntimeError("Cannot call sync version from async context")
            result = loop.run_until_complete(_asyncssh_ssh_async(server, username, key_file, key_file_password, password, use_password, use_password_2fa, command))
        except RuntimeError:
            # Create new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(_asyncssh_ssh_async(server, username, key_file, key_file_password, password, use_password, use_password_2fa, command))
            finally:
                loop.close()

        return result

def _paramiko_ssh(server, username, key_file, key_file_password, password, use_password, use_password_2fa, command):
        """ Execute an paramiko ssh command """

        import paramiko
        #from io import StringIO
        #from base64 import b64decode
        #from scp import SCPClient

        bpy.context.scene.raas_session.show_dialog(server, username, key_file, key_file_password, password, use_password, use_password_2fa, client_type='PARAMIKO')

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

async def _asyncssh_ssh_jump_async(server1, server2, username, key_file, key_file_password, password, use_password, use_password_2fa, command):
        """ Execute an asyncssh ssh command through a jump host (async version) """

        import asyncssh

        bpy.context.scene.raas_session.show_dialog(server1, username, key_file, key_file_password, password, use_password, use_password_2fa, client_type='ASYNCSSH')

        try:
            # Get the SSH connection to the jump host from the session
            jump_conn = bpy.context.scene.raas_session.get_ssh(server1, client_type='ASYNCSSH')
            
            if jump_conn is None:
                raise Exception("AsyncSSH connection to jump host not available")

            # Connect to target server (server2) through jump host
            # Note: We need to recreate the connection through the jump host each time
            # since AsyncSSH doesn't maintain persistent connections like Paramiko channels
            import asyncssh
            
            # Load client keys if needed
            client_keys = []
            if not use_password and key_file:
                try:
                    if key_file_password:
                        client_keys = [asyncssh.read_private_key(key_file, passphrase=key_file_password)]
                    else:
                        client_keys = [asyncssh.read_private_key(key_file)]
                except Exception as e:
                    raise Exception(f"Failed to load SSH key: {e}")
            
            if use_password:
                target_conn = await jump_conn.connect_ssh(
                    server2,
                    username=username,
                    password=password,
                    known_hosts=None
                )
            else:
                target_conn = await jump_conn.connect_ssh(
                    server2,
                    username=username,
                    client_keys=client_keys,
                    known_hosts=None
                )

            # Execute command on target server
            result = await target_conn.run(command, check=False)
            
            if result.exit_status != 0 and result.stderr:
                error_lines = result.stderr.strip().split('\n')
                if len(error_lines) > 1 or 'load bsc' not in error_lines[0]:
                    target_conn.close()
                    raise Exception(result.stderr)

            target_conn.close()
            return result.stdout

        except Exception as e:
            raise Exception("asyncssh ssh jump command failed: %s: %s" % (e.__class__, e))

def _asyncssh_ssh_jump(server1, server2, username, key_file, key_file_password, password, use_password, use_password_2fa, command):
        """ Execute an asyncssh ssh command through a jump host (sync wrapper) """

        import asyncio

        # Use existing event loop if available, otherwise create new one
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running (in Blender context), we can't use run_until_complete
                raise RuntimeError("Cannot call sync version from async context")
            result = loop.run_until_complete(_asyncssh_ssh_jump_async(server1, server2, username, key_file, key_file_password, password, use_password, use_password_2fa, command))
        except RuntimeError:
            # Create new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(_asyncssh_ssh_jump_async(server1, server2, username, key_file, key_file_password, password, use_password, use_password_2fa, command))
            finally:
                loop.close()

        return result

def _paramiko_ssh_jump(server1, server2, username, key_file, key_file_password, password, use_password, use_password_2fa, command):
        """ Execute an paramiko ssh command through a jump host (server1 -> server2) """

        import paramiko

        bpy.context.scene.raas_session.show_dialog(server1, username, key_file, key_file_password, password, use_password, use_password_2fa, client_type='PARAMIKO')

        result = None
        ssh_jump = None
        ssh_target = None
        
        try:
            # Get the SSH connection to the jump host (server1)
            ssh_jump = bpy.context.scene.raas_session.paramiko_get_ssh(server1)
            
            # Create a transport channel through the jump host to server2
            jump_transport = ssh_jump.get_transport()
            dest_addr = (server2, 22)
            local_addr = ('127.0.0.1', 0)
            jump_channel = jump_transport.open_channel("direct-tcpip", dest_addr, local_addr)
            
            # Create a new SSH client for the target server (server2)
            ssh_target = paramiko.SSHClient()
            ssh_target.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Load the key for authentication to server2
            if use_password:
                ssh_target.connect(server2, username=username, password=password, sock=jump_channel)
            else:
                try:
                    if key_file_password is None or len(key_file_password) == 0:
                        key = paramiko.RSAKey.from_private_key_file(key_file)
                    else:
                        key = paramiko.RSAKey.from_private_key_file(key_file, key_file_password)
                except Exception as e:
                    if key_file_password is None or len(key_file_password) == 0:
                        key = paramiko.Ed25519Key.from_private_key_file(key_file)
                    else:
                        key = paramiko.Ed25519Key.from_private_key_file(key_file, key_file_password)
                
                ssh_target.connect(server2, username=username, pkey=key, sock=jump_channel)
            
            # Execute the command on server2
            stdin, stdout, stderr = ssh_target.exec_command(command)
            result = stdout.readlines()
            error = stderr.readlines()
            
            if len(error) > 0 and (len(error) > 1 or 'load bsc' not in error[0]):
                raise Exception(str(error))
            
            # Close the target connection
            ssh_target.close()
            
        except Exception as e:
            if ssh_target is not None:
                ssh_target.close()
            
            raise Exception("paramiko ssh jump command failed: %s: %s" % (e.__class__, e))
        
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
    
    if preset.raas_ssh_library == 'ASYNCSSH':
        return await _asyncssh_ssh_async(server, username, key_file, key_file_password, password, use_password, use_password_2fa, command)
    elif preset.raas_ssh_library == 'PARAMIKO':
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
    
    if preset.raas_ssh_library == 'ASYNCSSH':
        return _asyncssh_ssh(server, username, key_file, key_file_password, password, use_password, use_password_2fa, command)
    elif preset.raas_ssh_library == 'PARAMIKO':
        return _paramiko_ssh(server, username, key_file, key_file_password, password, use_password, use_password_2fa, command)
    else:
        return _ssh_sync(None, server, None, command)
    

async def ssh_command_jump(server1, server2, command, preset):
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
    
    if preset.raas_ssh_library == 'ASYNCSSH':
        return await _asyncssh_ssh_jump_async(server1, server2, username, key_file, key_file_password, password, use_password, use_password_2fa, command)
    elif preset.raas_ssh_library == 'PARAMIKO':
        return _paramiko_ssh_jump(server1, server2, username, key_file, key_file_password, password, use_password, use_password_2fa, command)
    else:
        return await _ssh_async_jump(None, server1, server2, None, command)

def ssh_command_sync_jump(server1, server2, command, preset):
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
    
    if preset.raas_ssh_library == 'ASYNCSSH':
        return _asyncssh_ssh_jump(server1, server2, username, key_file, key_file_password, password, use_password, use_password_2fa, command)
    elif preset.raas_ssh_library == 'PARAMIKO':
        return _paramiko_ssh_jump(server1, server2, username, key_file, key_file_password, password, use_password, use_password_2fa, command)
    else:
        return _ssh_async_jump(None, server1, server2, None, command)
                  
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

async def _asyncssh_put_async(server, username, key_file, key_file_password, password, use_password, use_password_2fa, source, destination):
        """ Execute an asyncssh file upload (put) - async version """

        import asyncssh

        bpy.context.scene.raas_session.show_dialog(server, username, key_file, key_file_password, password, use_password, use_password_2fa, client_type='ASYNCSSH')

        try:
            # Get the SSH connection from the session
            conn = bpy.context.scene.raas_session.get_ssh(server, client_type='ASYNCSSH')
            
            if conn is None:
                raise Exception("AsyncSSH connection not available")

            # Upload file(s)
            async with conn.start_sftp_client() as sftp:
                await sftp.put(source, destination, recurse=True, preserve=True)

        except Exception as e:
            raise Exception("asyncssh put command failed: %s: %s" % (e.__class__, e))

def _asyncssh_put(server, username, key_file, key_file_password, password, use_password, use_password_2fa, source, destination):
        """ Execute an asyncssh file upload (put) - sync wrapper """

        import asyncio

        # Use existing event loop if available, otherwise create new one
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                raise RuntimeError("Cannot call sync version from async context")
            loop.run_until_complete(_asyncssh_put_async(server, username, key_file, key_file_password, password, use_password, use_password_2fa, source, destination))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_asyncssh_put_async(server, username, key_file, key_file_password, password, use_password, use_password_2fa, source, destination))
            finally:
                loop.close()

async def _asyncssh_get_async(server, username, key_file, key_file_password, password, use_password, use_password_2fa, source, destination):
        """ Execute an asyncssh file download (get) - async version """

        import asyncssh

        bpy.context.scene.raas_session.show_dialog(server, username, key_file, key_file_password, password, use_password, use_password_2fa, client_type='ASYNCSSH')

        try:
            # Get the SSH connection from the session
            conn = bpy.context.scene.raas_session.get_ssh(server, client_type='ASYNCSSH')
            
            if conn is None:
                raise Exception("AsyncSSH connection not available")

            # Download file(s)
            async with conn.start_sftp_client() as sftp:
                await sftp.get(source, destination, recurse=True, preserve=True)

        except Exception as e:
            raise Exception("asyncssh get command failed: %s: %s" % (e.__class__, e))

def _asyncssh_get(server, username, key_file, key_file_password, password, use_password, use_password_2fa, source, destination):
        """ Execute an asyncssh file download (get) - sync wrapper """

        import asyncio

        # Use existing event loop if available, otherwise create new one
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                raise RuntimeError("Cannot call sync version from async context")
            loop.run_until_complete(_asyncssh_get_async(server, username, key_file, key_file_password, password, use_password, use_password_2fa, source, destination))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_asyncssh_get_async(server, username, key_file, key_file_password, password, use_password, use_password_2fa, source, destination))
            finally:
                loop.close()

def _paramiko_put(server, username, key_file, key_file_password, password, use_password, use_password_2fa, source, destination):
        """ Execute an paramiko command """

        import paramiko
        from io import StringIO
        from base64 import b64decode
        from scp import SCPClient

        bpy.context.scene.raas_session.show_dialog(server, username, key_file, key_file_password, password, use_password, use_password_2fa, client_type='PARAMIKO')

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

        bpy.context.scene.raas_session.show_dialog(server, username, key_file, key_file_password, password, use_password, use_password_2fa, client_type='PARAMIKO')

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
    
    if preset.raas_ssh_library == 'ASYNCSSH':
        if to_cluster == True:
            source = job_local_dir
            destination = '%s/%s' % (str(sharedBasepath), job_remote_dir)
            print('copy from %s to server' % (job_local_dir))
            await _asyncssh_put_async(serverHostname, username, key_file, key_file_password, password, use_password, use_password_2fa, source, destination)
        else:
            destination = job_local_dir
            source = '%s/%s' % (str(sharedBasepath), job_remote_dir)
            print('copy from server to: %s' % (job_local_dir))
            await _asyncssh_get_async(serverHostname, username, key_file, key_file_password, password, use_password, use_password_2fa, source, destination)
    elif preset.raas_ssh_library == 'PARAMIKO':
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
