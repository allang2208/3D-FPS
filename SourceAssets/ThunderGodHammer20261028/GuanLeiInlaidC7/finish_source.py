"""Bind final dedicated PBR atlases and pack editable project."""
import bpy,json
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'GuanLei_InlaidC7_Editable.blend'));bpy.context.preferences.filepaths.save_version=0
manifest=json.loads((P/'model_manifest.json').read_text(encoding='utf-8'))
for row in manifest['parts']:
 mat=bpy.data.materials[row['material']];mat.use_nodes=True;ns=mat.node_tree.nodes;ls=mat.node_tree.links;ns.clear()
 bs=ns.new('ShaderNodeBsdfPrincipled');out=ns.new('ShaderNodeOutputMaterial');ls.new(bs.outputs[0],out.inputs['Surface']);nodes={}
 for k,rel in row['textures'].items():
  im=bpy.data.images.load(str(P/rel),check_existing=True);im.colorspace_settings.name='sRGB' if k=='BaseColor' else 'Non-Color'
  tex=ns.new('ShaderNodeTexImage');tex.image=im;nodes[k]=tex
 ls.new(nodes['BaseColor'].outputs[0],bs.inputs['Base Color']);sep=ns.new('ShaderNodeSeparateColor');ls.new(nodes['ORM'].outputs[0],sep.inputs[0]);ls.new(sep.outputs['Green'],bs.inputs['Roughness']);ls.new(sep.outputs['Blue'],bs.inputs['Metallic'])
 nm=ns.new('ShaderNodeNormalMap');ls.new(nodes['Normal'].outputs[0],nm.inputs['Color']);ls.new(nm.outputs[0],bs.inputs['Normal'])
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'GuanLei_InlaidC7_Editable.blend'))
print('GUANLEI_C7_SOURCE_PACKED',flush=True)
