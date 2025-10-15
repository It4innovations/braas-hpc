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

import importlib
import sys
import subprocess
from collections import namedtuple
import functools
import logging
import os.path
import tempfile

import datetime
import typing

import bpy
from bpy.types import AddonPreferences, Operator, WindowManager, Scene, PropertyGroup
from bpy.props import StringProperty, EnumProperty, PointerProperty, BoolProperty, IntProperty
import rna_prop_ui

from . import async_loop
from . import raas_server
from . import raas_jobs
from . import raas_config
from . import raas_render

ADDON_NAME = 'braas-hpc'

log = logging.getLogger(__name__)


@functools.lru_cache()
def factor(factor: float) -> dict:
    """Construct keyword argument for UILayout.split().

    On Blender 2.8 this returns {'factor': factor}, and on earlier Blenders it returns
    {'percentage': factor}.
    """
    if bpy.app.version < (2, 80, 0):
        return {'percentage': factor}
    return {'factor': factor}

##################################################


def show_message_box(message="", title="BRaaS-HPC", icon='INFO'):

    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)


##################################################

Dependency = namedtuple("Dependency", ["module", "package", "name"])
python_dependencies = (Dependency(module="paramiko", package="paramiko", name=None),
                       Dependency(module="scp", package="scp", name=None),
                       )
                    #    Dependency(module="blender_asset_tracer",
                    #               package="blender_asset_tracer", name=None),


internal_dependencies = []


def import_module(module_name, global_name=None, reload=True):
    if global_name is None:
        global_name = module_name

    if global_name in globals():
        importlib.reload(globals()[global_name])
    else:
        # Attempt to import the module and assign it to globals dictionary. This allow to access the module under
        # the given name, just like the regular import would.
        globals()[global_name] = importlib.import_module(module_name)


def install_pip():
    try:
        if bpy.app.version < (2, 90, 0):
            python_exe = bpy.app.binary_path_python
        else:
            python_exe = sys.executable

        # Check if pip is already installed
        subprocess.run([python_exe, "-m", "pip", "--version"], check=True)

        # Upgrade
        subprocess.run([python_exe, "-m", "pip", "install",
                       "--upgrade", "pip"], check=True)

    except subprocess.CalledProcessError:
        import ensurepip

        ensurepip.bootstrap()
        os.environ.pop("PIP_REQ_TRACKER", None)


def install_and_import_module(module_name, package_name=None, global_name=None):
    if package_name is None:
        package_name = module_name

    if global_name is None:
        global_name = module_name

    # Create a copy of the environment variables and modify them for the subprocess call
    environ_copy = dict(os.environ)
    environ_copy["PYTHONNOUSERSITE"] = "1"

    if bpy.app.version < (2, 90, 0):
        python_exe = bpy.app.binary_path_python
    else:
        python_exe = sys.executable

    subprocess.run([python_exe, "-m", "pip", "install",
                   package_name], check=True, env=environ_copy)

    # The installation succeeded, attempt to import the module again
    import_module(module_name, global_name)

################################################################


def _paramiko_generate_ssh_key(private_filepath, public_filepath, password):

    import paramiko
    key = paramiko.RSAKey.generate(2048)
    key.write_private_key_file(private_filepath, password)

    public_key = "%s %s" % (key.get_name(), key.get_base64())
    with open(public_filepath, "w") as f:
        f.write(public_key)

    f.close()


class RAAS_OT_generate_sshkey(Operator):
    bl_idname = 'raas.generate_sshkey'
    bl_label = 'Generate a public/private key pair'
    bl_description = ("Generate SSH Key")

    def execute(self, context):
        try:
            if not preferences().check_valid_settings_gen(type='GENERATE'):
                return {"CANCELLED"}

            if len(preferences().raas_gen_public_key_path) == 0:
                preferences().raas_gen_public_key_path = preferences(
                ).raas_job_storage_path + '/raas_gen.public.key'

            if len(preferences().raas_gen_private_key_path) == 0:
                preferences().raas_gen_private_key_path = preferences(
                ).raas_job_storage_path + '/raas_gen.private.key'

            _paramiko_generate_ssh_key(preferences().raas_gen_private_key_path, preferences(
            ).raas_gen_public_key_path, preferences().raas_gen_password)

        except Exception as e:
            import traceback
            traceback.print_exc()

            self.report({'ERROR'}, "Problem with %s: %s: %s" %
                        (self.bl_label, e.__class__, e))
            return {"CANCELLED"}

        self.report({'INFO'}, "'%s' finished" % (self.bl_label))
        return {"FINISHED"}


