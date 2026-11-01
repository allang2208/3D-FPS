"""Actual mesh/material render for formal modification icon production."""
import bpy,sys,json,math
from mathutils import Vector
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'LeiXiPommelV2_Editable.blend'))
sys.path.insert(0,'C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts')
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
o=bpy.data.objects['SM_ThunderGodHammer_pommel_lei_xi_v2'];apply_grayscale([o])
center=sum([Vector(v) for v in o.bound_box],Vector())/8
for v in o.data.vertices:v.co=(v.co-center)*18
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.resolution_x=1024;scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True
scene.use_nodes=False;scene.render.use_sequencer=False;scene.render.use_compositing=False
if hasattr(scene,'compositing_node_group'):scene.compositing_node_group=None
world=bpy.data.worlds.new('Neutral studio');scene.world=world;world.use_nodes=True
wn=world.node_tree.nodes;wl=world.node_tree.links;wn.clear();bg=wn.new('ShaderNodeBackground');wo=wn.new('ShaderNodeOutputWorld');wl.new(bg.outputs[0],wo.inputs[0]);bg.inputs[0].default_value=(.16,.16,.16,1);bg.inputs[1].default_value=.4
def aim(ob,point=(0,0,0)):ob.rotation_euler=(Vector(point)-ob.location).to_track_quat('-Z','Y').to_euler()
camdata=bpy.data.cameras.new('IconCamera');cam=bpy.data.objects.new('IconCamera',camdata);scene.collection.objects.link(cam);cam.location=(.9,-4,.35);aim(cam);camdata.type='ORTHO';camdata.ortho_scale=1.72;scene.camera=cam
for name,loc,power,size in [('Key',(-2,-3,4),500,3),('Fill',(3,-2,1),280,2),('Rim',(0,3,2),700,2)]:
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=loc;aim(ob)
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';neutral_output(scene)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'LeiXiPommel_IconAuthoring.blend'))
scene.render.filepath=str(P/'lei_xi_pommel_model_icon_source.png');bpy.ops.render.render(write_still=True)
print('LEIXI_ACTUAL_MODEL_ICON_SOURCE_RENDERED',flush=True)
