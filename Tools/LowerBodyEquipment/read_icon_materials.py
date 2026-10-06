import json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/LowerBodyIcons20261004';R.mkdir(exist_ok=True)
result={}
for key in ['jeans','cargo','sneakers']:
    saved=json.loads((P/'SourceAssets/LowerBodyEquipment20261003/saved_assets.json').read_text())
    mesh=u.load_asset(saved[key+'_icon_mesh']);mat=mesh.static_materials[0].material_interface
    vectors={};scalars={};textures={}
    for n in u.MaterialEditingLibrary.get_vector_parameter_names(mat):
        v=u.MaterialEditingLibrary.get_material_instance_vector_parameter_value(mat,n)
        vectors[str(n)]=[v.r,v.g,v.b,v.a]
    for n in u.MaterialEditingLibrary.get_scalar_parameter_names(mat):scalars[str(n)]=u.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mat,n)
    for n in u.MaterialEditingLibrary.get_texture_parameter_names(mat):
        t=u.MaterialEditingLibrary.get_material_instance_texture_parameter_value(mat,n)
        textures[str(n)]=t.get_path_name() if t else None
    result[key]={'asset':mat.get_path_name(),'class':mat.get_class().get_name(),'vectors':vectors,'scalars':scalars,'textures':textures}
(R/'materials.json').write_text(json.dumps(result,indent=2))
print('LOWER_BODY_ICON_MATERIAL_INPUTS_SAVED')
