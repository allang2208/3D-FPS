"""Save TangDao-only blade-surface runes, retaining the current PBR and rune graph."""
import json
import shutil
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
SURFACE = P.parent
ROOT = P.parents[3]
E, L = u.MaterialEditingLibrary, u.EditorAssetLibrary
D = '/Game/Weapons/TangDao20261002/SurfaceV2/Materials'
REVISION = 'TangDaoNativeBladeRune20261002'
if Path(u.Paths.project_dir()).resolve() != ROOT:
    raise RuntimeError('TangDao blade-rune authoring requires FPSGAME')
receipt = {'revision': REVISION, 'assets': [], 'complete': False,
           'runtime_tested': False, 'geometry_changed': False, 'existing_pbr_preserved': True}

def record():
    (P / 'import_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')

def save(asset):
    # No installed rune: preserve the original PBR and skip the mask samples.
    inactive = 'if (RuneMode < -.5) return float4(0, 0, 0, 0);\n'
    for expression in E.get_material_expressions(asset):
        if isinstance(expression, u.MaterialExpressionCustom):
            code = expression.get_editor_property('code')
            if 'RuneTexture' in code and 'RuneMode' in code and not code.startswith(inactive):
                expression.set_editor_property('code', inactive + code)
    errors = list(E.recompile_material(asset) or [])
    if errors:
        raise RuntimeError('TangDao blade material compilation failed: ' + str(errors))
    L.set_metadata_tag(asset, 'TangDaoRuneSurfaceRevision', REVISION)
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False):
        raise RuntimeError('TangDao blade material save failed: ' + asset.get_path_name())
    receipt['assets'].append(asset.get_path_name())
    record()

def connect(a, output, b, pin):
    pin = '' if pin is None or str(pin) == 'None' else str(pin)
    if not E.connect_material_expressions(a, output, b, pin):
        raise RuntimeError('Blade-rune graph connection failed: ' + pin)

path = D + '/M_TangDaoBladeRuneSurface'
material = u.load_asset(path)
pending_file = P / 'authoring_pending.json'
pending = json.loads(pending_file.read_text(encoding='utf-8')) if pending_file.exists() else {}
if material and L.get_metadata_tag(material, 'TangDaoRuneSurfaceRevision') != REVISION and pending.get('asset') != path:
    raise RuntimeError('Preserved an unowned blade-rune material at ' + path)
if not material:
    source = u.load_asset(D + '/M_TangDaoSurface')
    if not source:
        raise RuntimeError('Missing refined blade surface')
    material = L.duplicate_asset(source.get_path_name(), path)
    if not material:
        raise RuntimeError('Private blade material duplication failed; retain the current editor asset state')
    pending = {'asset': path, 'copies': {}}
    pending_file.write_text(json.dumps(pending, indent=2), encoding='utf-8')