class RAAS_OT_upload_sshkey(Operator):
    bl_idname = 'raas.upload_sshkey'
    bl_label = 'Upload public key'
    bl_description = ("Upload SSH Key")

    def execute(self, context):
        try:
            if not preferences().check_valid_settings_gen():
                return {"CANCELLED"}

            if len(preferences().raas_gen_public_key_path) > 0:
                with open(preferences().raas_gen_public_key_path) as f:
                    public_key = f.readlines()

                bpy.context.window_manager.clipboard = public_key[0]

            import webbrowser
            if preferences().raas_account_type == "EDUID":
                webbrowser.open(
                    'https://signup.e-infra.cz/fed/registrar/?vo=IT4Innovations', new=2)
            else:
                webbrowser.open('https://extranet.it4i.cz/ssp/?action=changesshkey&login=%s' %
                                preferences().raas_gen_username, new=2)

        except Exception as e:
            import traceback
            traceback.print_exc()

            self.report({'ERROR'}, "Problem with %s: %s: %s" %
                        (self.bl_label, e.__class__, e))
            return {"CANCELLED"}

        self.report({'INFO'}, "'%s' finished" % (self.bl_label))
        return {"FINISHED"}


# class RAAS_OT_setup_sshkey(Operator):
#     bl_idname = 'raas.setup_sshkey'
#     bl_label = 'Setup'
#     bl_description = ("Setup")

#     def execute(self, context):
#         try:
#             pref = preferences()

#             if not pref.check_valid_settings_gen():
#                 return {"CANCELLED"}

#             pref.raas_da_username = pref.raas_gen_username
#             pref.raas_private_key_path = pref.raas_gen_private_key_path
#             pref.raas_private_key_password = pref.raas_gen_password
#             pref.raas_pid = pref.raas_gen_pid
#             pref.raas_project_group = pref.raas_da_username

#             # TODO
#             if not pref.check_valid_settings(type='PROJECT_DIR'):
#                 return {"CANCELLED"}

#             cmd = raas_jobs.CmdGetPidDir(pref.raas_pid.upper())
#             if len(cmd) > 0:
#                 server = raas_config.GetDAServer(context)
#                 res = raas_render.ssh_command_sync(server, cmd)
#                 pref.raas_pid_dir = res.strip()

#         except Exception as e:
#             import traceback
#             traceback.print_exc()

#             self.report({'ERROR'}, "Problem with %s: %s: %s" %
#                         (self.bl_label, e.__class__, e))
#             return {"CANCELLED"}

#         self.report({'INFO'}, "'%s' finished" % (self.bl_label))
#         return {"FINISHED"}


# class RAAS_OT_find_pid_dir(Operator):
#     bl_idname = 'raas.find_pid_dir'
#     bl_label = 'Find Project Dir'
#     bl_description = ("Find Project Dir")

#     def execute(self, context):
#         # success = True

#         for cl in raas_config.Cluster_items:
#             try:
#                 if not preferences().check_valid_settings(type='PROJECT_DIR'):
#                     return {"CANCELLED"}

#                 cmd = raas_jobs.CmdGetPidDir(preferences().raas_pid.upper())
#                 if len(cmd) > 0:
#                     # server = raas_config.GetDAServer(context)
#                     server = raas_config.GetServerFromType(cl[0])
#                     res = raas_render.ssh_command_sync(server, cmd)
#                     preferences().raas_pid_dir = res.strip()

#                     break

#             except Exception as e:
#                 import traceback
#                 traceback.print_exc()

#                 self.report({'ERROR'}, "Problem with %s: %s: %s" %
#                             (self.bl_label, e.__class__, e))
#                 # return {"CANCELLED"}
#                 # success = False

#         self.report({'INFO'}, "'%s' finished" % (self.bl_label))
#         return {"FINISHED"}


class RAAS_OT_install_scripts(Operator):
    bl_idname = 'raas.install_scripts'
    bl_label = 'Install scripts on the cluster'
    bl_description = ("Install scripts")

    def execute(self, context):
        for cl in raas_config.Cluster_items:
            try:
                #presets_tuples = [(p.cluster_name, p.is_active) for p in preferences().cluster_presets] 

                for p in preferences().cluster_presets:
                    if p.cluster_name == cl[0] and p.is_active:
                        # TODO: MJ
                        if not preferences().check_valid_settings(p, type='INSTALL_SCRIPTS'):
                            return {"CANCELLED"}
                                        
                        # Install scripts
                        self.report({'INFO'}, "Install scripts on '%s'" % (cl[0]))
                        cmd = raas_config.GetGitAddonCommand(preferences(
                        ).raas_scripts_repository, preferences().raas_scripts_repository_branch)
                        if len(cmd) > 0:
                            server = raas_config.GetServerFromType(cl[0])
                            raas_render.ssh_command_sync(server, cmd, p)

                            #preferences().raas_scripts_installed = True

                        # Install Blender
                        self.report({'INFO'}, "Install Blender on '%s'" % (cl[0]))
                        cmd = raas_config.GetBlenderInstallCommand(p, preferences().raas_blender_link)
                        if len(cmd) > 0:
                            server = raas_config.GetServerFromType(cl[0])
                            raas_render.ssh_command_sync(server, cmd, p)

                            #preferences().raas_blender_installed = True

                        # Apply patches
                        self.report({'INFO'}, "Apply patches on '%s'" % (cl[0]))
                        cmd = raas_config.GetBlenderPatchCommand(p, preferences().raas_blender_link)
                        if len(cmd) > 0:
                            server = raas_config.GetServerFromType(cl[0])
                            raas_render.ssh_command_sync(server, cmd, p)                            

                        preferences().raas_scripts_installed = True

                        break

            except Exception as e:
                import traceback
                traceback.print_exc()

                self.report({'ERROR'}, "Problem with %s: %s: %s" %
                            (self.bl_label, e.__class__, e))
                self.report({'ERROR'}, "Scripts could not be installed.")
                return {"CANCELLED"}

        self.report({'INFO'}, "'%s' finished" % (self.bl_label))
        return {"FINISHED"}
    
