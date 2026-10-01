"""Capture current 201 material inputs; no mesh export, edits or test pass."""
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
    raise RuntimeError('Preserve captured baseline')
OLD = P / 'SourceAssets/LMG20120260927'
jobs = json.loads((OLD / 'SurfaceFinish50/materials.json').read_text())['jobs']
roles = {v['asset']: v['role'] for v in jobs.values()}
paths = sorted(json.loads((OLD / 'SurfaceFinish50/bindings.json').read_text()))
result = {'meshes': {}, 'materials': {}, 'graphs': {}, 'sources': {}, 'tested': False}


def digest(asset):
    path = asset.get_path_name()
    file = P / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')
    result['sources'][path] = hashlib.sha256(file.read_bytes()).hexdigest()
    return path


for path in paths:
    mesh = u.load_asset(path)
    if not mesh:
        raise RuntimeError('Missing current mesh ' + path)
    skeletal = isinstance(mesh, u.SkeletalMesh)
    result['meshes'][path] = {'skeletal': skeletal, 'slots': [], 'sha256': digest(mesh) and result['sources'][path]}
    for s in mesh.get_editor_property('materials' if skeletal else 'static_materials'):
        mat = s.material_interface
        mp = mat.get_path_name() if mat else None
        result['meshes'][path]['slots'].append({'slot': str(s.material_slot_name), 'material': mp})
        if not mp or mp in result['materials']:
            continue
        if '/LMG201/' not in mp:
            continue
        base = mat.get_base_material()
        bp = digest(base)
        params = {}
        for kind in ('scalar', 'vector', 'texture'):
            params[kind] = {}
            for name in getattr(L, 'get_' + kind + '_parameter_names')(base):
                fn = 'get_material_instance_' if isinstance(mat, u.MaterialInstanceConstant) else 'get_material_default_'
                v = getattr(L, fn + kind + '_parameter_value')(mat, name)
                params[kind][str(name)] = (v.get_path_name() if v else None) if kind == 'texture' else ([v.r, v.g, v.b, v.a] if kind == 'vector' else v)
        result['materials'][mp] = {'base': bp, 'class': type(mat).__name__, 'role': roles.get(mp),
            'sha256': digest(mat) and result['sources'][mp], 'parameters': params,
            'blend': str(base.get_editor_property('blend_mode'))}
        if bp not in result['graphs']:
            result['graphs'][bp] = [{'description': str(n.get_editor_property('description')),
                'code': str(n.get_editor_property('code')),
                'inputs': [str(i.get_editor_property('input_name')) for i in n.get_editor_property('inputs')]}
                for n in L.get_material_expressions(base) if isinstance(n, u.MaterialExpressionCustom)]

weather_path = '/Game/Weapons/LMG201/Accessories22/DA_LMG201_AttachmentWetMaterials'
weather = u.load_asset(weather_path)
if not weather:
    raise RuntimeError('Missing 201 weather table ' + weather_path)
result['weather'] = {'path': digest(weather), 'sha256': result['sources'][weather.get_path_name()],
    'mapping': {str(k): v.get_path_name() if v else None for k, v in weather.get_editor_property('wet_materials').items()}}
(OUT / 'current.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('WEAPON_SURFACE_201_R01_INPUTS', len(result['meshes']), len(result['materials']), flush=True)
