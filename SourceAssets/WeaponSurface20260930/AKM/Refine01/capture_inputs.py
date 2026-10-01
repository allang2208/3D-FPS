"""Read current AKM production material inputs; no scene or mesh export."""
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
paths = ['/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative']
paths += ['/Game/Weapons/AttachmentFinish20260913/AKM/Meshes/SM_AKM_' + k
    for k in ('vertical', 'canted_CompactMount', 'prism', 'drum', 'suppressor', 'brake', 'titanium_brake')]
paths += ['/Game/Weapons/AKMIntegration/SovietFab/OpticSteel/' + k
    for k in ('SM_AKM_optic', 'SM_LPVO1to6X', 'SM_PrismScope2X', 'SM_PanoramicRedDot', 'SM_LPVORing')]
paths += ['/Game/Weapons/AKMIntegration/SovietFab/Optics/SM_AKM_Mount_' + k
    for k in ('lpvo_1_6x', 'prism_scope_2x', 'panoramic_red_dot')]
paths += [
    '/Game/Weapons/ExtMagContinuity20260919/SM_ExtMag_AKM40_Continuous',
    '/Game/Weapons/ResonanceGrip20260913/MeshyIntegration/AKM/SM_ResonanceGrip',
    '/Game/Weapons/TacticalVerticalForegrip20260919/AKM/SM_TacticalVerticalForegrip',
    '/Game/Weapons/TacticalSuppressor20260913/AKM/SM_TacticalSuppressor',
    '/Game/Weapons/ReferenceStock5080/AKM/SM_SkeletonStock',
    '/Game/Weapons/QRPerformanceStock/Meshy20260913/AKM/SM_PerformanceStock',
    '/Game/Weapons/CoreStock20260914/Meshy0914005605/AKM/SM_CoreStock',
    '/Game/Weapons/TacticalTelescopicStock20260914/AKM/SM_TacticalTelescopicStock',
    '/Game/Weapons/StableAntiSlipRearGrip/Selected91727/AKM/SM_StableAntiSlipRearGrip',
    '/Game/Weapons/RearGripFinish20260913/AKM/balanced/SM_BalancedRearGrip',
    '/Game/Weapons/RearGripFinish20260913/AKM/phantom/SM_PhantomRearGrip',
    '/Game/Weapons/PSO1Russian20260923/AKM/SM_PSO1_AKM',
    '/Game/Weapons/TacticalDevices20260913/AKM/laser/SM_TacticalDevice',
    '/Game/Weapons/TacticalDevices20260913/HunyuanV3/AKM/flashlight/SM_TacticalDevice',
]
OVERRIDES = {
    '/Game/Weapons/TacticalDevices20260913/AKM/laser/SM_TacticalDevice':
        ('M_Tactical_laser', '/Game/Weapons/TacticalDevices20260913/AKM/laser/M_AKM_laser_Body_OpticalV2'),
    '/Game/Weapons/TacticalDevices20260913/HunyuanV3/AKM/flashlight/SM_TacticalDevice':
        ('M_Tactical_flashlight', '/Game/Weapons/TacticalDevices20260913/HunyuanV3/AKM/flashlight/M_AKM_flashlight_Body_MetalTail'),
}


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
        raise RuntimeError('Missing current AKM mesh ' + path)
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
for path in ('/Game/Weather/RainVisibility/DA_WeatherPresentation', '/Game/Weapons/PSO1Russian20260923/DA_PSO1_WetMaterials'):
    table = u.load_asset(path)
    if not table:
        raise RuntimeError('Missing weather library ' + path)
    mapping.update({str(k): v.get_path_name() if v else None for k, v in table.get_editor_property('wet_materials').items()})
    tables.append(digest(table))
# These pairs are registered explicitly by WeatherViewEffectsComponent.
mapping['/Game/Weapons/ExtMagContinuity20260919/Materials/M_AKM_Continuous_Graph.M_AKM_Continuous_Graph'] = '/Game/Weapons/ExtMagContinuity20260919/Materials/M_AKMWet_Continuous_Graph.M_AKMWet_Continuous_Graph'
for path in list(result['materials']):
    if mapping.get(path):
        describe(u.load_asset(mapping[path]))
result['weather'] = {'path': tables[0], 'mapping': mapping, 'read_tables': tables}
(OUT / 'current.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('WEAPON_SURFACE_AKM_R01_INPUTS', len(result['meshes']), len(result['materials']), flush=True)
