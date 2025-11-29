# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

# (c) IT4Innovations, VSB-TUO

bl_info = {
    "name" : "BRaaS-HPC",
    "author" : "Milan Jaros, Petr Strakos, Marta Jaros, Lubomir Riha",
    "description" : "Rendering-as-a-service for Blender on HPC",
    "blender" : (4, 0, 0),
    "version" : (4, 5, 5),
    "location" : "Addon Preferences panel",
    "wiki_url" : "https://github.com/It4innovations/braas-hpc/",
    "category" : "System",
}

import logging

log = logging.getLogger(__name__)

def register():
    """Late-loads and registers the Blender-dependent submodules."""

    from . import async_loop
    from . import raas_pref
    from . import raas_render

    async_loop.setup_asyncio_executor()
    async_loop.register()

    raas_pref.register()
    raas_render.register()    

def unregister():
    """unregister."""

    from . import async_loop
    from . import raas_pref
    from . import raas_render
    
    try:
        async_loop.unregister()
        raas_pref.unregister()
        raas_render.unregister() 
    except RuntimeError:
        pass

