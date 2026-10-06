"""Render the actual accessory as production UI source, not an acceptance view."""
import bpy,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'RSH12_HeavySuppressor_Editable.blend'))
sys.path.insert(0,'C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts')
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
obj=bpy.data.objects['SM_RSH12_HeavySuppressor']
apply_grayscale([obj]);scene=bpy.context.scene;neutral_output(scene)
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
world=bpy.data.worlds.new('ProductionIconWorld');world.use_nodes=True
background=world.node_tree.nodes.new('ShaderNodeBackground');world_output=world.node_tree.nodes.new('ShaderNodeOutputWorld')
world.node_tree.links.new(background.outputs['Background'],world_output.inputs['Surface'])
background.inputs['Color'].default_value=(.12,.12,.12,1)
background.inputs['Strength'].default_value=.35;scene.world=world
target=Vector((.09,0,0));data=bpy.data.cameras.new('ProductionIconCamera');cam=bpy.data.objects.new(data.name,data);scene.collection.objects.link(cam)
cam.location=target+Vector((0,.6,0));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
data.type='ORTHO';data.ortho_scale=.18/.79;data.clip_start=.001;scene.camera=cam
for i,(location,energy,size) in enumerate([((.10,.22,.23),10,.25),((0,-.15,.10),7,.18),((.23,.10,-.08),4,.16)]):
    light=bpy.data.lights.new('IconArea'+str(i),'AREA');light.energy=energy;light.shape='DISK';light.size=size
    lo=bpy.data.objects.new(light.name,light);scene.collection.objects.link(lo);lo.location=location;lo.rotation_euler=(target-lo.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(O/'IconModel.png')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'RSH12_HeavySuppressor_Icon.blend'))
bpy.ops.render.render(write_still=True)
print('RSH_SUPPRESSOR_ICON_SOURCE_SAVED',scene.render.filepath,flush=True)
