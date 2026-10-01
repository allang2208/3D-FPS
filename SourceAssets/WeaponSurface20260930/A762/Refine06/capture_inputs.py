"""Read current A762 material inputs for production; no asset mutations or tests."""
import hashlib
import json
from pathlib import Path
import unreal as u

O = Path(__file__).parent
P = Path(u.Paths.project_dir()).resolve()
L = u.MaterialEditingLibrary
if P != Path('D:/FPS3D/FPSGAME').resolve():
    raise RuntimeError('Wrong project')
OUT = O / 'Input'
OUT.mkdir(parents=True, exist_ok=True)
if (OUT / 'current.json').exists():
    raise RuntimeError('Production input already captured; preserve its baseline')
plan = json.loads((O.parent / 'slot_plan.json').read_text(encoding='utf-8'))
accessories = json.loads((O.parent / 'Bake/accessory_plan.json').read_text(encoding='utf-8'))
meshes = {'A762': '/Game/Weapons/A762/Integrated20260920/SK_A762_Manny'}
meshes.update({k: v['path'] for k, v in plan['static'].items()})
meshes.update({k: v['path'] for k, v in accessories.items()})
result = {'meshes': {}, 'materials': {}, 'tested': False}

def disk(path):
    return P / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')

for key, path in meshes.items():
    mesh = u.load_asset(path)
    if not mesh:
        raise RuntimeError('Missing production input ' + path)
    skeletal = isinstance(mesh, u.SkeletalMesh)
    slots = mesh.get_editor_property('materials' if skeletal else 'static_materials')
    result['meshes'][key] = {'path': path, 'skeletal': skeletal, 'slots': []}
    for slot in slots:
        mat = slot.material_interface
        mp = mat.get_path_name() if mat else None
        result['meshes'][key]['slots'].append({'slot': str(slot.material_slot_name), 'material': mp})
        if not mp or '/A762/SurfaceStandard08/' not in mp or mp in result['materials']:
            continue
        if not isinstance(mat, u.MaterialInstanceConstant):
            raise RuntimeError('Unexpected material type ' + mp)
        base = mat.get_base_material()
        parameters = {}
        for kind in ('scalar', 'vector', 'texture'):
            parameters[kind] = {}
            for name in getattr(L, 'get_' + kind + '_parameter_names')(base):
                value = getattr(L, 'get_material_instance_' + kind + '_parameter_value')(mat, name)
                parameters[kind][str(name)] = (value.get_path_name() if value else None) if kind == 'texture' else ([value.r, value.g, value.b, value.a] if kind == 'vector' else value)
        result['materials'][mp] = {
            'parent': mat.get_editor_property('parent').get_path_name(),
            'base': base.get_path_name(),
            'sha256': hashlib.sha256(disk(mp).read_bytes()).hexdigest(),
            'parameters': parameters,
        }
(OUT / 'current.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('A762_SURFACE_R06_INPUTS', len(result['materials']), len(result['meshes']), flush=True)
