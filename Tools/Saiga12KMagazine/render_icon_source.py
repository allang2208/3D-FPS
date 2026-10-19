"""Produce the actual-model source for the required framed attachment icon."""
import bpy,math,json,sys
from pathlib import Path
from mathutils import Vector
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KMagazine20261017'
bpy.ops.wm.open_mainfile(filepath=str(O/'Authoring/Saiga12K_Ext12.blend'));scene=bpy.context.scene;ob=bpy.data.objects['Saiga12K_Ext12']
# These values come from the live gun's current polymer instance, not old source artwork.
f=json.loads((O/'Input/factory.json').read_text());v=f['material_vectors'];s=f['material_scalars'];m=ob.data.materials[0];nodes=m.node_tree.nodes;links=m.node_tree.links;bs=nodes.get('Principled BSDF')
bs.inputs['Base Color'].default_value=tuple(v.get('FinishColor',[.019,.019,.018,1]));bs.inputs['Roughness'].default_value=s.get('Roughness',.53);bs.inputs['Metallic'].default_value=s.get('Metallic',0.)
uv=nodes.new('ShaderNodeUVMap');uv.uv_map='UV1';tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(O/'Textures/T_Saiga12K_Ext12_Mask.png'));tex.image.colorspace_settings.name='Non-Color';links.new(uv.outputs['UV'],tex.inputs['Vector'])
split=nodes.new('ShaderNodeSeparateColor');links.new(tex.outputs['Color'],split.inputs['Color'])
ao=nodes.new('ShaderNodeMath');ao.operation='MULTIPLY_ADD';ao.inputs[1].default_value=.65;ao.inputs[2].default_value=.35;links.new(split.outputs['Blue'],ao.inputs[0])
mul=nodes.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1.;mul.inputs[1].default_value=bs.inputs['Base Color'].default_value;links.new(ao.outputs[0],mul.inputs[2]);links.new(mul.outputs[0],bs.inputs['Base Color'])
noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=50.;bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.004;links.new(noise.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],bs.inputs['Normal'])
sys.path.insert(0,'C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts');import apply_modification_icon_grayscale as grey;grey.apply_grayscale([ob]);grey.neutral_output(scene)
coords=[ob.matrix_world@Vector(p) for p in ob.bound_box];centre=sum(coords,Vector())/8;span=max(max(v.z for v in coords)-min(v.z for v in coords),max(v.y for v in coords)-min(v.y for v in coords))
camdata=bpy.data.cameras.new('ActualInstalledSide');cam=bpy.data.objects.new('ActualInstalledSide',camdata);scene.collection.objects.link(cam);cam.location=centre+Vector((80,0,0));cam.rotation_euler=(centre-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=span*1.22;scene.camera=cam
def light(name,offset,energy,size):
 d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=centre+Vector(offset);o.rotation_euler=(centre-o.location).to_track_quat('-Z','Y').to_euler()
light('Key',(35,-25,35),40000,35);light('Fill',(25,30,10),20000,25);light('Edge',(-10,-12,25),30000,22)
scene.world=bpy.data.worlds.new('NeutralStudio');scene.world.use_nodes=True;bg=scene.world.node_tree.nodes.new('ShaderNodeBackground');out=scene.world.node_tree.nodes.new('ShaderNodeOutputWorld');scene.world.node_tree.links.new(bg.outputs[0],out.inputs['Surface']);bg.inputs[0].default_value=(.18,.18,.18,1);bg.inputs[1].default_value=.3
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.render.resolution_x=1024;scene.render.resolution_y=1024;scene.render.resolution_percentage=100;scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.filepath=str(O/'Icons/saiga12k_ext12_source.png');scene.view_settings.view_transform='AgX'
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Icons/Saiga12K_Ext12_Icon.blend'),compress=True);bpy.ops.render.render(write_still=True)
(O/'Icons/source.json').write_text(json.dumps({'mesh':'Authoring/Saiga12K_Ext12.blend','forward':'UE +Y / image left','up':'UE +Z / image up','camera':'horizontal orthographic +X','source':'current actual magazine mesh with WS1.1 effective polymer finish and own UV1 mask','purpose':'production attachment icon, not runtime acceptance'},indent=2),encoding='utf-8')
