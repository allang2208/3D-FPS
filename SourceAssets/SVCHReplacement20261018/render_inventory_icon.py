"""Produce the replacement's inventory PNG from the actual editable model."""
import bpy,math,shutil,hashlib,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;P=O.parents[1]
bpy.ops.wm.open_mainfile(filepath=str(O/'SVCH_Replacement_Editable.blend'),load_ui=False)
sc=bpy.context.scene;rig=bpy.data.objects['SK_M4_Infima'];rig.data.pose_position='REST'
gun=[o for o in sc.objects if o.type=='MESH' and o.name!='SVCH_BareArmsV9'];bpy.data.objects['SVCH_BareArmsV9'].hide_render=True
pts=[o.matrix_world@v.co for o in gun for v in o.data.vertices];lo=Vector([min(v[i] for v in pts) for i in range(3)]);hi=Vector([max(v[i] for v in pts) for i in range(3)]);center=(lo+hi)/2
cam=bpy.data.objects.new('InventoryCamera',bpy.data.cameras.new('InventoryCamera'));sc.collection.objects.link(cam);sc.camera=cam;cam.data.type='ORTHO';cam.location=center+Vector((-2.,-.06,.30));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=1.
sc.render.resolution_x=1536;sc.render.resolution_y=640;sc.render.resolution_percentage=100;bpy.context.view_layer.update();q=cam.matrix_world.inverted();local=[q@v for v in pts];vf=cam.data.view_frame(scene=sc);sx=max(abs(v.x) for v in vf);sy=max(abs(v.y) for v in vf);cam.data.ortho_scale=max(max(abs(v.x) for v in local)/sx,max(abs(v.y) for v in local)/sy)*1.08
world=bpy.data.worlds.new('InventoryStudio');world.use_nodes=True;world.node_tree.nodes.clear();bg=world.node_tree.nodes.new('ShaderNodeBackground');out=world.node_tree.nodes.new('ShaderNodeOutputWorld');world.node_tree.links.new(bg.outputs[0],out.inputs[0]);bg.inputs[0].default_value=(.28,.30,.34,1);bg.inputs[1].default_value=.5;sc.world=world
for name,offset,power,size in [('Key',(-.8,.1,1.0),110,1.1),('Fill',(-.4,-.9,.3),60,.9),('Edge',(.5,.3,.7),130,.8)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);sc.collection.objects.link(o);o.location=center+Vector(offset);o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
sc.render.engine='CYCLES';sc.cycles.samples=32;sc.cycles.use_denoising=True;sc.render.film_transparent=True;sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGBA';sc.render.filepath=str(O/'ue_svch.png');bpy.ops.render.render(write_still=True)
target=P/'Content/ColdSteelData/Icons/ue_svch.png';backup=O/'Before';backup.mkdir(exist_ok=True)
if target.exists():
 old=backup/('ue_svch_'+hashlib.sha256(target.read_bytes()).hexdigest()[:12]+'.png')
 if not old.exists():shutil.copy2(target,old)
shutil.copy2(O/'ue_svch.png',target)
(O/'icon_receipt.json').write_text(json.dumps({'saved':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'purpose':'production inventory icon','not_runtime_acceptance':True},indent=2));print('SVCH_INVENTORY_ICON_SAVED',flush=True)