# class RAAS_OT_install_blender(Operator):
#     bl_idname = 'raas.install_blender'
#     bl_label = 'Install Blender on the cluster'
#     bl_description = ("Install Blender")

#     def execute(self, context):
#         for cl in raas_config.Cluster_items:
#             try:
#                 # presets_tuples = [(p.cluster_name, p.is_active) for p in preferences().cluster_presets] 
#                 # if not preferences().check_valid_settings(cl, type='INSTALL_BLENDER'):
#                 #     return {"CANCELLED"}

#                 for p in preferences().cluster_presets:
#                     #if (cl[0], True) in presets_tuples:
#                     if p.cluster_name == cl[0] and p.is_active:
#                         # TODO: MJ
#                         if not preferences().check_valid_settings(p, type='INSTALL_SCRIPTS'):
#                             return {"CANCELLED"}
                                                                 
#                         self.report({'INFO'}, "Install Blender on '%s'" % (cl[0]))

#                         cmd = raas_config.GetBlenderInstallCommand(preferences().raas_blender_link)
#                         if len(cmd) > 0:
#                             server = raas_config.GetServerFromType(cl[0])
#                             raas_render.ssh_command_sync(server, cmd, p)

#                             preferences().raas_blender_installed = True
#                         break

#             except Exception as e:
#                 import traceback
#                 traceback.print_exc()

#                 self.report({'ERROR'}, "Problem with %s: %s: %s" %
#                             (self.bl_label, e.__class__, e))
#                 self.report({'ERROR'}, "Blender could not be installed.")
#                 return {"CANCELLED"}

#         self.report({'INFO'}, "'%s' finished" % (self.bl_label))
#         return {"FINISHED"}    

##################################################################


class RAAS_OT_install_dependencies(Operator):
    bl_idname = 'raas.install_dependencies'
    bl_label = 'Install dependencies'
    bl_description = ("Downloads and installs the required python packages for this add-on. "
                      "Internet connection is required. Blender may have to be started with "
                      "elevated permissions in order to install the package")

    def execute(self, context):
        try:
            install_pip()
            for dependency in python_dependencies:
                install_and_import_module(module_name=dependency.module,
                                          package_name=dependency.package,
                                          global_name=dependency.name)

            # enable_internal_addons()
            # install_external_addons()

        except (subprocess.CalledProcessError, ImportError) as err:
            self.report({"ERROR"}, str(err))
            return {"CANCELLED"}

        preferences().dependencies_installed = True

        # Register the panels, operators, etc. since dependencies are installed
        # from . import sim_scene
        # sim_scene.register()

        self.report({'INFO'}, "'%s' finished" % (self.bl_label))
        return {"FINISHED"}


class RAAS_OT_update_dependencies(Operator):
    bl_idname = 'raas.update_dependencies'
    bl_label = 'Update dependencies'
    bl_description = ("Downloads and installs the required python packages for this add-on. "
                      "Internet connection is required. Blender may have to be started with "
                      "elevated permissions in order to install the package")

    def execute(self, context):
        try:
            install_pip()
            for dependency in python_dependencies:
                install_and_import_module(module_name=dependency.module,
                                          package_name=dependency.package,
                                          global_name=dependency.name)

            # enable_internal_addons()
            # install_external_addons()

        except (subprocess.CalledProcessError, ImportError) as err:
            self.report({"ERROR"}, str(err))
            return {"CANCELLED"}

        preferences().dependencies_installed = True

        # Register the panels, operators, etc. since dependencies are installed
        # from . import sim_scene
        # sim_scene.register()

        self.report({'INFO'}, "'%s' finished" % (self.bl_label))
        return {"FINISHED"}
##################################################

class RAAS_OT_NewClusterPreset(bpy.types.Operator):
    """Create a new cluster preset"""
    bl_idname = "pref.newcluster"
    bl_label = "Add a new cluster"

    def draw(self, context):
        layout = self.layout


    def execute(self, context):
        addonprefs = preferences()
        addonprefs.cluster_presets.add()  # New preset

        return {'FINISHED'}
    
class RAAS_OT_RemoveClusterPreset(bpy.types.Operator):
    """Removes a cluster preset"""
    bl_idname = "pref.removecluster"
    bl_label = ""
    
    index: bpy.props.IntProperty()

    def draw(self, context):
        layout = self.layout


    def execute(self, context):
        addonprefs = preferences()
        addonprefs.cluster_presets.remove(self.index)  # Remove this preset

        return {'FINISHED'}
    
