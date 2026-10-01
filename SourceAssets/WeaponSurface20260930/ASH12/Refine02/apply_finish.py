"""Import, compile and save ASH12 R02 through the shared gated runner.

Retain all slot bindings, source normals, region identities and the UV1-6
extension seam reconstruction. No PIE, preview rendering or extra tests.
"""
import hashlib
import json
import shutil
from pathlib import Path
import unreal as u

O = Path(__file__).parent
P = Path(u.Paths.project_dir()).resolve()
if P != Path('D:/FPS3D/FPSGAME').resolve():
    raise RuntimeError('Wrong project')
L, E, A = u.MaterialEditingLibrary, u.EditorAssetLibrary, u.AssetToolsHelpers.get_asset_tools()
C = json.loads((O / 'Input/current.json').read_text())
R = json.loads((O / 'recipe.json').read_text())
ROOT = '/Game/Weapons/ASH12/SurfaceStandard20260930/Refine02'
RP = O / 'apply_receipt.json'
receipt = json.loads(RP.read_text()) if RP.exists() else {'version': R['version'],
    'textures': {}, 'masters': {}, 'presets': {}, 'instances': {}, 'complete': False,
    'mesh_changed': False, 'wet_table_changed': False, 'tested': False}


def record():
    RP.write_text(json.dumps(receipt, indent=2), encoding='utf-8')


def disk(path):
    return P / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')


def sha(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def load(path):
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError('Missing production asset ' + path)
    return asset


def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Asset save failed ' + asset.get_path_name())


# Concurrency/ownership guards; never overwrite unrelated unsaved assets.
dirty = set()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('PIE active; preserve the current session')
    dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(ROOT + '/') for p in dirty):
    raise RuntimeError('Unsaved R02 production assets')
targets = {t['material'] for t in R['targets']}
for path, digest in C['sources'].items():
    if path.split('.')[0] in dirty:
        raise RuntimeError('Unsaved production input ' + path)
    if path not in targets and sha(disk(path)) != digest:
        raise RuntimeError('Source material changed ' + path)
weather = dict(load('/Game/Weapons/ASH12/Surface20260919/DA_ASH12_WetMaterials').get_editor_property('wet_materials'))
bindings = {}
for t in R['targets']:
    path = t['material']
    prior = receipt['instances'].get(path)
    if sha(disk(path)) != (prior['saved_sha256'] if prior else t['sha256']):
        raise RuntimeError('Concurrent material change ' + path)
    mi = load(path)
    if mi.get_editor_property('parent').get_path_name() != (prior['parent'] if prior else t['parent']):
        raise RuntimeError('Material inheritance changed ' + path)
    if weather.get(path) != mi:
        raise RuntimeError('ASH12 wet self mapping changed ' + path)
    key = t['mesh']
    if key not in bindings:
        row = C['meshes'][key]
        if row['path'].split('.')[0] in dirty:
            raise RuntimeError('Unsaved mesh input ' + row['path'])
        mesh = load(row['path'])
        bindings[key] = {str(s.material_slot_name): s.material_interface.get_path_name() if s.material_interface else None
            for s in mesh.get_editor_property('materials' if row['skeletal'] else 'static_materials')}
    if bindings[key].get(t['slot']) != path:
        raise RuntimeError('Material binding changed ' + key + ' ' + t['slot'])

textures = {}
for name, spec in R['textures'].items():
    path = spec['asset']
    if sha(Path(spec['source'])) != spec['sha256']:
        raise RuntimeError('Texture source changed; regenerate recipe ' + name)
    if name not in receipt['textures']:
        if E.does_asset_exist(path):
            raise RuntimeError('New texture destination occupied ' + path)
        task = u.AssetImportTask()
        task.filename = spec['source']
        task.destination_path, task.destination_name = path.rsplit('/', 1)
        task.automated, task.replace_existing, task.save = True, False, False
        A.import_asset_tasks([task])
        tex = load(path)
        tex.set_editor_property('srgb', False)
        tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_BC7)
        tex.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_WEAPON)
        tex.set_editor_property('address_x', u.TextureAddress.TA_WRAP)
        tex.set_editor_property('address_y', u.TextureAddress.TA_WRAP)
        E.set_metadata_tag(tex, 'WeaponSurfaceVersion', R['version'])
        save(tex)
        receipt['textures'][name] = {'path': path, 'source_sha256': spec['sha256'], 'saved': True}
        record()
    textures[name] = load(path)


def node(m, cls, **props):
    n = L.create_material_expression(m, cls)
    for key, value in props.items():
        n.set_editor_property(key, value)
    return n


def wire(src, target, pin):
    n, output = src if isinstance(src, tuple) else (src, '')
    if not L.connect_material_expressions(n, output, target, pin):
        raise RuntimeError('Material connection failed: ' + pin)


