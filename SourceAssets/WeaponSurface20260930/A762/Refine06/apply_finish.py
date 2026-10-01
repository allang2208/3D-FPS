"""Import and save the A762 Refine06 finish; same MIs, parents and mesh bindings.

Run through ../../run_ue.ps1. This performs production import/save only, no PIE,
rendering, screenshots or validation pass. Exact target backups are retained.
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
R = json.loads((O / 'recipe.json').read_text())
C = json.loads((O / 'Input/current.json').read_text())
RP = O / 'apply_receipt.json'
receipt = json.loads(RP.read_text()) if RP.exists() else {
    'version': R['version'], 'textures': {}, 'instances': {}, 'complete': False,
    'mesh_changed': False, 'parent_changed': False, 'wetness_changed': False, 'tested': False}

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

# Ownership/concurrency guards precede any write. Do not overwrite unsaved
# editor content, a different slot binding or changed material inputs.
dirty = set()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('PIE active; preserve the current session')
    dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
bindings = {}
for key, row in C['meshes'].items():
    if row['path'].split('.')[0] in dirty:
        raise RuntimeError('Unsaved mesh binding input ' + row['path'])
    mesh = load(row['path'])
    bindings[key] = {str(s.material_slot_name): s.material_interface.get_path_name() if s.material_interface else None
        for s in mesh.get_editor_property('materials' if row['skeletal'] else 'static_materials')}
for t in R['targets']:
    path = t['material']
    if path.split('.')[0] in dirty:
        raise RuntimeError('Unsaved target ' + path)
    prior = receipt['instances'].get(path)
    expected = prior['saved_sha256'] if prior else t['sha256']
    if sha(disk(path)) != expected:
        raise RuntimeError('Concurrent material change ' + path)
    mi = load(path)
    if mi.get_editor_property('parent').get_path_name() != t['parent'] or mi.get_base_material().get_path_name() != t['base']:
        raise RuntimeError('Material inheritance changed ' + path)
    if bindings[t['mesh']].get(t['slot']) != path:
        raise RuntimeError('Material slot changed ' + t['mesh'] + ' ' + t['slot'])

textures = {}
for name, spec in R['textures'].items():
    path = spec['asset']
    if path in dirty:
        raise RuntimeError('Unsaved texture ' + path)
    if sha(Path(spec['source'])) != spec['sha256']:
        raise RuntimeError('Texture source changed; regenerate its recipe ' + name)
    if name not in receipt['textures']:
        if E.does_asset_exist(path):
            raise RuntimeError('New texture path already occupied ' + path)
        task = u.AssetImportTask()
        task.filename = spec['source']
        task.destination_path, task.destination_name = path.rsplit('/', 1)
        task.automated, task.replace_existing, task.save = True, False, False
        A.import_asset_tasks([task])
        tex = load(path)
        tex.set_editor_property('srgb', False)
        tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_NORMALMAP if spec['kind'] == 'normal' else u.TextureCompressionSettings.TC_BC7)
        tex.set_editor_property('flip_green_channel', False)
        tex.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_WEAPON)
        tex.set_editor_property('address_x', u.TextureAddress.TA_WRAP)
        tex.set_editor_property('address_y', u.TextureAddress.TA_WRAP)
        E.set_metadata_tag(tex, 'WeaponSurfaceVersion', R['version'])
        save(tex)
        receipt['textures'][name] = {'path': path, 'source_sha256': spec['sha256'], 'saved': True}
        record()
    textures[name] = load(path)

for t in R['targets']:
    path = t['material']
    if path in receipt['instances']:
        continue
    mi = load(path)
    backup = O / 'Before' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(disk(path), backup)
    # Patch only authored finish parameters; keep the preset parent, source
    # atlas, UV channels, seated AO, optical paths and wetness controls intact.
    # UE 5.8 MaterialEditingLibrary setters leave bResult=false even after
    # setting a value. Parameter names come from the captured live interface.
    parameters = C['materials'][path]['parameters']
    for name, value in t['scalars'].items():
        if name not in parameters['scalar']:
            raise RuntimeError('Unknown scalar ' + name)
        L.set_material_instance_scalar_parameter_value(mi, name, float(value))
    for name, value in t['vectors'].items():
        if name not in parameters['vector']:
            raise RuntimeError('Unknown vector ' + name)
        L.set_material_instance_vector_parameter_value(mi, name, u.LinearColor(*value, 1))
    for name, value in t['textures'].items():
        if name not in parameters['texture']:
            raise RuntimeError('Unknown texture parameter ' + name)
        L.set_material_instance_texture_parameter_value(mi, name, textures[value])
    L.update_material_instance(mi)
    E.set_metadata_tag(mi, 'WeaponSurfaceRevision', R['version'])
    save(mi)
    receipt['instances'][path] = {'saved': True, 'saved_sha256': sha(disk(path)),
        'backup': str(backup), 'family': t['family'], 'scalars': t['scalars'], 'vectors': t['vectors'],
        'textures': {name: textures[value].get_path_name() for name, value in t['textures'].items()}}
    record()
receipt['complete'] = True
record()
print('A762_SURFACE_R06_SAVED', len(receipt['instances']), 'instances', len(receipt['textures']), 'textures; tested=False', flush=True)