def cluster_partition_settings_callback(self, context):
    """Returns a list partitions dynamically based on the cluster selected.

    Returns:
        _list_: _A list of cluster partitions._
    """
    tmp = [cl[0] for cl in raas_config.Cluster_items]
    if self.cluster_name not in tmp:
        return []
    else:
        return getattr(raas_config, "%s_partitions" % self.cluster_name.capitalize())
    
    
class ClusterPresets(bpy.types.PropertyGroup):
    """
        A property group of cluster presets. Each presets has the following properties:
        cluster_name, partition_name (queue), allocation_name, is_active, working_dir.
    """

    cluster_name: bpy.props.EnumProperty(
        name="Cluster",
        description="Select a cluster",
        items=raas_config.Cluster_items
    ) # type: ignore

    partition_name: bpy.props.EnumProperty(
        name="Partition/Queue",
        description="Select a partition/queue",
        items=cluster_partition_settings_callback
    ) # type: ignore

    allocation_name: bpy.props.StringProperty(
        name="Project",
        description="Project allocation name",
        default=""
    ) # type: ignore

    job_type : bpy.props.EnumProperty(
        items=raas_config.JobQueue_items,
        name="Type of Job (resources)"
    ) # type: ignore

    is_active: bpy.props.BoolProperty(
        name="Active",
        description="This settings is active",
        default=True
    ) # type: ignore
    
    working_dir: StringProperty(
        name='Project Dir',
        description='The PROJECT data storage is a central storage for projects/users data on IT4Innovations, e.g. /mnt/projX/OPEN-XX-XX, /mnt/projX/DD-XX-XX',
        default=''
    ) # type: ignore

    raas_da_username: StringProperty(
        name='Username',
        default=''
    ) # type: ignore

    raas_da_password: StringProperty(
        name='Password',
        default='',
        subtype='PASSWORD'
    ) # type: ignore

    raas_da_use_password: bpy.props.BoolProperty(
        name="Use Password",
        default=False
    ) # type: ignore

    raas_private_key_path: StringProperty(
        name='Private Key Path',
        description='Private Key Path',
        subtype='FILE_PATH',
        default=''
    ) # type: ignore 

    raas_private_key_password: StringProperty(
        name='Key Passphrase',
        default='',
        subtype='PASSWORD'
    ) # type: ignore

    raas_ssh_library: EnumProperty(
        name='SSH Library',
        items=raas_config.ssh_library_items
    ) # type: ignore    

class RAAS_OT_find_working_dir(Operator):
    """
        Goes through all cluster presets and for each finds the remote working directory.
    """
    bl_idname = 'raas.find_working_dir'
    bl_label = 'Find Working Dirs'
    bl_description = ("Find")

    def execute(self, context):
        try:            
            # Get the cluster presets
            addonprefs = preferences()
            for preset in addonprefs.cluster_presets:
                if not preferences().check_valid_settings(preset, type='PROJECT_DIR'):
                    return {"CANCELLED"}

                if preset.allocation_name != "" and len(preset.working_dir) == 0:
                    raas_config.GetPidDir(preset)  # sets the working_dir in the preset

                # # Test connection
                # if preset.is_active:
                #     server = raas_config.GetServerFromType(preset.cluster_name.upper())
                #     cmd = 'hostname'
                #     res = raas_render.ssh_command_sync(server, cmd, preset)
                #     print("Test connection to %s: %s" % (preset.cluster_name, res.strip()))

        except Exception as e:
            import traceback
            traceback.print_exc()

            self.report({'ERROR'}, "Problem with %s: %s: %s" %
                        (self.bl_label, e.__class__, e))

        self.report({'INFO'}, "'%s' finished" % (self.bl_label))
        return {"FINISHED"}
    
class RAAS_OT_test_connection(Operator):
    """
        Goes through all cluster presets and for each tests the connection.
    """
    bl_idname = 'raas.test_connection'
    bl_label = 'Test Connections'
    bl_description = ("Test")

    def execute(self, context):
        try:            
            # Get the cluster presets
            addonprefs = preferences()
            for preset in addonprefs.cluster_presets:
                # if not preferences().check_valid_settings(preset, type='PROJECT_DIR'):
                #     return {"CANCELLED"}

                # if preset.allocation_name != "" and len(preset.working_dir) == 0:
                #     raas_config.GetPidDir(preset)  # sets the working_dir in the preset

                # Test connection
                if preset.is_active:
                    server = raas_config.GetServerFromType(preset.cluster_name.upper())
                    cmd = 'hostname'
                    res = raas_render.ssh_command_sync(server, cmd, preset)
                    print("Test connection to %s: %s" % (preset.cluster_name, res.strip()))

        except Exception as e:
            import traceback
            traceback.print_exc()

            self.report({'ERROR'}, "Problem with %s: %s: %s" %
                        (self.bl_label, e.__class__, e))

        self.report({'INFO'}, "'%s' finished" % (self.bl_label))
        return {"FINISHED"}    
            
    
