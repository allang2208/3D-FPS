"""Read FBX source transforms for the invisible F6 dog diagnosis."""
import json
from pathlib import Path
from io_scene_fbx import parse_fbx

root = Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedDogMeshy20260924/CompletionV2')
result = {}
def clean(v):
    if isinstance(v, bytes): return v.decode('utf-8', errors='replace')
    if isinstance(v, (str, int, float)): return v
    return list(v)
for f in [root/'SK_InfectedDog_MeshyV2.fbx', root/'Animations/A_InfectedDogMeshy_Idle.fbx']:
    tree, version = parse_fbx.parse(str(f))
    d = {'version': version, 'models': []}; result[f.name] = d
    for e in tree.elems:
        if e.id == b'GlobalSettings':
            d['globals'] = [[clean(p) for p in prop.props] for el in e.elems if el.id == b'Properties70' for prop in el.elems]
        if e.id == b'Objects':
            for model in e.elems:
                if model.id != b'Model': continue
                name = clean(model.props[1])
                if not any(n in name for n in ['Armature', 'root', 'pelvis']): continue
                md = {'name': name, 'properties': []}; d['models'].append(md)
                for el in model.elems:
                    if el.id == b'Properties70':
                        md['properties'] = [[clean(p) for p in prop.props] for prop in el.elems]
out = Path('D:/FPS3D/FPSGAME/Saved/InfectedDogMeshy/FbxUnitsDiagnosis.json')
out.write_text(json.dumps(result, indent=2), encoding='utf-8')
print('FBX_DIAGNOSIS_SAVED', out)
