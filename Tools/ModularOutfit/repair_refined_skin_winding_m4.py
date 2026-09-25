"""Repair the V3 export convention, preserving geometry, UV placement and weights."""
import hashlib,json,shutil
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/RefinedSkinV3')
backup=root/'WindingRepair20260924';backup.mkdir(exist_ok=True)
paths=[root/'M4_original.json',root/'M4_bare_shape.json']
source,shape=[json.loads(p.read_text(encoding='utf8')) for p in paths]
if source.get('surface_winding')=='ue_native':
    print('V3_WINDING_ALREADY_REPAIRED')
else:
    before={}
    for p in paths:
        data=p.read_bytes();before[p.name]=hashlib.sha256(data).hexdigest()
        target=backup/p.name
        if not target.exists():shutil.copy2(p,target)
    if (root/'saved.json').exists() and not (backup/'saved-before.json').exists():
        shutil.copy2(root/'saved.json',backup/'saved-before.json')
    # Reverse corner-associated data together: physical UVs/normals stay put.
    for field in ('triangles','uv','normals'):source[field]=[list(reversed(face)) for face in source[field]]
    shape['normals']=[list(reversed(face)) for face in shape['normals']]
    source['surface_winding']=shape['surface_winding']='ue_native'
    shape['geometry_policy']['winding']='Native UE winding; no extra reversal after Blender outward orientation'
    for p,data in zip(paths,(source,shape)):
        p.write_text(json.dumps(data,separators=(',',':')),encoding='utf8')
    receipt={'before':before,'after':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
             'change':'Reverse triangle and matching UV/normal corner order only',
             'preserved':['positions','bone weights','reference skeleton','material ids','texture pixels','animation assets']}
    (backup/'repair.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
    print('V3_WINDING_REPAIRED',len(source['triangles']))
