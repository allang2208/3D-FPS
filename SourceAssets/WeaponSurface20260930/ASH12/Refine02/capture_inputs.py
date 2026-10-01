"""Read current ASH12 finish inputs for production. No asset writes or tests."""
import hashlib
import json
from pathlib import Path
import unreal as u

O = Path(__file__).parent
P = Path(u.Paths.project_dir()).resolve()
if P != Path('D:/FPS3D/FPSGAME').resolve():
    raise RuntimeError('Wrong project')
L = u.MaterialEditingLibrary
OUT = O / 'Input'
OUT.mkdir(parents=True, exist_ok=True)
if (OUT / 'current.json').exists():
    raise RuntimeError('Preserve the existing production baseline')
PLAN = json.loads((O.parent / 'slot_plan.json').read_text())
result = {'meshes': {}, 'materials': {}, 'graphs': {}, 'sources': {}, 'tested': False}


def source(asset):
    path = asset.get_path_name()
    if path not in result['sources']:
        file = P / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')
        result['sources'][path] = hashlib.sha256(file.read_bytes()).hexdigest()
    return path


for key, entry in PLAN.items():
    if not any(s['action'] == 'preset' for s in entry['slots'].values()):
        continue
    mesh = u.load_asset(entry['path'])
    if not mesh:
        raise RuntimeError('Missing production mesh ' + entry['path'])
    skeletal = isinstance(mesh, u.SkeletalMesh)
    slots = mesh.get_editor_property('materials' if skeletal else 'static_materials')
    result['meshes'][key] = {'path': mesh.get_path_name(), 'skeletal': skeletal, 'slots': []}
    for slot in slots:
        name = str(slot.material_slot_name)
        mat = slot.material_interface
        mp = mat.get_path_name() if mat else None
        result['meshes'][key]['slots'].append({'slot': name, 'material': mp})
        spec = entry['slots'].get(name)
        if not spec or spec['action'] != 'preset':
            continue
        if not isinstance(mat, u.MaterialInstanceConstant) or '/ASH12/SurfaceStandard20260930/Materials/' not in mp:
            raise RuntimeError('Unexpected production material ' + str(mp))
        base = mat.get_base_material()
        bp = source(base)
        parent = mat.get_editor_property('parent')
        chain = []
        while parent:
            chain.append(source(parent))
            parent = parent.get_editor_property('parent') if isinstance(parent, u.MaterialInstanceConstant) else None
        if bp not in result['graphs']:
            result['graphs'][bp] = [{'description': str(n.get_editor_property('description')),
                'code': str(n.get_editor_property('code')),
                'inputs': [str(i.get_editor_property('input_name')) for i in n.get_editor_property('inputs')]}
                for n in L.get_material_expressions(base) if isinstance(n, u.MaterialExpressionCustom)]
        params = {}
        for kind in ('scalar', 'vector', 'texture'):
            params[kind] = {}
            for pn in getattr(L, 'get_' + kind + '_parameter_names')(base):
                v = getattr(L, 'get_material_instance_' + kind + '_parameter_value')(mat, pn)
                params[kind][str(pn)] = (v.get_path_name() if v else None) if kind == 'texture' else ([v.r, v.g, v.b, v.a] if kind == 'vector' else v)
        source(mat)
        result['materials'][mp] = {'parent': chain[0], 'base': bp, 'chain': chain,
            'sha256': result['sources'][mp], 'parameters': params,
            'mesh': key, 'slot': name, 'preset': spec['preset'],
            'regional': bool(spec.get('regional')), 'seam_normal': bool(spec.get('seam_normal'))}
weather = u.load_asset('/Game/Weapons/ASH12/Surface20260919/DA_ASH12_WetMaterials')
result['wet_materials'] = {str(k): v.get_path_name() if v else None
    for k, v in weather.get_editor_property('wet_materials').items()}
(OUT / 'current.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('WEAPON_SURFACE_ASH12_R02_INPUTS', len(result['materials']), len(result['meshes']), flush=True)
