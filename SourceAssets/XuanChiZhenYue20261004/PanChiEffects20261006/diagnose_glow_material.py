"""Compile only the reported guard material and record its render outputs."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
E=u.MaterialEditingLibrary
m=u.load_asset('/Game/Weapons/XuanChiZhenYue20261004/PanChiEffects20261006/M_PanChiGuardGlow')
out={'material':m.get_path_name(),'shader_errors':list(E.recompile_material(m)),'outputs':{}}
for key in ['MP_EMISSIVE_COLOR','MP_OPACITY','MP_FRONT_MATERIAL']:
    node=E.get_material_property_input_node(m,getattr(u.MaterialProperty,key))
    out['outputs'][key]={'node':node.get_class().get_name() if node else None,'inputs':[str(x) for x in E.get_material_expression_input_names(node)] if node else []}
out['scalar_parameters']=[str(n) for n in E.get_scalar_parameter_names(m)]
(P/'glow-material-diagnosis-20261007.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out))
