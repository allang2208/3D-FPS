from pathlib import Path
import bpy
p=Path(__file__).resolve().parents[1]/'M249_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(p),use_scripts=False)
bpy.context.preferences.filepaths.save_version=0
for name in ('M249_HoloHousing','M249_OpticalHousing'):
    m=bpy.data.materials[name];nodes=m.node_tree.nodes
    color=next(n for n in nodes if n.type=='TEX_IMAGE' and n.image.name.startswith('T_M249_Color'))
    shader=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
    m.node_tree.links.new(color.outputs['Alpha'],shader.inputs['Alpha'])
    for link in list(shader.inputs['Emission Color'].links):m.node_tree.links.remove(link)
    shader.inputs['Emission Strength'].default_value=0
bpy.ops.wm.save_as_mainfile(filepath=str(p),compress=True)
