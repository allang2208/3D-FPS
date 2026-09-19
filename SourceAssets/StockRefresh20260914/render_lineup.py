"""Render a labelled overview of the same five meshes used for the shipped icons."""
import bpy,math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
entries=[('false','原厂枪托',(-2.5,0,1.1)),('skeleton','骨架枪托',(0,0,1.1)),('qr_performance','高性能后托',(2.5,0,1.1)),('core_stock','镂空轻型枪托',(-1.25,0,-1.1)),('tactical_telescopic','战术伸缩枪托',(1.25,0,-1.1))]
font=bpy.data.fonts.load('C:/Windows/Fonts/msyh.ttc')
labelmat=bpy.data.materials.new('Label');labelmat.use_nodes=True;n=labelmat.node_tree.nodes;l=labelmat.node_tree.links;n.clear();out=n.new('ShaderNodeOutputMaterial');em=n.new('ShaderNodeEmission');em.inputs[0].default_value=(.7,.75,.82,1);l.new(em.outputs[0],out.inputs[0])
for key,label,loc in entries:
 with bpy.data.libraries.load(str(P/'Icons'/('stock_'+key+'.blend')),link=False) as (source,dest):
  dest.objects=[name for name in source.objects if name.startswith('SM_') or name=='M4_Stock Classic Unreal_Export']
 for ob in dest.objects:
  if not ob or ob.type!='MESH':continue
  bpy.context.collection.objects.link(ob);ob.location+=Vector(loc);ob.hide_render=False;ob.hide_set(False)
 bpy.ops.object.text_add(location=(loc[0],-.15,loc[2]-.98),rotation=(math.pi/2,0,0));txt=bpy.context.object;txt.data.body=label;txt.data.font=font;txt.data.align_x='CENTER';txt.data.size=.155;txt.data.materials.append(labelmat)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.resolution_x=1800;scene.render.resolution_y=1050;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.world=bpy.data.worlds.new('LineupWorld');scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.025,.032,.042,1);bg.inputs[1].default_value=.7
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=.35
for loc,energy,size in [((-2,-5,5),1500,7),((3,2,4),1900,7),((-5,-2,-2),350,4),((0,-5,.2),180,6)]:
 bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=energy;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(0,-10,-.1));cam=bpy.context.object;cam.rotation_euler=(Vector((0,0,-.1))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=7.75;scene.camera=cam
scene.render.filepath=str(P/'stock_lineup.png');bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'stock_lineup.blend'));bpy.ops.render.render(write_still=True)
