"""Requested offline detail/assembly inspection of the exact exported V4 geometry."""
import bpy,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'ThorSeatsPrecisionV4.blend'))
rows=json.loads((P/'model_manifest.json').read_text(encoding='utf-8'))['parts']
parts=[bpy.data.objects[r['mesh']] for r in rows]
for o in bpy.context.scene.objects:
 if o.type=='MESH':o.hide_render=True;o.hide_set(False)
surface=parts[0].data.materials[0];ns=surface.node_tree.nodes;ls=surface.node_tree.links;ns.clear()
bs=ns.new('ShaderNodeBsdfPrincipled');out=ns.new('ShaderNodeOutputMaterial');ls.new(bs.outputs[0],out.inputs[0])
nodes={}
for name in ['BaseColor','MetallicRoughness','Normal']:
 n=ns.new('ShaderNodeTexImage');n.image=bpy.data.images.load(str(P.parent/'Textures'/(name+'.jpg')),check_existing=False);n.image.colorspace_settings.name='sRGB' if name=='BaseColor' else 'Non-Color';nodes[name]=n
ls.new(nodes['BaseColor'].outputs[0],bs.inputs['Base Color']);sep=ns.new('ShaderNodeSeparateColor');ls.new(nodes['MetallicRoughness'].outputs[0],sep.inputs[0]);ls.new(sep.outputs['Green'],bs.inputs['Roughness']);ls.new(sep.outputs['Blue'],bs.inputs['Metallic']);nm=ns.new('ShaderNodeNormalMap');ls.new(nodes['Normal'].outputs[0],nm.inputs['Color']);ls.new(nm.outputs[0],bs.inputs['Normal'])
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100;scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=0
scene.world=bpy.data.worlds.new('Precision inspection studio');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.12,.12,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.4
for o in parts:o.location=Vector((0,0,-.916));o.scale=(1,1,1)
bpy.ops.object.camera_add(location=(.075,-.42,.045));cam=bpy.context.object;cam.data.type='ORTHO';scene.camera=cam
for loc,power,size in [((-.22,-.3,.28),5,.3),((.2,-.22,.04),2.6,.2),((0,.15,.2),5,.2)]:
 bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=power;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(-o.location).to_track_quat('-Z','Y').to_euler()
for ob,row in zip(parts,rows):
 ob.hide_render=False
 for view,loc,target,scale in [('front',(.075,-.42,.045),(0,0,0),.191),('detail',(.17,-.32,.14),(.026,-.04,.038),.107)]:
  cam.location=Vector(loc);cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
  scene.render.filepath=str(P/'Preview'/(row['id']+'_'+view+'.png'));bpy.ops.render.render(write_still=True)
 ob.hide_render=True
# The two neighboring factory modules keep their actual pivots and mating faces.
with bpy.data.libraries.load(str(P.parent/'ModulesV1/ThunderGodHammer_Modular_Editable.blend'),link=False) as(a,b):b.objects=['SM_ThunderGodHammer_hammer_heads_factory','SM_ThunderGodHammer_neck_factory']
neighbors=[]
for o in b.objects:
 bpy.context.collection.objects.link(o);o.data.materials[0]=surface;o.location.z-=.916;o.hide_render=False;neighbors.append(o)
cam.location=(.13,-.42,.095);cam.rotation_euler=(Vector((0,0,-.012))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.38
for ob,row in zip(parts,rows):
 ob.hide_render=False;scene.render.filepath=str(P/'Preview'/(row['id']+'_assembled.png'));bpy.ops.render.render(write_still=True);ob.hide_render=True
print('DETAIL_AND_ASSEMBLY_VIEWS_COMPLETE',flush=True)
