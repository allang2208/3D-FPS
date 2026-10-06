"""Render the actual new model as a production UI icon source, not a test preview."""
import bpy
import sys
from pathlib import Path
from mathutils import Vector

O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'RSH12_MuzzleBrake_Editable.blend'))
scene=bpy.context.scene
model=bpy.data.objects['SM_RSH12_MuzzleBrake']
for c in bpy.data.collections:c.hide_render=c.name!='GAME_Export'
for ob in scene.objects:
    if ob.type=='MESH':ob.hide_render=ob!=model
model.hide_set(False)
sys.path.insert(0,'C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts')
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
apply_grayscale([model]);neutral_output(scene)
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.render.film_transparent=True
points=[model.matrix_world@Vector(c) for c in model.bound_box]
lo=Vector(tuple(min(v[i] for v in points) for i in range(3)))
hi=Vector(tuple(max(v[i] for v in points) for i in range(3)))
center=(lo+hi)*.5;span=max(hi-lo)
data=bpy.data.cameras.new('Brake_IconCamera');cam=bpy.data.objects.new(data.name,data)
scene.collection.objects.link(cam);data.type='ORTHO';data.ortho_scale=span*1.35;data.clip_start=.001
# Forward (+X) projects left; small front-side yaw reveals the actual front recess.
cam.location=center+Vector((.35,1.,0.)).normalized()*span*3
cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();scene.camera=cam
scene.world=bpy.data.worlds.new('Brake_IconWorld');scene.world.use_nodes=True
scene.world.node_tree.nodes.clear()
bg=scene.world.node_tree.nodes.new('ShaderNodeBackground');bg.inputs['Strength'].default_value=.25
out=scene.world.node_tree.nodes.new('ShaderNodeOutputWorld')
scene.world.node_tree.links.new(bg.outputs['Background'],out.inputs['Surface'])
for i,(offset,power) in enumerate([((.12,.13,.19),1.),((-.1,.18,.05),.65),((.04,-.15,.1),.85)]):
    light=bpy.data.lights.new('Brake_IconLight'+str(i),'AREA');light.energy=power;light.size=.14
    obj=bpy.data.objects.new(light.name,light);scene.collection.objects.link(obj)
    obj.location=center+Vector(offset);obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(O/'MuzzleBrake_IconSource.png')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'RSH12_MuzzleBrake_Icon.blend'))
bpy.ops.render.render(write_still=True)
print('RSH_BRAKE_ICON_SOURCE_SAVED',flush=True)