if L.get_metadata_tag(material, 'TangDaoRuneSurfaceRevision') != REVISION:
    runes = u.load_asset('/Game/Weapons/MeleeRunes20260915/SurfaceV2/M_SilverRuneSurfaceV2')
    if not runes:
        raise RuntimeError('Missing authored rune material')
    originals = list(E.get_material_expressions(runes))
    existing = {n.get_name(): n for n in E.get_material_expressions(material)}
    copies = {}
    for original in originals:
        name = original.get_name()
        previous = pending.get('copies', {}).get(name, name)
        copies[name] = existing.get(previous) or E.duplicate_material_expression(material, None, original)
        pending.setdefault('copies', {})[name] = copies[name].get_name()
    pending_file.write_text(json.dumps(pending, indent=2), encoding='utf-8')
    # Retain the exact current source nodes, parameters and HLSL. Reconnect every
    # copied input to nodes owned by the private blade material.
    for original in originals:
        inputs = list(E.get_inputs_for_material_expression(runes, original))
        names = list(E.get_material_expression_input_names(original))
        if len(inputs) != len(names):
            raise RuntimeError('Unexpected rune input layout: ' + original.get_name())
        for input_node, name in zip(inputs, names):
            if input_node:
                connect(copies[input_node.get_name()], '', copies[original.get_name()], str(name))
    original_rgb = E.get_material_property_input_node(runes, u.MaterialProperty.MP_EMISSIVE_COLOR)
    original_coverage = E.get_material_property_input_node(runes, u.MaterialProperty.MP_OPACITY)
    emission = copies[original_rgb.get_name()]
    coverage = copies[original_coverage.get_name()]
    # The old overlay used alpha blending. Weight its emission by the same
    # animated coverage before the existing exposure compensation.
    multiply = E.create_material_expression(material, u.MaterialExpressionMultiply)
    if isinstance(original_rgb, u.MaterialExpressionEyeAdaptationInverse):
        rgb_input = E.get_inputs_for_material_expression(runes, original_rgb)[0]
        connect(copies[rgb_input.get_name()], '', multiply, 'A')
        connect(coverage, '', multiply, 'B')
        connect(multiply, '', emission, str(E.get_material_expression_input_names(emission)[0]))
    else:
        connect(emission, '', multiply, 'A')
        connect(coverage, '', multiply, 'B')
        emission = multiply
    slab = E.get_material_property_input_node(material, u.MaterialProperty.MP_FRONT_MATERIAL)
    if not isinstance(slab, u.MaterialExpressionSubstrateShadingModels):
        raise RuntimeError('Preserved an unsupported refined blade surface graph')
    connect(emission, '', slab, 'Emissive Color')
    if not E.connect_material_property(emission, '', u.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError('Blade emission output connection failed')
    E.layout_material_expressions(material)
save(material)

temporal_path = path + '_Whirlwind'
temporal = u.load_asset(temporal_path)
if temporal and L.get_metadata_tag(temporal, 'TangDaoRuneSurfaceRevision') != REVISION:
    raise RuntimeError('Preserved an unowned temporal blade material')
if not temporal:
    temporal = L.duplicate_asset(material.get_path_name(), temporal_path)
    responsive = E.create_material_expression(temporal, u.MaterialExpressionTemporalResponsivenessOutput)
    one = E.create_material_expression(temporal, u.MaterialExpressionConstant)
    one.set_editor_property('r', 1.)
    connect(one, '', responsive, '')
save(temporal)

def write_json(file, data):
    backup = P / 'Before' / file.relative_to(ROOT)
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(file, backup)
    temporary = file.with_suffix(file.suffix + '.tangrune.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(file)

catalog_file = ROOT / 'Content/ColdSteelData/tang-dao-modules.json'
catalog = json.loads(catalog_file.read_text(encoding='utf-8-sig'))
bindings_file = SURFACE / 'bindings.json'
bindings = json.loads(bindings_file.read_text(encoding='utf-8-sig'))
for choice, row in catalog['slots']['blade_1'].items():
    row['materials']['M_TangDaoSurface'] = material.get_path_name()
    bindings['slots']['blade_1'][choice]['M_TangDaoSurface'] = material.get_path_name()
catalog['rune_surface_revision'] = REVISION
bindings['rune_surface_revision'] = REVISION
write_json(bindings_file, bindings)
write_json(catalog_file, catalog)
mapping_file = ROOT / 'Content/ColdSteelData/whirlwind-temporal-materials.json'
mapping = json.loads(mapping_file.read_text(encoding='utf-8-sig'))
mapping[material.get_path_name()] = temporal.get_path_name()
write_json(mapping_file, mapping)
receipt.update(complete=True, blade_choices=list(catalog['slots']['blade_1']),
               rune_graph_source=runes.get_path_name() if 'runes' in globals() else '/Game/Weapons/MeleeRunes20260915/SurfaceV2/M_SilverRuneSurfaceV2',
               shared_rune_material_modified=False, draw_path='opaque blade surface emission',
               inactive_mask_samples_skipped=True)
record()
print('TANGDAO_NATIVE_BLADE_RUNES_SAVED ' + json.dumps(receipt, ensure_ascii=False))

# Rebind the separately authored cloud-capable surfaces after the base refresh.
import runpy
cloud_extension = SURFACE.parent / 'CloudRune20261002/catalog_extension.py'
if cloud_extension.exists():
    cloud = runpy.run_path(str(cloud_extension), run_name='tang_dao_cloud_rune_extension')
    if cloud['installed']():
        cloud['install']()
