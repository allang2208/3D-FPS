"""Read the current graphs to author scoped material edits; no rendering or play."""
import json,os
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
paths={'shared':'/Game/Weapons/MeleeRunes20260915/SurfaceV2/M_SilverRuneSurfaceV2',
       'spirit':'/Game/Weapons/FrostSpiritBurst20260922/M_SilverRuneSurface_FrostSpirit',
       'gold':'/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922/M_AzureRunesword_NativeGold'}
result={}
for key,path in paths.items():
    mat=u.load_asset(path)
    if not mat:raise RuntimeError('Missing material '+path)
    nodes=[]
    for n in u.MaterialEditingLibrary.get_material_expressions(mat):
        if isinstance(n,u.MaterialExpressionCustom):
            row={'type':'custom','description':n.get_editor_property('description'),'code':n.get_editor_property('code'),
                 'inputs':[str(p.get_editor_property('input_name')) for p in n.get_editor_property('inputs')]}
            nodes.append(row)
        elif isinstance(n,(u.MaterialExpressionScalarParameter,u.MaterialExpressionVectorParameter)):
            value=n.get_editor_property('default_value')
            if isinstance(value,u.LinearColor):value=[value.r,value.g,value.b,value.a]
            nodes.append({'type':'parameter','name':str(n.get_editor_property('parameter_name')),'value':value})
    result[key]={'asset':path,'nodes':nodes}
(P/'material_sources.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('RUNE_FADE_AUTHORING_SOURCES '+json.dumps({k:len(v['nodes']) for k,v in result.items()}))
