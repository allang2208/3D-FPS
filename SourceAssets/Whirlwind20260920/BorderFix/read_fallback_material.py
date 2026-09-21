import json
from pathlib import Path
import unreal as u
P=Path(__file__).parent
rows=[]
for path in ['/Engine/EngineMaterials/DefaultPostProcessMaterial','/Game/Skills/Whirlwind20260920/M_WhirlwindFocus']:
    m=u.load_asset(path)
    item={'path':path,'domain':str(m.get_editor_property('material_domain')),'expressions':[]}
    for e in u.MaterialEditingLibrary.get_material_expressions(m):
        info={'class':e.get_class().get_name(),'name':e.get_name()}
        if isinstance(e,u.MaterialExpressionCustom):info['code']=e.get_editor_property('code')
        if isinstance(e,u.MaterialExpressionConstant3Vector):info['color']=str(e.get_editor_property('constant'))
        if isinstance(e,u.MaterialExpressionVectorParameter):
            info['parameter']=str(e.get_editor_property('parameter_name'));info['color']=str(e.get_editor_property('default_value'))
        if isinstance(e,u.MaterialExpressionTextureSample):
            texture=e.get_editor_property('texture');info['texture']=texture.get_path_name() if texture else None
        item['expressions'].append(info)
    rows.append(item)
(P/'fallback-material-source.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print(json.dumps(rows))
