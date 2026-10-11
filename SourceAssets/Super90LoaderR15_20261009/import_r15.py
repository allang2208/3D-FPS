"""Save R15 rhythm in 15 loader clips and the loader entries of four grip profiles.

Unreal Python (commandlet or MCP bridge). The idle, quick-melee, sprint and all
other profile entries and retained overrides are preserved. No PIE, render or
validation test is run here.
"""
import json, shutil, hashlib
from pathlib import Path
import unreal as u

subsystem = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if subsystem and subsystem.get_game_world():
    raise RuntimeError('Exit PIE before replacing Super90 loader assets; no assets changed.')

O = Path(__file__).parent; P = O.parents[1]
ROOT = '/Game/Weapons/Super90/Speedloader20261007'; ANIM = ROOT + '/Animations'
E = u.EditorAssetLibrary; A = u.AssetToolsHelpers.get_asset_tools(); L = u.MaterialEditingLibrary
manifest = json.loads((O / 'authoring.json').read_text(encoding='utf-8'))
if manifest['revision'] != 'LoaderR15-20261009': raise RuntimeError('Run author_r15.py before this import.')
receipt = {'completed': False, 'revision': manifest['revision'], 'saved': [], 'profiles': {}, 'package_sha256': {}, 'runtime_tested': False}
def record(): (O / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
def load(path):
    obj = u.load_asset(path)
    if not obj: raise RuntimeError('Missing ' + path)
    return obj
def backup(path):
    rel = path.split('.')[0].removeprefix('/Game/') + '.uasset'
    src = P / 'Content' / rel; dst = O / 'Before' / 'Content' / rel
    if src.exists() and not dst.exists(): dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, dst)
    receipt['package_sha256'].setdefault(path.split('.')[0], {})['before'] = hashlib.sha256(src.read_bytes()).hexdigest() if src.exists() else None
def save(obj):
    if not E.save_loaded_asset(obj, False): raise RuntimeError('Save failed ' + obj.get_path_name())
    if obj.get_path_name() not in receipt['saved']: receipt['saved'].append(obj.get_path_name())
    package = obj.get_path_name().split('.')[0]
    file = P / 'Content' / (package.removeprefix('/Game/') + '.uasset')
    receipt['package_sha256'].setdefault(package, {})['after'] = hashlib.sha256(file.read_bytes()).hexdigest()
    record(); return obj
def tag(obj, file):
    E.set_metadata_tag(obj, 'Super90SpeedloaderSource', manifest['revision'] + '; R15 preserved accepted R14 full push; only source time remapped; measured reference camera')
    E.set_metadata_tag(obj, 'Super90SourceSHA256', hashlib.sha256(Path(file).read_bytes()).hexdigest())

families = ('vertical', 'canted', 'prism', 'angled')
profile_paths = {f: '/Game/Weapons/Super90/Foregrips20261007/Profiles/DA_Super90_' + f for f in families}
targets = {ANIM + '/' + c['name'] for c in manifest['clips']}
targets.update(profile_paths.values())
audio_recipe=json.loads((O/'audio_provenance.json').read_text(encoding='utf-8'))
targets.update(row['asset'] for row in audio_recipe['audio'])


# An existing editor may have unsaved manual work. Refuse only an actual overlap;
# the shared bridge owns the import batch, and other packages stay untouched.
conflicts = [p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
             if p.get_path_name() in targets]
if conflicts:
    raise RuntimeError('Unsaved target packages; preserving current work: ' + ', '.join(conflicts))
for clip in manifest['clips']: backup(ANIM + '/' + clip['name'])
for path in profile_paths.values(): backup(path)

skeleton = load('/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7').skeleton
compression = load('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
flag = 'Interchange.FeatureFlags.Import.FBX'; previous = u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None, flag + ' 0')
def task_for(file, name, dest, opt):
    t = u.AssetImportTask(); t.filename = str(file); t.destination_name = name; t.destination_path = dest
    t.automated = True; t.replace_existing = True; t.replace_existing_settings = True; t.save = False
    t.factory = u.FbxFactory(); t.options = opt; A.import_asset_tasks([t])
    if not t.imported_object_paths: raise RuntimeError('FBX import failed ' + name)
try:
    for clip in manifest['clips']:
        opt = u.FbxImportUI(); opt.automated_import_should_detect_type = False; opt.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
        opt.import_mesh = False; opt.import_as_skeletal = False; opt.import_animations = True; opt.import_materials = False; opt.import_textures = False
        opt.create_physics_asset = False; opt.skeleton = skeleton
        opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
        opt.anim_sequence_import_data.set_editor_property('custom_sample_rate', 60)
        task_for(clip['file'], clip['name'], ANIM, opt)
        obj = load(ANIM + '/' + clip['name']); obj.set_editor_property('bone_compression_settings', compression)
        tag(obj, clip['file']); save(obj)
finally:
    u.SystemLibrary.execute_console_command(None, flag + ' ' + str(previous))

def snapshot_other_clips(asset, family):
    payload = {'family': family, 'clips': []}; retained = {}
    for clip in asset.get_editor_property('clips'):
        base = clip.get_editor_property('base').get_path_name()
        if base.startswith(ANIM + '/'): continue          # only the loader entries are replaced
        payload['clips'].append({'base': base, 'duration': float(clip.get_editor_property('duration')), 'tracks': [
            {'bone': str(t.get_editor_property('bone')), 'times': list(t.get_editor_property('times')), 'values': list(t.get_editor_property('values'))}
            for t in clip.get_editor_property('tracks')]})
        original = clip.get_editor_property('retained')
        if original: retained[base] = original.get_path_name()
    return payload, retained

for family, path in profile_paths.items():
    asset = load(path); combined, retained = snapshot_other_clips(asset, family)
    kept = len(combined['clips'])
    combined['clips'].extend(json.loads((O / (family + '_profiles.json')).read_text(encoding='utf-8'))['clips'])
    if not asset.set_shared_clips_from_json(json.dumps(combined)): raise RuntimeError('Grip extension failed ' + family)
    if retained:
        rows = list(asset.get_editor_property('clips'))
        for i, row in enumerate(rows):
            base = row.get_editor_property('base').get_path_name()
            if base in retained: row.set_editor_property('retained', load(retained[base])); rows[i] = row
        asset.set_editor_property('clips', rows)
    E.set_metadata_tag(asset, 'Super90SpeedloaderGrip', manifest['revision'] + '; loader entries replaced; idle, melee, sprint and other entries retained')
    save(asset); receipt['profiles'][family] = {'path': path, 'kept_clips': kept, 'clip_count': len(combined['clips'])}; record()
audio_script=O/'import_audio.py'
exec(compile(audio_script.read_text(encoding='utf-8'),str(audio_script),'exec'),
     {'__file__':str(audio_script),'__name__':'__main__'})
receipt['audio_receipt']=str(O/'audio_import_receipt.json')
receipt['completed'] = True; record()
print('SUPER90_LOADER_R15_SAVED', len(receipt['saved']), 'assets; no gameplay test', flush=True)
