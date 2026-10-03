import json
from pathlib import Path
import unreal as u
lib=u.MaterialEditingLibrary
data={}
for name in ['MI_FaceDown','MI_Face_Skin_Baked_LOD0','MI_Body_Baked']:
    mat=u.load_asset('/Game/AsianMale_Jason/Material/'+name)
    values={}
    for kind in ['static_switch','scalar','vector','texture']:
        names=getattr(lib,'get_'+kind+'_parameter_names')(mat)
        fn=getattr(lib,'get_material_instance_'+kind+'_parameter_value')
        values[kind]={str(n):str(fn(mat,n)) for n in names}
    values['overrides']=mat.get_editor_property('base_property_overrides').export_text()
    data[name]=values
Path('D:/FPS3D/FPSGAME/SourceAssets/JasonFaceRepair20261003/shader_inputs.json').write_text(json.dumps(data,indent=2))
print('JASON_SKIN_SHADER_INPUTS_SAVED')
