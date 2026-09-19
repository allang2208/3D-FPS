"""Bake the receiver's authored coating onto independent attachment UV1 atlases."""
import bpy,json,math,ast,textwrap
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;S=O.parent.parent;T=O/'Textures';T.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.read_factory_settings(use_empty=True)
source=ast.parse((S/'QBZ191Hero20260913/build.py').read_text())
function=next(x for x in source.body if isinstance(x,ast.FunctionDef) and x.name=='material')
exec(compile(ast.Module(body=[function],type_ignores=[]),'receiver_material_source','exec'))
mat=material('AUTH_QBZ191_ReceiverCoating',(.025,.029,.033),.72,.30)
mat.use_fake_user=True
n=mat.node_tree.nodes;l=mat.node_tree.links
bs=next(x for x in n if x.type=='BSDF_PRINCIPLED');out=next(x for x in n if x.type=='OUTPUT_MATERIAL')
# The source rifle atlas contains engravings at rifle-specific UV coordinates.
# Its procedural coating is reused; those unrelated UV markings are excluded.
for tex in list(n):
 if tex.type=='TEX_IMAGE' and tex.label=='Original colour and markings reference':
  for link in list(tex.outputs['Color'].links):
   if link.to_node.type=='MIX_RGB':link.to_node.inputs[0].default_value=0.
base=bs.inputs['Base Color'].links[0].from_socket;rough=bs.inputs['Roughness'].links[0].from_socket;normal=bs.inputs['Normal'].links[0].from_socket
metal_node=n.new('ShaderNodeValue');metal_node.outputs[0].default_value=.72;metal=metal_node.outputs[0];group='Body'
wear=(S/'QBZ191ContactWear20260913/wear.py').read_text()
exec(textwrap.dedent(wear[wear.index(' def mathnode'):wear.index(' emit=n.new')]))
base=bs.inputs['Base Color'].links[0].from_socket;rough=bs.inputs['Roughness'].links[0].from_socket;metal=bs.inputs['Metallic'].links[0].from_socket
def mathnode(op,a,b):
 x=n.new('ShaderNodeMath');x.operation=op
 for i,v in enumerate([a,b]):
  if isinstance(v,(int,float)):x.inputs[i].default_value=v
  else:l.new(v,x.inputs[i])
 return x.outputs[0]
# Apply the same final finish used on the currently installed receiver.
blend=n.new('ShaderNodeMixRGB');blend.inputs[0].default_value=.32;blend.inputs[2].default_value=(.025,.029,.032,1);l.new(base,blend.inputs[1]);base=blend.outputs[0]
rough=mathnode('ADD',mathnode('MULTIPLY',rough,.62),.42*.38)
l.new(base,bs.inputs['Base Color']);l.new(rough,bs.inputs['Roughness'])
orm=n.new('ShaderNodeCombineColor');orm.inputs[0].default_value=1;l.new(rough,orm.inputs[1]);l.new(metal,orm.inputs[2])
emit=n.new('ShaderNodeEmission');target=n.new('ShaderNodeTexImage');n.active=target
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=8;s.render.bake.use_selected_to_active=False;s.render.bake.use_clear=True;s.render.bake.margin=12
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type=='OPTIX'
if any(d.use for d in prefs.devices):s.cycles.device='GPU'

bpy.ops.mesh.primitive_plane_add(size=.1)
ob=bpy.context.object;ob.data.materials.append(mat)
for kind,socket in [('BaseColor',base),('ORM',orm.outputs[0])]:
 im=bpy.data.images.new('T_QBZ191_StableCollar_'+kind,width=1024,height=1024,alpha=False)
 im.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color';target.image=im
 l.new(socket,emit.inputs['Color']);l.new(emit.outputs[0],out.inputs['Surface'])
 bpy.ops.object.bake(type='EMIT');im.filepath_raw=str(T/(im.name+'.png'));im.file_format='PNG';im.save()
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'QBZ_CollarCoating_Editable.blend'))