class RaasPreferences(AddonPreferences):
    bl_idname = ADDON_NAME

    error_message: StringProperty(
        name='Error Message',
        default='',
        options={'HIDDEN', 'SKIP_SAVE'}
    ) # type: ignore

    ok_message: StringProperty(
        name='Message',
        default='',
        options={'HIDDEN', 'SKIP_SAVE'}
    ) # type: ignore

    show_ssh_gen: BoolProperty(
        default=False
    ) # type: ignore

    # raas_server: StringProperty(
    #     name='RaaS Server',
    #     default=''
    # )

    raas_username: StringProperty(
        name='Username',
        description='Username to access the server',
        default=''
    ) # type: ignore

    raas_password: StringProperty(
        name='Password',
        description='Password to access the server',
        default='',
        subtype='PASSWORD'
    ) # type: ignore

    ## Adding new clusters
    cluster_presets: bpy.props.CollectionProperty(type=ClusterPresets)

    raas_working_dir: StringProperty(
        name='Project Dir',
        description='The PROJECT data storage is a central storage for projects/users data on IT4Innovations, e.g. /mnt/projX/OPEN-XX-XX, /mnt/projX/DD-XX-XX',
        default=''
    ) # type: ignore

    raas_pid_name: StringProperty(
        name='Project ID',
        description='Computing resource allocated by the project allocation committee to the primary investigator, e.g. OPEN-XX-XX, DD-XX-XX',
        default=''
    ) # type: ignore

    raas_pid_queue: StringProperty(
        name='Project Queue',
        description='The queue for running the job on the cluster, e.g. qcpu, qgpu',
        default='qcpu'
    ) # type: ignore

    raas_pid_dir: StringProperty(
        name='Project Dir',
        description='The PROJECT data storage is a central storage for projects/users data on IT4Innovations, e.g. /mnt/projX/OPEN-XX-XX, /mnt/projX/DD-XX-XX',
        default=''
    ) # type: ignore

    #############################################################

    raas_job_storage_path: StringProperty(
        name='Local Storage Path',
        description='Path where to store job files',
        subtype='DIR_PATH',
        default=tempfile.gettempdir()
    ) # type: ignore

    dependencies_installed: BoolProperty(
        default=False
    ) # type: ignore

    # raas_use_paramiko: BoolProperty(
    #     name='Use Paramiko',
    #     default=True
    # )

    # raas_ssh_library: EnumProperty(
    #     name='SSH Library',
    #     items=raas_config.ssh_library_items
    # ) # type: ignore

    raas_account_type: EnumProperty(
        name='Account Type',
        items=raas_config.account_types_items
    ) # type: ignore

    raas_project_group: StringProperty(
        name='Working Group',
        default=''
    ) # type: ignore

    # raas_da_username: StringProperty(
    #     name='Username',
    #     default=''
    # )

    # raas_private_key_password: StringProperty(
    #     name='Key Passphrase',
    #     default='',
    #     subtype='PASSWORD'
    # )

    # raas_private_key_path: StringProperty(
    #     name='Private Key Path',
    #     description='Private Key Path',
    #     subtype='FILE_PATH',
    #     default=''
    # )    

    raas_gen_private_key_path: StringProperty(
        name='Gen. Private Key Path',
        description='Gen. Private Key Path',
        subtype='FILE_PATH',
        default=''
    ) # type: ignore

    raas_gen_public_key_path: StringProperty(
        name='Gen. Public Key Path',
        description='Gen. Public Key Path',
        subtype='FILE_PATH',
        default=''
    ) # type: ignore

    raas_scripts_repository: StringProperty(
        name='Repository',
        default='https://github.com/It4innovations/braas-hpc.git'
    ) # type: ignore

    raas_scripts_repository_branch: StringProperty(
        name='Branch',
        default='master'
    ) # type: ignore

    raas_blender_link: StringProperty(
        name='Link',
        default='https://ftp.nluug.nl/pub/graphics/blender/release/Blender4.5/blender-4.5.3-linux-x64.tar.xz'
    ) # type: ignore

    raas_scripts_installed: BoolProperty(
        default=False
    ) # type: ignore

    # raas_blender_installed: BoolProperty(
    #     default=False
    # ) # type: ignore    

    # raas_gen_pid: StringProperty(
    #     name='Project ID',
    #     default=''
    # )

    raas_gen_username: StringProperty(
        name='Username',
        default=''
    ) # type: ignore

    raas_gen_password: StringProperty(
        name='Key Passphrase',
        default='',
        subtype='PASSWORD'
    ) # type: ignore

    def check_valid_settings(self, cl, type='NONE'):
        if cl.raas_ssh_library == 'PARAMIKO':
            if len(cl.raas_da_username) == 0:
                show_message_box(
                    message='Username is not set in preferences', icon='ERROR')
                return False

            if  not cl.raas_da_use_password and len(cl.raas_private_key_path) == 0:
                show_message_box(
                    message='Private Key File is not set in preferences', icon='ERROR')
                return False

        if not self.raas_scripts_installed and type != 'PROJECT_DIR' and type != 'INSTALL_SCRIPTS' and type != 'INSTALL_BLENDER':
            show_message_box(
                message='Scripts are not installed', icon='ERROR')
            return False
        
        if len(self.raas_scripts_repository) == 0 or len(self.raas_scripts_repository_branch) == 0:
            show_message_box(
                message='Git repository is not set in preferences', icon='ERROR')
            return False        
        
        # if not self.raas_blender_installed and type != 'PROJECT_DIR' and type != 'INSTALL_SCRIPTS' and type != 'INSTALL_BLENDER':
        #     show_message_box(
        #         message='Blender is not installed', icon='ERROR')
        #     return False        

        if len(self.raas_blender_link) == 0:
            show_message_box(
                message='Link to Blender is not set in preferences', icon='ERROR')
            return False

        if not self.dependencies_installed:
            show_message_box(
                message='Dependencies are not installed', icon='ERROR')
            return False

        if not self.raas_job_storage_path and type != 'PROJECT_DIR' and type != 'INSTALL_SCRIPTS' and type != 'INSTALL_BLENDER':
            show_message_box(
                message='Local Storage Path is not set in preferences', icon='ERROR')
            return False

        return True

    def check_valid_settings_gen(self, type='NONE'):
        if not self.dependencies_installed:
            show_message_box(
                message='Dependencies are not installed', icon='ERROR')
            return False

        # if len(self.raas_gen_pid) == 0:
        #     show_message_box(
        #         message='Project ID is not set in the generate SSH keys section', icon='ERROR')
        #     return False

        if len(self.raas_gen_username) == 0:
            show_message_box(
                message='Username is not set in the generate SSH keys section', icon='ERROR')
            return False

        if len(self.raas_gen_public_key_path) == 0 and type != 'GENERATE':
            show_message_box(
                message='Public Key File is not set in the generate SSH keys section', icon='ERROR')
            return False

        if len(self.raas_gen_private_key_path) == 0 and type != 'GENERATE':
            show_message_box(
                message='Private Key File is not set in the generate SSH keys section', icon='ERROR')
            return False

        if len(self.raas_gen_password) == 0:
            show_message_box(
                message='Key Passphrase is not set in the generate SSH keys section', icon='ERROR')
            return False

        return True

    def reset_messages(self):
        self.ok_message = ''
        self.error_message = ''

    def draw(self, context):
        layout = self.layout

        # raas_pid = box.split(**factor(0.25), align=True)
        # raas_pid.label(text='Project ID:')
        # pid_box = raas_pid.row(align=True)
        # pid_box.prop(self, 'raas_pid', text='')


        # if self.raas_ssh_library == 'PARAMIKO':
        #     box = layout.box()
            
        #     auth_split = box.split(**factor(0.25), align=True)
        #     auth_split.label(text='Username:')
        #     user_box = auth_split.row(align=True)
        #     user_box.prop(self, 'raas_da_username', text='')

        #     pkey_split = box.split(**factor(0.25), align=True)
        #     pkey_split.label(text='Private Key File:')
        #     user_box = pkey_split.row(align=True)
        #     user_box.prop(self, 'raas_private_key_path', text='')

        #     auth_split = box.split(**factor(0.25), align=True)
        #     auth_split.label(text='Key Passphrase:')
        #     user_box = auth_split.row(align=True)
        #     user_box.prop(self, 'raas_private_key_password', text='')

        # raas_pid_dir = box.split(**factor(0.25), align=True)
        # raas_pid_dir.label(text='Project Dir:')
        # pid_dir_box = raas_pid_dir.row(align=True)
        # pid_dir_box.prop(self, 'raas_pid_dir', text='')
        # pid_dir_box.operator(RAAS_OT_find_pid_dir.bl_idname, icon="CONSOLE")
        
        box = layout.box()

        raas_pid = box.split(**factor(1.0), align=True)
        pid_box = raas_pid.row(align=True)    
        pid_box.label(text='Cluster settings:')

        raas_pid = box.split(**factor(1.0), align=True)
        pid_box = raas_pid.row(align=True)
        pid_box.operator("pref.newcluster", icon="ADD")
        
        for idx, preset in enumerate(self.cluster_presets):
            if preset.working_dir == '' or preset.allocation_name == '':
                preset.is_active = False
            box_row = box.box()
            raas_pid = box_row.split(**factor(1.0), align=True)
            pid_box = raas_pid.column(align=True)
            pid_box.prop(preset, "cluster_name")
            pid_box.prop(preset, "partition_name")
            pid_box.prop(preset, "job_type")

            raas_pid = box_row.split(**factor(1.0), align=True)
            pid_box = raas_pid.column(align=True)
            pid_box.prop(preset, "raas_da_username")
            pid_box.prop(preset, "raas_da_use_password")
            
            if preset.raas_da_use_password:
                pid_box.prop(preset, "raas_da_password")
            else:
                pid_box.prop(preset, "raas_private_key_path")
                pid_box.prop(preset, "raas_private_key_password")

            raas_pid = box_row.split(**factor(1.0), align=True)
            pid_box = raas_pid.column(align=True)
            pid_box.prop(preset, "raas_ssh_library")                

            raas_pid = box_row.split(**factor(1.0), align=True)
            pid_box = raas_pid.column(align=True)
            pid_box.prop(preset, "allocation_name")
            pid_box.prop(preset, "working_dir", text='Dir')
            pid_box.prop(preset, "is_active")
            pid_box.operator("pref.removecluster", icon="CANCEL").index = idx


        if len(self.cluster_presets) > 0:
            raas_pid = box.split(**factor(1.0), align=True)
            pid_box = raas_pid.column(align=True)
            pid_box.operator(RAAS_OT_find_working_dir.bl_idname, icon="CONSOLE")
            pid_box.operator(RAAS_OT_test_connection.bl_idname, icon="CONSOLE")

        box = layout.box()

        raas_box = box.column()
        path_split = raas_box.split(**factor(0.25), align=True)
        path_split.label(text='Local Storage Path:')
        path_box = path_split.row(align=True)
        path_box.prop(self, 'raas_job_storage_path', text='')
        props = path_box.operator(
            'raas.explore_file_path', text='', icon='DISK_DRIVE')
        props.path = self.raas_job_storage_path

        raas_pgroup = box.split(**factor(0.25), align=True)
        raas_pgroup.label(text='Working Group:')
        pgroup_box = raas_pgroup.row(align=True)
        pgroup_box.prop(self, 'raas_project_group', text='')

        boxD = layout.box()
        boxD.label(text='Blender dependencies:')

        dependencies_installed = preferences().dependencies_installed
        if not dependencies_installed:
            boxD.label(text='Dependencies are not installed', icon='ERROR')

        if not dependencies_installed:
            boxD.operator(RAAS_OT_install_dependencies.bl_idname,
                          icon="CONSOLE")
        else:
            boxD.operator(RAAS_OT_update_dependencies.bl_idname,
                          icon="CONSOLE")

        # box = layout.box()

        # par_split = box.split(**factor(0.25), align=True)
        # par_split.label(text='SSH Library:')
        # user_box = par_split.row(align=True)        
        # user_box.prop(self, 'raas_ssh_library', text='')  

        box = layout.box()

        boxG = box.box()
        boxG.label(text='Install scripts and Blender:')
        rep_split = boxG.split(**factor(0.25), align=True)
        rep_split.label(text='Git Repository (Scripts):')
        rep_box1 = rep_split.row(align=True)
        rep_box = rep_box1.row(align=True)
        # rep_box.enabled = False
        rep_box.prop(self, 'raas_scripts_repository', text='')
        rep_box = rep_box1.row(align=True)
        # rep_box.enabled = True
        rep_box.prop(self, 'raas_scripts_repository_branch', text='')
            
        #boxG = box.box()
        #boxG.label(text='Install Blender:')
        rep_split = boxG.split(**factor(0.25), align=True)
        rep_split.label(text='Link (Blender):')
        rep_box1 = rep_split.row(align=True)
        rep_box = rep_box1.row(align=True)
        rep_box.prop(self, 'raas_blender_link', text='')

        rep_split = boxG.split(**factor(0.25), align=True)
        rep_split.label(text='Manual Installation / Scripts allready installed:')
        rep_box1 = rep_split.row(align=True)
        rep_box = rep_box1.row(align=True)
        rep_box.prop(self, 'raas_scripts_installed', text='')

        # if self.raas_scripts_installed == False:
        #     if not self.raas_scripts_installed:
        #         boxG.label(text='Scripts are not installed', icon='ERROR')

        #     boxG.operator(RAAS_OT_install_scripts.bl_idname,
        #                     icon="CONSOLE", text="Install scripts on the cluster")
        # else:
        #     boxG.operator(RAAS_OT_install_scripts.bl_idname,
        #                     icon="CONSOLE", text="Update scripts")


        # if self.raas_blender_installed == False:
        #     if not self.raas_blender_installed:
        #         boxG.label(text='Blender is not installed', icon='ERROR')

        #     boxG.operator(RAAS_OT_install_blender.bl_idname,
        #                     icon="CONSOLE", text="Install Blender on the cluster")
        # else:
        #     boxG.operator(RAAS_OT_install_blender.bl_idname,
        #                     icon="CONSOLE", text="Update Blender")

        if self.raas_scripts_installed == False: # or self.raas_blender_installed == False:
            if not self.raas_scripts_installed:
                boxG.label(text='Scripts are not installed', icon='ERROR')

            # if not self.raas_blender_installed:
            #     boxG.label(text='Blender is not installed', icon='ERROR')

            boxG.operator(RAAS_OT_install_scripts.bl_idname,
                            icon="CONSOLE", text="Install scripts and Blender on the cluster(s)")
        else:
            boxG.operator(RAAS_OT_install_scripts.bl_idname,
                            icon="CONSOLE", text="Update scripts and Blender on the cluster(s)")

        # boxG = box.box()
        # show_gen_split = boxG.split(**factor(0.25), align=True)
        # show_gen_split.label(text='Generate SSH keys:')
        # user_box = show_gen_split.row(align=True)
        # user_box.prop(self, 'show_ssh_gen', text='')

        # if self.raas_ssh_library == 'PARAMIKO' and self.show_ssh_gen == True:

        #     # boxG.label(text='Generate SSH keys:')

        #     # raas_pid = boxG.split(**factor(0.25), align=True)
        #     # raas_pid.label(text='Project ID:')
        #     # pid_box = raas_pid.row(align=True)
        #     # pid_box.prop(self, 'raas_gen_pid', text='')

        #     auth_split = boxG.split(**factor(0.25), align=True)
        #     auth_split.label(text='Username:')
        #     user_box = auth_split.row(align=True)
        #     user_box.prop(self, 'raas_gen_username', text='')

        #     pkey_split = boxG.split(**factor(0.25), align=True)
        #     pkey_split.label(text='Public Key File:')
        #     user_box = pkey_split.row(align=True)
        #     user_box.prop(self, 'raas_gen_public_key_path', text='')

        #     pkey_split = boxG.split(**factor(0.25), align=True)
        #     pkey_split.label(text='Private Key File:')
        #     user_box = pkey_split.row(align=True)
        #     user_box.prop(self, 'raas_gen_private_key_path', text='')

        #     auth_split = boxG.split(**factor(0.25), align=True)
        #     auth_split.label(text='Key Passphrase:')
        #     user_box = auth_split.row(align=True)
        #     user_box.prop(self, 'raas_gen_password', text='')

        #     boxG.operator(RAAS_OT_generate_sshkey.bl_idname,
        #                     icon="CONSOLE")

        #     acc_split = boxG.split(**factor(0.25), align=True)
        #     acc_split.label(text='Account Type:')
        #     acc_box = acc_split.row(align=True)
        #     acc_box.prop(self, 'raas_account_type', text='')

        #     boxG.operator(RAAS_OT_upload_sshkey.bl_idname, icon="URL")

        #     # boxG = boxG.column()
        #     # boxG.label(
        #     #     text='Please wait a minute for the public key to install on all clusters before running Setup.')
        #     # boxG.operator(RAAS_OT_setup_sshkey.bl_idname, icon="COPY_ID")


