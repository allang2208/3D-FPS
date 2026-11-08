"""Render the actual grayscale component reference for the approved IconV2."""
import bpy,math,sys,importlib.util,json
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P))
import solid_surface_tools as m
bpy.ops.wm.open_mainfile(filepath=str(P/'ConicalHammerSeats_Editable.blend'))
obj=bpy.data.objects['SM_SteelWarhammer_ConicalSeat_V1']
for other in list(bpy.context.scene.objects):
    if other!=obj:bpy.data.objects.remove(other,do_unlink=True)
obj.hide_set(False);obj.hide_render=False
helper=Path('C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py')
spec=importlib.util.spec_from_file_location('icon_gray',helper);gray=importlib.util.module_from_spec(spec);spec.loader.exec_module(gray)
gray.apply_grayscale([obj]);scene=bpy.context.scene;gray.neutral_output(scene)
# Model-space +Z is the thrust direction. Show it pointing left, camera level.
R=Matrix.Rotation(math.radians(12),4,'Z')@Matrix.Rotation(-math.pi/2,4,'Y')
points=[R@Vector(c) for c in obj.bound_box]
lo=Vector(tuple(min(p[i] for p in points) for i in range(3)));hi=Vector(tuple(max(p[i] for p in points) for i in range(3)))
center=(lo+hi)*.5;scale=1.42/(hi.x-lo.x)
obj.matrix_world=Matrix.Translation(Vector((0,-.30,0)))@Matrix.Scale(scale,4)@Matrix.Translation(-center)@R
scene.render.engine='CYCLES';scene.cycles.samples=64;scene.render.threads_mode='FIXED';scene.render.threads=10
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='CUDA';prefs.get_devices()
    for d in prefs.devices:d.use=d.type=='CUDA'
    scene.cycles.device='GPU'
except Exception:pass
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.16,.16,.16,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.35
bpy.ops.object.camera_add(location=(0,-6,0));cam=bpy.context.object;cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='ORTHO';cam.data.ortho_scale=2.06;scene.camera=cam
for loc,power,size in [((-2,-3,3),650,3),((2,-2,1),350,2),((0,.5,2),450,2)]:
    bpy.ops.object.light_add(type='AREA',location=loc);lamp=bpy.context.object;lamp.data.energy=power;lamp.data.size=size
    lamp.rotation_euler=(Vector((0,0,0))-lamp.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(P/'Icons/conical_seat_actual_gray.png');bpy.ops.render.render(write_still=True)
print('CONICAL_SEAT_GRAY_REFERENCE_SAVED',flush=True)
