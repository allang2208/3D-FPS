"""Read current PKM authoring inputs, without running a scene or exporting a mesh."""
import hashlib
import json
from pathlib import Path
import unreal as u

O = Path(__file__).parent
P = Path(u.Paths.project_dir()).resolve()
if P != Path('D:/FPS3D/FPSGAME').resolve():
    raise RuntimeError('Wrong project')
ROOT = '/Game/Weapons/PKMLowpoly20260922'
E, L = u.EditorAssetLibrary, u.MaterialEditingLibrary
OUT = O / 'Input'
OUT.mkdir(parents=True, exist_ok=True)
if (OUT / 'current.json').exists():
    raise RuntimeError('Preserve captured baseline')
result = {'meshes': {}, 'materials': {}, 'graphs': {}, 'sources': {}, 'tested': False}


def digest(obj):
    path = obj.get_path_name()
    file = P / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')
    result['sources'][path] = hashlib.sha256(file.read_bytes()).hexdigest()
    return path


def describe(mat):
    path = mat.get_path_name()
    if path in result['materials']:
        return
    base = mat.get_base_material()
    bp = digest(base)
    params = {}
    for kind in ('scalar', 'vector', 'texture'):
        params[kind] = {}
        for name in getattr(L, 'get_' + kind + '_parameter_names')(base):
            prefix = 'get_material_instance_' if isinstance(mat, u.MaterialInstanceConstant) else 'get_material_default_'
            value = getattr(L, prefix + kind + '_parameter_value')(mat, name)
            params[kind][str(name)] = (value.get_path_name() if value else None) if kind == 'texture' else ([value.r, value.g, value.b, value.a] if kind == 'vector' else value)
    result['materials'][path] = {'base': bp, 'class': type(mat).__name__,
        'category': str(E.get_metadata_tag(base, 'PKM20_Category')),
        'source': str(E.get_metadata_tag(base, 'PKM20_Source')),
        'sha256': digest(mat) and result['sources'][path], 'parameters': params,
        'blend': str(base.get_editor_property('blend_mode'))}
    if bp not in result['graphs']:
        result['graphs'][bp] = [{'description': str(n.get_editor_property('description')),
            'code': str(n.get_editor_property('code')),
            'inputs': [str(i.get_editor_property('input_name')) for i in n.get_editor_property('inputs')]}
            for n in L.get_material_expressions(base) if isinstance(n, u.MaterialExpressionCustom)]


paths = [ROOT + '/Accessories14/SK_PKM_Manny_Modular', ROOT + '/OpticMount23/SM_PKM_optic_rail']
for directory in ('Bipod26', 'Accessories14/Meshes'):
    paths += list(E.list_assets(ROOT + '/' + directory, recursive=False, include_folder=False))
for path in paths:
    mesh = u.load_asset(path)
    if not isinstance(mesh, (u.SkeletalMesh, u.StaticMesh)):
        continue
    path = digest(mesh)
    skeletal = isinstance(mesh, u.SkeletalMesh)
    row = {'skeletal': skeletal, 'sha256': result['sources'][path], 'slots': []}
    for i, s in enumerate(mesh.get_editor_property('materials' if skeletal else 'static_materials')):
        mat = s.material_interface
        mp = mat.get_path_name() if mat else None
        row['slots'].append({'index': i, 'slot': str(s.material_slot_name), 'material': mp})
        if mat and mp.startswith(ROOT + '/'):
            describe(mat)
    result['meshes'][path] = row
weather = u.load_asset(ROOT + '/Finish20/DA_PKM_WetMaterials')
if not weather:
    raise RuntimeError('Missing PKM weather library')
wp = digest(weather)
mapping = {str(k): v.get_path_name() if v else None for k, v in weather.get_editor_property('wet_materials').items()}
for source in list(result['materials']):
    if mapping.get(source):
        describe(u.load_asset(mapping[source]))
result['weather'] = {'path': wp, 'sha256': result['sources'][wp], 'mapping': mapping}
(OUT / 'current.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('WEAPON_SURFACE_PKM_R01_INPUTS', len(result['meshes']), len(result['materials']), flush=True)
