import bpy,json,ast,math,textwrap
from pathlib import Path
O=Path(__file__).parent;S=O.parent
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(O/'QBZ191_ReceiverCoating_Editable.blend'))
code=(O/'bake_coating.py').read_text();exec(code[code.index('source=ast.parse'):code.index("s=bpy.context.scene;s.render.engine")])
manifest=json.loads((O/'coating.json').read_text());installed=json.loads((O/'import.json').read_text())
for key,info in manifest.items():
 ob=bpy.data.objects['SM_QBZ191_'+key]
 for idx,slot in enumerate(info['slots']):
  if slot['slot'] not in installed[key]['coated_slots']:continue
  m=ob.data.materials[idx].copy();m.name='M_QBZ191_Receiver_'+key+'_'+str(idx);m.use_nodes=True;nodes=m.node_tree.nodes;links=m.node_tree.links
  shader=next(x for x in nodes if x.type=='BSDF_PRINCIPLED');uv=nodes.new('ShaderNodeUVMap');uv.uv_map='QBZCoatingUV'
  for kind,path in info['textures'].items():
   image=bpy.data.images.load(path,check_existing=True);image.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color'
   tex=nodes.new('ShaderNodeTexImage');tex.image=image;links.new(uv.outputs[0],tex.inputs['Vector'])
   if kind=='BaseColor':links.new(tex.outputs[0],shader.inputs['Base Color'])
   else:
    sep=nodes.new('ShaderNodeSeparateColor');links.new(tex.outputs[0],sep.inputs[0]);links.new(sep.outputs[1],shader.inputs['Roughness']);links.new(sep.outputs[2],shader.inputs['Metallic'])
  ob.data.materials[idx]=m
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'QBZ191_ReceiverCoating_Editable.blend'));print('QBZ_COATING_EDITABLE_SAVED')
