import unreal as u,json
from pathlib import Path
out={};mel=u.MaterialEditingLibrary
for path in ['/Game/Monsters/WitchMeshy/OriginalRobeV05/Materials/M_Witch_V05_OriginalRobe','/Game/Monsters/WitchMeshy/Materials/M_Witch_Body']:
    m=u.load_asset(path);r={k:str(m.get_editor_property(k)) for k in ['two_sided','blend_mode','shading_model']}
    for p in [u.MaterialProperty.MP_BASE_COLOR,u.MaterialProperty.MP_NORMAL,u.MaterialProperty.MP_ROUGHNESS,u.MaterialProperty.MP_OPACITY_MASK,u.MaterialProperty.MP_WORLD_POSITION_OFFSET]:
        n=mel.get_material_property_input_node(m,p);r[str(p)]=str(n)
        if isinstance(n,u.MaterialExpressionTextureSample):r[str(p)+'_texture']=n.texture.get_path_name()
    out[path]=r
mesh=u.load_asset('/Game/Monsters/WitchRebuilt/SK_WitchRebuilt')
out['slots']=[{'name':str(s.get_editor_property('imported_material_slot_name')),'material':str(s.material_interface)} for s in mesh.materials]
Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921/Polish20260922/ue_material_inputs.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out))
