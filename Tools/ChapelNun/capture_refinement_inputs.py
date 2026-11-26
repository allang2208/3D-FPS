"""Read current native hair settings and the actual nun boot/collar geometry."""
from pathlib import Path
code=Path('D:/FPS3D/FPSGAME/Tools/ChapelNun/capture_sources.py').read_text(encoding='utf-8-sig')
exec(compile(code.split("head=capture(")[0],'<nun capture helpers>','exec'))
R=P/'SourceAssets/ChapelNun20261115/RefinementR4';(R/'Inputs').mkdir(parents=True,exist_ok=True)
capture('current_boots','/Game/Characters/ChapelNun20261115/Meshes/SK_Nun_Boots')
capture('current_trim','/Game/Characters/ChapelNun20261115/Meshes/SK_Nun_CollarCross')
haircfg=cfg['heads'][cfg['default_head']]['hair_styles']['long_straight']['grooms'][0]
asset=u.load_asset(haircfg['asset']);mat=u.load_asset(haircfg['materials'][0]);L=u.MaterialEditingLibrary
out={'config':haircfg,'material':mat.get_path_name(),'parent':str(mat.parent),'scalars':{},'vectors':{},'switches':{},'settings':{}}
for field in ('hair_groups_rendering','hair_groups_physics','hair_groups_interpolation','hair_groups_lod','hair_groups_materials'):
 out['settings'][field]=[x.export_text() for x in asset.get_editor_property(field)]
for name in L.get_scalar_parameter_names(mat):out['scalars'][str(name)]=L.get_material_instance_scalar_parameter_value(mat,name)
for name in L.get_vector_parameter_names(mat):
 c=L.get_material_instance_vector_parameter_value(mat,name);out['vectors'][str(name)]=[c.r,c.g,c.b,c.a]
for name in L.get_static_switch_parameter_names(mat):out['switches'][str(name)]=L.get_material_instance_static_switch_parameter_value(mat,name)
(R/'Inputs/native_hair_settings.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('REFINEMENT_INPUTS_SAVED',flush=True)
