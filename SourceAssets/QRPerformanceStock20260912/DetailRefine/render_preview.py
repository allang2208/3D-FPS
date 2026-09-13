"""User-requested close previews of the actual refined game model."""
import bpy,math
from pathlib import Path
from mathutils import Vector
R=Path(__file__).parent;out=R/'Preview20260913';out.mkdir(exist_ok=True)

def point_at(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
def area(name,location,power,size,target):
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
 o=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(o);o.location=location;point_at(o,target)

for key in ['M4','AKM']:
 bpy.ops.wm.open_mainfile(filepath=str(R/key/'QRStock_Refined_Editable.blend'))
 model=bpy.data.objects['SM_QRPerformanceStock_Refined']
 for o in bpy.context.scene.objects:
  if o!=model:o.hide_render=True
 model.hide_render=False;model.hide_set(False)
 scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True;scene.cycles.device='CPU'
 scene.render.threads_mode='FIXED';scene.render.threads=8;scene.render.resolution_x=1400;scene.render.resolution_y=1050;scene.render.resolution_percentage=100
 scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False;scene.view_settings.view_transform='AgX';scene.view_settings.exposure=.5
 scene.world=bpy.data.worlds.new('Neutral_studio');scene.world.use_nodes=True
 nodes=scene.world.node_tree.nodes;nodes.clear();bg=nodes.new('ShaderNodeBackground');world_out=nodes.new('ShaderNodeOutputWorld');scene.world.node_tree.links.new(bg.outputs['Background'],world_out.inputs['Surface']);bg.inputs['Color'].default_value=(.20,.23,.27,1);bg.inputs['Strength'].default_value=.65
 target=(9,0,-4.25)
 area('Large_softbox',(-6,-19,24),33000,17,target)
 area('Side_fill',(25,-12,9),13000,14,target)
 area('Edge_strip',(10,15,18),30000,11,target)
 data=bpy.data.cameras.new('Preview');camera=bpy.data.objects.new('Preview',data);bpy.context.collection.objects.link(camera);data.type='ORTHO';data.ortho_scale=24.7
 camera.location=(-6,-36,10);point_at(camera,target);scene.camera=camera
 scene.render.filepath=str(out/(key+'_QR_Refined_Close.png'));bpy.ops.render.render(write_still=True)
 print('PREVIEW_RENDERED',scene.render.filepath,flush=True)
