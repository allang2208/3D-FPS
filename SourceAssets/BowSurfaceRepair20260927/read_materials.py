"""Read the actual bow material modes and import settings without changing assets."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).parent;ROOT=P.parents[1]
bow=json.loads((ROOT/'Content/ColdSteelData/bows.json').read_text(encoding='utf8'))['bow_dark']
catalog=json.loads((ROOT/'Content/ColdSteelData/bow-gunsmith.json').read_text(encoding='utf8'))
paths=set(v for k,v in bow.items() if k.startswith('bow_part_') and k.endswith('_mesh') and v)
for col in catalog['columns']:
    for vis in [col['factory_visual']]+[o['visual'] for o in col['options']]:
        paths.update(v for k,v in vis.items() if k.endswith('_mesh') and v)
result=[]
for path in sorted(paths):
    asset=u.load_asset(path)
    if not asset:continue
    slots=asset.materials if isinstance(asset,u.SkeletalMesh) else asset.static_materials
    row={'asset':path,'materials':[]}
    for s in slots:
        m=s.material_interface
        if not m:continue
        while isinstance(m,u.MaterialInstanceConstant):m=m.parent
        row['materials'].append({'path':m.get_path_name(),'two_sided':m.get_editor_property('two_sided'),
            'blend':str(m.get_editor_property('blend_mode'))})
    result.append(row)
(P/'ue-materials.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print('BOW_MATERIAL_DIAGNOSIS',json.dumps(result))
