"""Read current M16 production material inputs; no scene or mesh export."""
import hashlib
import json
from pathlib import Path
import unreal as u

O = Path(__file__).parent
P = Path(u.Paths.project_dir()).resolve()
if P != Path('D:/FPS3D/FPSGAME').resolve():
    raise RuntimeError('Wrong project')
E, L = u.EditorAssetLibrary, u.MaterialEditingLibrary
OUT = O / 'Input'
OUT.mkdir(parents=True, exist_ok=True)
if (OUT / 'current.json').exists():
    raise RuntimeError('Preserve captured baseline')
result = {'meshes': {}, 'materials': {}, 'graphs': {}, 'sources': {}, 'overrides': {}, 'tested': False}
paths = ['/Game/Weapons/M16A2/Gameplay20260919/SK_M16_Manny',
 '/Game/Weapons/HK416/ARParts20261001/M16/SM_416_Stock',
 '/Game/Weapons/HK416/ARParts20261001/M16/SM_416_RearGrip',
 '/Game/Weapons/CommonHK41620260930/Meshes/SM_M16_eoth_holographic']
for path in E.list_assets('/Game/Weapons/M16A2/UniversalAttachments20260920/Meshes', recursive=True, include_folder=False):
    if E.find_asset_data(path).asset_class_path.asset_name == 'StaticMesh':
        paths.append(path)
OVERRIDES = {}


def digest(obj):
    path = obj.get_path_name()
    if path.startswith('/Game/'):
        file = P / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')
        result['sources'][path] = hashlib.sha256(file.read_bytes()).hexdigest()
    return path


def prop(obj, name, default=None):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return default


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
            v = getattr(L, prefix + kind + '_parameter_value')(mat, name)
            params[kind][str(name)] = (v.get_path_name() if v else None) if kind == 'texture' else ([v.r, v.g, v.b, v.a] if kind == 'vector' else v)
    digest(mat)
    result['materials'][path] = {'base': bp, 'class': type(mat).__name__, 'parameters': params,
        'blend': str(base.get_editor_property('blend_mode'))}
    if bp not in result['graphs']:
        nodes = []
        for n in L.get_material_expressions(base):
            row = {'name': n.get_name(), 'class': n.get_class().get_name()}
            for key in ('description', 'code', 'coordinate_index', 'parameter_name', 'r', 'constant', 'default_value', 'const_a', 'const_b', 'const_min', 'const_max'):
                v = prop(n, key)
                if v is not None:
                    row[key] = v if isinstance(v, (str, float, int, bool)) else str(v)
            tex = prop(n, 'texture')
            if tex:
                row['texture'] = tex.get_path_name()
            if isinstance(n, u.MaterialExpressionCustom):
                row['custom_inputs'] = [str(i.get_editor_property('input_name')) for i in n.get_editor_property('inputs')]
            row['connections'] = [s.get_name() if s else None for s in L.get_inputs_for_material_expression(base, n)]
            nodes.append(row)
        outputs = {}
        for name in ('BASE_COLOR', 'ROUGHNESS', 'METALLIC', 'NORMAL', 'AMBIENT_OCCLUSION', 'EMISSIVE_COLOR'):
            p = getattr(u.MaterialProperty, 'MP_' + name)
            n = L.get_material_property_input_node(base, p)
            outputs[name] = [n.get_name() if n else None, str(L.get_material_property_input_node_output_name(base, p))]
        result['graphs'][bp] = {'nodes': nodes, 'outputs': outputs}


for path in paths:
    mesh = u.load_asset(path)
    if not isinstance(mesh, (u.SkeletalMesh, u.StaticMesh)):
        raise RuntimeError('Missing current M16 mesh ' + path)
    path = digest(mesh)
    sk = isinstance(mesh, u.SkeletalMesh)
    row = {'skeletal': sk, 'sha256': result['sources'][path], 'slots': []}
    for i, s in enumerate(mesh.get_editor_property('materials' if sk else 'static_materials')):
        mat = s.material_interface
        mp = mat.get_path_name() if mat else None
        row['slots'].append({'index': i, 'slot': str(s.material_slot_name), 'material': mp})
        if mat and mp.startswith('/Game/Weapons/'):
            describe(mat)
    result['meshes'][path] = row
    override = OVERRIDES.get(path.split('.')[0])
    if override:
        mat = u.load_asset(override[1])
        if not mat:
            raise RuntimeError('Missing runtime override')
        describe(mat)
        result['overrides'][path] = {'slot': override[0], 'material': mat.get_path_name()}

mapping = {}
tables = []
for path in ('/Game/Weather/RainVisibility/DA_WeatherPresentation', '/Game/Weapons/HK416/Reworked20260930/DA_HK416_WetMaterials', '/Game/Weapons/M16A2/UniversalAttachments20260920/DA_M16_AttachmentWetMaterials'):
    table = u.load_asset(path)
    if not table:
        raise RuntimeError('Missing weather library ' + path)
    mapping.update({str(k): v.get_path_name() if v else None for k, v in table.get_editor_property('wet_materials').items()})
    tables.append(digest(table))
for path in list(result['materials']):
    if mapping.get(path):
        describe(u.load_asset(mapping[path]))
result['weather'] = {'path': tables[-1], 'mapping': mapping, 'read_tables': tables}
result['pie_at_capture'] = bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()) if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() else False
(OUT / 'current.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('WEAPON_SURFACE_M16_R01_INPUTS', len(result['meshes']), len(result['materials']), 'PIE', result['pie_at_capture'], flush=True)
