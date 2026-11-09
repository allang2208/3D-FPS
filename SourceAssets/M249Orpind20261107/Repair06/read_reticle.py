from pathlib import Path
import unreal as u,json
r=Path(__file__).resolve().parent
mesh=u.load_asset('/Game/Weapons/M249/SK_M249_V7')
mat=u.load_asset('/Game/Weapons/M249/Materials/M_M249_Reticle')
report={'material':mat.get_path_name(),'shader':str(mat.get_editor_property('shading_model')),'two_sided':mat.get_editor_property('two_sided'),'blend':str(mat.get_editor_property('blend_mode'))}
(r/'reticle_material.json').write_text(json.dumps(report,indent=2),encoding='utf8')
report['input']=str(u.MaterialEditingLibrary.get_material_property_input_node(mat,u.MaterialProperty.MP_EMISSIVE_COLOR))
if u.MaterialEditingLibrary.get_material_property_input_node(mat,u.MaterialProperty.MP_EMISSIVE_COLOR):
    report['color']=str(u.MaterialEditingLibrary.get_material_property_input_node(mat,u.MaterialProperty.MP_EMISSIVE_COLOR).get_editor_property('constant'))
(r/'reticle_material.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('M249_RETICLE_READ',report,flush=True)
