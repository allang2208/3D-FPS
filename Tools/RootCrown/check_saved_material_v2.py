"""Requested material check: reload the saved BP/material in a fresh SM6 process."""
import unreal as u,json
from pathlib import Path
D='/Game/Monsters/RootCrown';ME=u.MaterialEditingLibrary
bp=u.load_asset(D+'/BP_RootCrownRigPreview');cdo=u.get_default_object(bp.generated_class())
mat=cdo.get_editor_property('slash_material');component=cdo.get_editor_property('mesh')
if component.get_material(0)!=mat:raise RuntimeError('Saved Blueprint material override differs from SlashMaterial')
nodes={};pending=[ME.get_material_property_input_node(mat,p) for p in (u.MaterialProperty.MP_FRONT_MATERIAL,u.MaterialProperty.MP_BASE_COLOR)]
while pending:
    node=pending.pop()
    if not node or node.get_path_name() in nodes:continue
    nodes[node.get_path_name()]=node;pending.extend(c for c in ME.get_inputs_for_material_expression(mat,node) if c)
mask=next(n for n in nodes.values() if isinstance(n,u.MaterialExpressionCustom) and 'smoothstep(56.0' in n.get_editor_property('code'))
if not any(isinstance(n,u.MaterialExpressionVertexInterpolator) for n in ME.get_inputs_for_material_expression(mat,mask) if n):raise RuntimeError('Saved crown mask bypasses vertex interpolation')
stats=ME.get_statistics(mat)
pixel=stats.get_editor_property('num_pixel_shader_instructions')
if pixel<=0:raise RuntimeError('Saved material has no compiled pixel shader')
textures=[t.get_path_name() for t in ME.get_material_used_textures(mat)]
for role in ('BaseColor','Normal','MetallicRoughness'):
    if not any('T_RootCrown_'+role+'.' in path for path in textures):raise RuntimeError('Missing texture '+role)
report={'passed':True,'scope':'saved Root Crown material reload and SM6 shader compilation only','material':mat.get_path_name(),'blueprint':bp.get_path_name(),'vertex_interpolator_connected':True,'pixel_instructions':pixel,'vertex_instructions':stats.get_editor_property('num_vertex_shader_instructions'),'textures':textures,'gameplay_run':False}
Path('D:/FPS3D/FPSGAME/SourceAssets/RootCrown20261014/Reports/material_v2_saved_check.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('ROOT_CROWN_SAVED_MATERIAL_CHECK '+json.dumps(report))
