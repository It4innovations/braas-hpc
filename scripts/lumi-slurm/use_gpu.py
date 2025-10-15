import bpy

# force rendering to GPU
bpy.context.scene.cycles.device = 'GPU'
cpref = bpy.context.preferences.addons['cycles'].preferences
cpref.compute_device_type = 'HIP'
# Use GPU devices only
cpref.get_devices()
for device in cpref.devices:
    device.use = device.type == 'HIP'
    
    if device.use:
        print("Device used: ", device.name)
