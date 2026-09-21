import unreal,json
from pathlib import Path
root=Path(unreal.Paths.project_dir()).resolve()
if root.as_posix().lower()!='d:/fps3d/fpsgame':raise RuntimeError('Wrong project')
lib=unreal.MaterialEditingLibrary
m=unreal.load_asset('/Game/Vefects/Free_Fire/Shared/Materials/M_VFX_Erosion')
report={k:str(m.get_editor_property(k)) for k in ('blend_mode','shading_model','translucency_pass','output_translucent_velocity','disable_depth_test')}
report['dynamic']=[]
for n in lib.get_material_expressions(m):
    if isinstance(n,unreal.MaterialExpressionDynamicParameter):
        report['dynamic'].append({'names':[str(v) for v in n.get_editor_property('param_names')],'default':str(n.get_editor_property('default_value'))})
report['outputs']={str(prop):str(lib.get_material_property_input_node(m,prop)) for prop in (unreal.MaterialProperty.MP_EMISSIVE_COLOR,unreal.MaterialProperty.MP_OPACITY)}
(root/'SourceAssets/FireballTorchBurn20260921/material-contract.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
