"""Keep editable source shading consistent with the new UE material graphs."""
import bpy
from pathlib import Path
O=Path(__file__).parent
bpy.context.preferences.filepaths.save_version=0
for file in O.glob('QBZ191_*Editable.blend'):
 bpy.ops.wm.open_mainfile(filepath=str(file));gun=bpy.data.objects['QBZ191_Export']
 for m in gun.data.materials:
  m.use_nodes=True;nodes=m.node_tree.nodes;links=m.node_tree.links;bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
  rough=next(n for n in nodes if n.type=='TEX_IMAGE' and n.image and 'Roughness' in n.image.name)
  mul=nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=.8;links.new(rough.outputs['Color'],mul.inputs[0])
  add=nodes.new('ShaderNodeMath');add.operation='ADD';add.inputs[1].default_value=.06;links.new(mul.outputs[0],add.inputs[0])
  lo=nodes.new('ShaderNodeMath');lo.operation='MAXIMUM';lo.inputs[1].default_value=.38 if 'Irons' in m.name else .28;links.new(add.outputs[0],lo.inputs[0])
  hi=nodes.new('ShaderNodeMath');hi.operation='MINIMUM';hi.inputs[1].default_value=.78;links.new(lo.outputs[0],hi.inputs[0]);links.new(hi.outputs[0],bs.inputs['Roughness'])
  for n in nodes:
   if n.type=='NORMAL_MAP':n.inputs['Strength'].default_value=.65 if 'Irons' in m.name else .85
 bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(file));print('QBZ_EDITABLE_MATERIAL_UPDATED',file.name,flush=True)
