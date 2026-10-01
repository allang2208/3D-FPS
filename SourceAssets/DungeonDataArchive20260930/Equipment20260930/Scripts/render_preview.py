"""User-requested previews of the actual Blender geometry and packed PBR atlas."""
import math,json
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authored/ArchiveEquipment_Editable.blend'))
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=True
try:
 p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
 for d in p.devices:d.use=d.type=='OPTIX'
 s.cycles.device='GPU'
except Exception:s.cycles.device='CPU'
s.render.resolution_x=1400;s.render.resolution_y=1400;s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';s.view_settings.exposure=-.25
world=bpy.data.worlds.new('Reference studio');s.world=world;world.use_nodes=True
bg=world.node_tree.nodes.new('ShaderNodeBackground');wo=world.node_tree.nodes.new('ShaderNodeOutputWorld');world.node_tree.links.new(bg.outputs[0],wo.inputs[0]);bg.inputs[0].default_value=(.64,.66,.68,1);bg.inputs[1].default_value=.30
def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
for name,loc,power,size in [('Key',(-3.5,-4.5,6),1050,4.0),('Fill',(4,-1,3.6),600,3.5),('Rim',(0,4,4.6),1050,3.0)]:
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;o=bpy.data.objects.new(name,data);s.collection.objects.link(o);o.location=loc;aim(o,(0,0,1))
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.012));floor=bpy.context.object
m=bpy.data.materials.new('Studio floor');m.diffuse_color=(.28,.29,.28,1);m.use_nodes=True
bs=m.node_tree.nodes.new('ShaderNodeBsdfPrincipled');mo=m.node_tree.nodes.new('ShaderNodeOutputMaterial');m.node_tree.links.new(bs.outputs[0],mo.inputs[0]);bs.inputs['Base Color'].default_value=(.28,.29,.28,1);bs.inputs['Roughness'].default_value=.83;floor.data.materials.append(m)
data=bpy.data.cameras.new('Preview Camera');camera=bpy.data.objects.new('Preview Camera',data);s.collection.objects.link(camera);s.camera=camera;data.type='ORTHO';data.lens=62
models=list(bpy.data.collections['GAME_EXPORTS'].objects)
for o in models:o.hide_render=True
outputs=[]
for o in models:
 o.location=(0,0,0);o.hide_render=False
 is_console='Console' in o.name;target=(0,0,.75 if is_console else 1.07)
 camera.location=(-4.5,-6.4,3.05 if is_console else 3.15);aim(camera,target);data.ortho_scale=3.5 if is_console else 2.90
 s.render.filepath=str(ROOT/'Previews'/(o.name+'_Blender.png'));bpy.ops.render.render(write_still=True);outputs.append(s.render.filepath);o.hide_render=True
(ROOT/'Receipts/previews.json').write_text(json.dumps(dict(kind='actual Blender model render',images=outputs,render_engine='Cycles',samples=48,user_requested=True,unreal_preview=False),indent=2),encoding='utf-8')
print('ARCHIVE_MODEL_PREVIEWS_SAVED',len(outputs),flush=True)