def regional_master(source):
    if source in receipt['masters']:
        return load(receipt['masters'][source]['path'])
    path = ROOT + '/Master/M_ASH12_R02_Regions'
    if E.does_asset_exist(path):
        raise RuntimeError('New regional graph destination occupied ' + path)
    m = E.duplicate_asset(source, path)
    if not m:
        raise RuntimeError('Regional graph duplicate failed')
    expressions = list(L.get_material_expressions(m))
    params = {str(n.get_editor_property('parameter_name')): n for n in expressions
        if isinstance(n, (u.MaterialExpressionScalarParameter, u.MaterialExpressionVectorParameter))}
    custom = {str(n.get_editor_property('description')): n for n in expressions
        if isinstance(n, u.MaterialExpressionCustom)}
    defaults = {k: v for k, v in next(t for t in R['targets'] if t['regional'])['scalars'].items()
        if k.startswith('R02_')}
    for name, value in defaults.items():
        params[name] = node(m, u.MaterialExpressionScalarParameter, parameter_name=name,
            default_value=value, group='ASH12 Refine02 Regions')
    # Preserve R/G/B thresholds and priority. Add only per-region finish
    # controls; metallic identities, normal wiring and dry bore stay intact.
    mask = custom['ASH12 authored surface regions']
    zero = node(m, u.MaterialExpressionConstant, r=0.)
    for base_name, pin, suffix in (
        ('GrainRoughness', 'GrainR', 'GrainRoughness'),
        ('MottleRoughness', 'MottleR', 'MottleRoughness'),
        ('CavityDarken', 'CavDark', 'CavityDarken'),
        ('CavityRoughness', 'CavRough', 'CavityRoughness')):
        inputs = {'Base': params[base_name], 'Red': params['R02_RegionPolymer' + suffix],
            'Green': params['R02_RegionBolt' + suffix], 'Blue': zero, 'Mask': mask}
        n = node(m, u.MaterialExpressionCustom,
            code='return lerp(lerp(lerp(Base,Red,Mask.r),Green,Mask.g),Blue,Mask.b);',
            description='ASH12 R02 ' + suffix + ' regions', output_type=u.CustomMaterialOutputType.CMOT_FLOAT1)
        pins = []
        for key in inputs:
            p = u.CustomInput()
            p.set_editor_property('input_name', key)
            pins.append(p)
        n.set_editor_property('inputs', pins)
        for key, src in inputs.items():
            wire(src, n, key)
        wire(n, custom['WS_ColorRough'], pin)
    wire(params['R02_RegionPolymerEdgeHighlight'], custom['ASH12 Edge highlight regions'], 'Red')
    wire(params['R02_RegionBoltEdgeHighlight'], custom['ASH12 Edge highlight regions'], 'Green')
    wire(params['R02_RegionPolymerStipple'], custom['ASH12 Polymer stipple'], 'Red')
    E.set_metadata_tag(m, 'WeaponSurfaceGraph', R['version'])
    E.set_metadata_tag(m, 'WeaponSurfaceSourceGraph', source)
    errors = L.recompile_material(m)
    if errors:
        raise RuntimeError('Regional material compilation failed ' + str(errors))
    save(m)
    receipt['masters'][source] = {'path': m.get_path_name(), 'saved': True}
    record()
    return m


def regional_parent(t):
    source = t['parent']
    if source in receipt['presets']:
        return load(receipt['presets'][source]['path'])
    master = regional_master(t['base'])
    path = ROOT + '/Presets/MI_ASH12_R02_Regions_' + t['preset']
    if E.does_asset_exist(path):
        raise RuntimeError('New regional preset destination occupied ' + path)
    preset = E.duplicate_asset(source, path)
    if not preset:
        raise RuntimeError('Regional preset duplicate failed ' + source)
    # Copy the current preset so inherited metallic/normal/wetness parameters
    # are retained, rather than clearing overrides or flattening into defaults.
    L.set_material_instance_parent(preset, master)
    L.update_material_instance(preset)
    E.set_metadata_tag(preset, 'WeaponSurfaceRevision', R['version'])
    save(preset)
    receipt['presets'][source] = {'path': preset.get_path_name(), 'saved': True}
    record()
    return preset


for index, t in enumerate(R['targets']):
    path = t['material']
    if path in receipt['instances']:
        continue
    mi = load(path)
    backup = O / 'Before' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(disk(path), backup)
    if t['regional']:
        L.set_material_instance_parent(mi, regional_parent(t))
    for name, value in t['scalars'].items():
        L.set_material_instance_scalar_parameter_value(mi, name, float(value))
    for name, value in t['vectors'].items():
        L.set_material_instance_vector_parameter_value(mi, name, u.LinearColor(*value, 1))
    for name, value in t['textures'].items():
        L.set_material_instance_texture_parameter_value(mi, name, textures[value])
    L.update_material_instance(mi)
    E.set_metadata_tag(mi, 'WeaponSurfaceRevision', R['version'])
    save(mi)
    receipt['instances'][path] = {'saved': True, 'saved_sha256': sha(disk(path)),
        'backup': str(backup), 'parent': mi.get_editor_property('parent').get_path_name(),
        'preset': t['preset'], 'regional': t['regional'], 'scalars': t['scalars'], 'vectors': t['vectors'],
        'textures': {n: textures[v].get_path_name() for n, v in t['textures'].items()}}
    record()
    if (index + 1) % 5 == 0:
        print('WEAPON_SURFACE_ASH12_R02_PROGRESS', index + 1, flush=True)
receipt['complete'] = True
record()
print('WEAPON_SURFACE_ASH12_R02_SAVED', len(receipt['instances']), 'instances', len(receipt['textures']),
    'texture', len(receipt['masters']), 'regional master', len(receipt['presets']), 'presets; tested=False', flush=True)