def ctx_preferences():
    """Returns bpy.context.preferences in a 2.79-compatible way."""
    try:
        return bpy.context.preferences
    except AttributeError:
        return bpy.context.user_preferences


def preferences() -> RaasPreferences:
    return ctx_preferences().addons[ADDON_NAME].preferences


class RaasAuthValidate(async_loop.AsyncModalOperatorMixin, Operator):
    bl_idname = 'raas_auth.validate'
    bl_label = 'Validate'

    # def execute(self, context):
    async def async_execute(self, context):
        # from . import raas_pref

        addon_prefs = preferences()
        addon_prefs.reset_messages()

        try:
            resp = await raas_server.get_token(addon_prefs.raas_username, addon_prefs.raas_password)
        except:
            resp = None

        # resp = await raas_server.get_token(addon_prefs.raas_username, addon_prefs.raas_password)
        if resp and len(resp) == 36:
            addon_prefs.ok_message = 'Authentication token is valid.'
        else:
            addon_prefs.error_message = 'Authentication token is not valid!'

        # return {'FINISHED'}
        self.quit()


def register():
    """register."""

    bpy.utils.register_class(ClusterPresets)
    bpy.utils.register_class(RaasPreferences)
    bpy.utils.register_class(RaasAuthValidate)
    bpy.utils.register_class(RAAS_OT_install_dependencies)
    bpy.utils.register_class(RAAS_OT_update_dependencies)
    bpy.utils.register_class(RAAS_OT_generate_sshkey)
    bpy.utils.register_class(RAAS_OT_upload_sshkey)
    bpy.utils.register_class(RAAS_OT_NewClusterPreset)
    bpy.utils.register_class(RAAS_OT_RemoveClusterPreset)
    bpy.utils.register_class(RAAS_OT_find_working_dir)
    bpy.utils.register_class(RAAS_OT_test_connection)
    bpy.utils.register_class(RAAS_OT_install_scripts)
    # bpy.utils.register_class(RAAS_OT_install_blender)

    try:
        for dependency in python_dependencies:
            import_module(module_name=dependency.module,
                          global_name=dependency.name)

        # check_internal_addons()
        # check_external_addons()

        preferences().dependencies_installed = True
    except ModuleNotFoundError:
        preferences().dependencies_installed = False

    return


def unregister():
    """unregister."""

    bpy.utils.unregister_class(ClusterPresets)
    bpy.utils.unregister_class(RaasAuthValidate)
    bpy.utils.unregister_class(RaasPreferences)
    bpy.utils.unregister_class(RAAS_OT_install_dependencies)
    bpy.utils.unregister_class(RAAS_OT_update_dependencies)
    bpy.utils.unregister_class(RAAS_OT_generate_sshkey)
    bpy.utils.unregister_class(RAAS_OT_upload_sshkey)
    bpy.utils.unregister_class(RAAS_OT_NewClusterPreset)
    bpy.utils.unregister_class(RAAS_OT_RemoveClusterPreset)
    bpy.utils.unregister_class(RAAS_OT_find_working_dir)
    bpy.utils.unregister_class(RAAS_OT_test_connection)
    bpy.utils.unregister_class(RAAS_OT_install_scripts)
    # bpy.utils.unregister_class(RAAS_OT_install_blender)

    return
