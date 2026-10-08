import json
from pathlib import Path
import unreal as u
E=u.MaterialEditingLibrary
m=u.load_asset('/Game/Weapons/XuanChiZhenYue20261004/PanChiEffects20261006/M_PanChiGuardGlow')
out={'material':m.get_path_name(),'expressions':[]}
for n in E.get_material_expressions(m):
    r={'type':n.get_class().get_name()}
    if isinstance(n,u.MaterialExpressionCustom):r['code']=n.get_editor_property('code')
    out['expressions'].append(r)
for key in ['MP_EMISSIVE_COLOR','MP_OPACITY','MP_FRONT_MATERIAL']:
    n=E.get_material_property_input_node(m,getattr(u.MaterialProperty,key));out[key]=n.get_class().get_name() if n else None
Path(__file__).with_name('saved-glow-graph-20261007.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out))
