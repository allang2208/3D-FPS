"""Save only 18 M16 sprint clips and refresh 15 sprint profile entries.

Run through the project's existing mutex-protected UE Python batch bridge or
background PythonScript commandlet. No mesh, binding, material, catalog, reload
or non-sprint profile import. No gameplay, preview or acceptance test.
"""
import hashlib
import json
import shutil
from pathlib import Path
import unreal as u

P = Path(u.Paths.project_dir()).resolve()
O = Path(__file__).resolve().parent
if P != Path('D:/FPS3D/FPSGAME').resolve(): raise RuntimeError('Wrong project')
manifest = json.loads((O/'authored.json').read_text(encoding='utf-8'))
if not manifest.get('complete'): raise RuntimeError('Sprint authoring has not completed')
rows = list(manifest['clips'].values())
profiles = [spec for spec in json.loads((P/'SourceAssets/WeaponAnimationSharing20261001/manifest.json').read_text())['profiles']
    if spec['weapon'] == 'ue_m16a2']
roles = {'sprint_enter', 'sprint_loop', 'sprint_exit'}
headless = '-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
dirty = set()
if not headless:
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('End PIE before saving sprint animations')
    dirty = {package.get_name() for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}

def disk(asset_path):
    return P/'Content'/(asset_path.split('.')[0].removeprefix('/Game/')+'.uasset')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def backup(asset_path):
    package_name = asset_path.split('.')[0]
    if package_name in dirty: raise RuntimeError('Unsaved destination package '+package_name)
    file = disk(asset_path)
    target = O/'BeforePackages'/(package_name.removeprefix('/Game/')+'.uasset')
    target.parent.mkdir(parents=True, exist_ok=True)
    if file.exists() and not target.exists(): shutil.copy2(file, target)
    return str(target) if target.exists() else None

def load(path):
    asset = u.load_asset(path)
    if not asset: raise RuntimeError('Missing production asset '+path)
    return asset

def save(asset):
    if not u.EditorAssetLibrary.save_loaded_asset(asset, False):
        raise RuntimeError('Asset save failed '+asset.get_path_name())

receipt_path = O/'import-receipt.json'
receipt = {'revision': manifest['revision'], 'animations': {}, 'profiles': {},
    'complete': False, 'tested': False, 'rendered': False,
    'mesh_imported': False, 'skeleton_reference_modified': False,
    'non_sprint_profile_entries_refreshed': False}

def record():
    temp = receipt_path.with_suffix('.tmp')
    temp.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    temp.replace(receipt_path)

# Capture only the packages this production actually replaces.
backups = {row['asset']: backup(row['asset']) for row in rows}
backups.update({spec['asset']: backup(spec['asset']) for spec in profiles})
mesh = load('/Game/Weapons/M16A2/Gameplay20260919/SK_M16_Manny')
skeleton = mesh.get_editor_property('skeleton')
compression = load('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
tools = u.AssetToolsHelpers.get_asset_tools()
for row in rows:
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    options.import_mesh = False
    options.import_animations = True
    options.import_materials = False
    options.import_textures = False
    options.skeleton = skeleton
    options.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
    options.anim_sequence_import_data.set_editor_property('custom_sample_rate', 120)
    task = u.AssetImportTask()
    task.filename = row['file']
    task.destination_path = row['folder']
    task.destination_name = row['name']
    task.options = options
    task.automated = True
    task.replace_existing = True
    task.save = False
    tools.import_asset_tasks([task])
    imported = list(task.get_editor_property('imported_object_paths'))
    if row['asset'] not in {path.split('.')[0] for path in imported}:
        raise RuntimeError('Requested sprint asset was not imported: '+row['asset']+'; returned '+str(imported))
    clip = load(row['asset'])
    clip.set_editor_property('bone_compression_settings', compression)
    save(clip)
    receipt['animations'][row['family']+'/'+row['kind']] = {
        'asset': clip.get_path_name(), 'source': row['file'], 'imported_object_paths': imported,
        'saved': True, 'sha256': digest(disk(row['asset'])),
        'backup': backups[row['asset']]}
    record()
    print('M16_SPRINT_LEFT_CLIP_SAVED', row['family'], row['kind'], flush=True)

for spec in profiles:
    profile = load(spec['asset'])
    refreshed = []
    for pair in spec['pairs']:
        if pair['role'] not in roles: continue
        base, authored = load(pair['base']), load(pair['authored'])
        # BakeClip replaces only this Base's entry. Every other clip, metadata
        # field and Family remains in the existing saved profile object.
        if not profile.bake_clip(base, authored):
            raise RuntimeError('Cannot bake M16 sprint layer '+spec['family']+'/'+pair['role'])
        refreshed.append({'role': pair['role'], 'base': pair['base'], 'authored': pair['authored']})
    save(profile)
    receipt['profiles'][spec['family']] = {'asset': profile.get_path_name(),
        'refreshed': refreshed, 'saved': True,
        'sha256': digest(disk(spec['asset'])), 'backup': backups[spec['asset']]}
    record()
    print('M16_SPRINT_PROFILE_ENTRIES_SAVED', spec['family'], len(refreshed), flush=True)
receipt['complete'] = True
receipt['status'] = '18 animations and 15 sprint entries in 5 existing profiles imported and saved; user testing pending'
record()
u.log('M16_SPRINT_LEFT_COPY_INSTALL_COMPLETE '+str(len(receipt['animations']))+' '+str(len(receipt['profiles'])))
