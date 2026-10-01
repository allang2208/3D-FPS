"""Import/compile/save the SVD R04 finish. No PIE, preview or test pass."""
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
ROOT = '/Game/Weapons/SVDDragunov20260922/SurfaceStandard20261001/Refine04'
RP = O / 'apply_receipt.json'
receipt = json.loads(RP.read_text()) if RP.exists() else {'version': R['version'],
    'textures': {}, 'masters': {}, 'instances': {}, 'complete': False,
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


# Preserve any newer disk edits or unsaved editor work before this batch writes.
dirty = set()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('PIE active; preserve the current session')
    dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
wet_asset = load('/Game/Weapons/SVDDragunov20260922/Accessories20260923/DA_SVD_AttachmentWetMaterials')
weather = dict(wet_asset.get_editor_property('wet_materials'))
bindings = {}
for t in R['targets']:
    path = t['material']
    if path.split('.')[0] in dirty or t['base'].split('.')[0] in dirty:
        raise RuntimeError('Unsaved target/source ' + path)
    prior = receipt['instances'].get(path)
    if sha(disk(path)) != (prior['saved_sha256'] if prior else t['sha256']):
        raise RuntimeError('Concurrent material change ' + path)
    mi = load(path)
    if mi.get_editor_property('parent').get_path_name() != (prior['parent'] if prior else t['parent']):
        raise RuntimeError('Material inheritance changed ' + path)
    if weather.get(path) != mi:
        raise RuntimeError('SVD wet self mapping changed ' + path)
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
    if path in dirty:
        raise RuntimeError('Unsaved texture ' + path)
    if sha(Path(spec['source'])) != spec['sha256']:
        raise RuntimeError('Texture source changed; regenerate recipe ' + name)
    if name not in receipt['textures']:
        if E.does_asset_exist(path):
            raise RuntimeError('New texture path occupied ' + path)
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


def wire(src, target, pin):
    node, output = src if isinstance(src, tuple) else (src, '')
    if not L.connect_material_expressions(node, output, target, pin):
        raise RuntimeError('Material connection failed: ' + pin)


def input_of(material, node, name):
    pins = [str(p.get_editor_property('input_name')) for p in node.get_editor_property('inputs')]
    source = L.get_inputs_for_material_expression(material, node)[pins.index(name)]
    return source, str(L.get_input_node_output_name_for_material_expression(node, source))


def furniture_master(source):
    target = ROOT + '/Master/M_SVD_R04_OriginalFurniture'
    if source in receipt['masters']:
        return load(receipt['masters'][source]['path'])
    if target in dirty or E.does_asset_exist(target):
        raise RuntimeError('Private material destination occupied ' + target)
    m = E.duplicate_asset(source, target)
    if not m:
        raise RuntimeError('Material duplicate failed ' + source)
    custom = {str(n.get_editor_property('description')): n for n in L.get_material_expressions(m)
        if isinstance(n, u.MaterialExpressionCustom)}
    old = custom['SVD R03 differentiated dielectric finish']
    inputs = {name: input_of(m, old, name) for name in ('Base', 'Rough', 'Finish', 'Region', 'Exterior', 'Dielectric')}
    inputs['Grain'] = custom['WS_Grain']
    for name, param, value in [('PolymerRough', 'R04_PolymerRoughness', .54),
        ('PolymerGrain', 'R04_PolymerGrain', .022), ('ColorCleanup', 'R04_PolymerColorCleanup', .30)]:
        n = L.create_material_expression(m, u.MaterialExpressionScalarParameter)
        n.set_editor_property('parameter_name', param)
        n.set_editor_property('default_value', value)
        n.set_editor_property('group', 'SVD Refine04')
        inputs[name] = n
    node = L.create_material_expression(m, u.MaterialExpressionCustom)
    node.set_editor_property('description', 'SVD R04 fine polymer finish')
    node.set_editor_property('code', (O / 'DielectricFinish.hlsl').read_text())
    node.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT4)
    pins = []
    for name in inputs:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    node.set_editor_property('inputs', pins)
    for name, src in inputs.items():
        wire(src, node, name)
    wire(node, custom['WS_Wet'], 'CR')
    # Both normal stages and the single wetness pass stay wired as authored.
    E.set_metadata_tag(m, 'WeaponSurfaceGraph', R['version'])
    E.set_metadata_tag(m, 'WeaponSurfaceSourceGraph', source)
    errors = L.recompile_material(m)
    if errors:
        raise RuntimeError('Material compilation failed ' + str(errors))
    save(m)
    receipt['masters'][source] = {'path': m.get_path_name(), 'saved': True}
    record()
    return m


for index, t in enumerate(R['targets']):
    path = t['material']
    if path in receipt['instances']:
        continue
    mi = load(path)
    backup = O / 'Before' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(disk(path), backup)
    if t['mixed_polymer']:
        L.set_material_instance_parent(mi, furniture_master(t['base']))
    # Names are derived from the captured live interface. UE 5.8 setters return
    # false even after a successful set; do not use that return value as a test.
    for name, value in t['scalars'].items():
        L.set_material_instance_scalar_parameter_value(mi, name, float(value))
    for name, value in t['textures'].items():
        L.set_material_instance_texture_parameter_value(mi, name, textures[value])
    L.update_material_instance(mi)
    E.set_metadata_tag(mi, 'WeaponSurfaceRevision', R['version'])
    save(mi)
    receipt['instances'][path] = {'saved': True, 'saved_sha256': sha(disk(path)),
        'backup': str(backup), 'parent': mi.get_editor_property('parent').get_path_name(),
        'category': t['category'], 'mixed_polymer': t['mixed_polymer'], 'scalars': t['scalars'],
        'textures': {n: textures[v].get_path_name() for n, v in t['textures'].items()}}
    record()
    if (index + 1) % 10 == 0:
        print('WEAPON_SURFACE_SVD_R04_PROGRESS', index + 1, flush=True)
receipt['complete'] = True
record()
print('WEAPON_SURFACE_SVD_R04_SAVED', len(receipt['instances']), 'instances', len(receipt['textures']),
    'texture', len(receipt['masters']), 'private master; tested=False', flush=True)
