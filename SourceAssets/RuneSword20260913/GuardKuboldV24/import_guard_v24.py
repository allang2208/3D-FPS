"""Install guard V24 (Guard / GuardHit / GuardBreak, Standard + LongGrip) with an UnrealEditor-Cmd pythonscript run.

Run through run_import.ps1 (asset-batch mutex, refuses while an FPSGAME editor/commandlet on this project is active).
- Guard: the raise starts from the installed idle of each folder (start-only handoff, the same solver as the V85
  inspect import, SwordIdleClose20260926 helpers); the 2.05 s breathing hold is left exactly as authored so the
  runtime loop is seamless. GuardHit / GuardBreak start and end on authored hold / stunned poses: no handoff.
- DA_Sword_LongGrip: an existing entry whose Base is one of the three Standard clips is rebaked against the new
  LongGrip clip (or kept as a Retained entry if it was one). Clips without an entry keep loading their LongGrip asset.
- Refuses to overwrite a target that changed since the hashes read on 2026-11-22 (V23, see BASELINE).
- Backups, final FBX, handoff keys and the receipt go to the batch directory on F:
  F:/FPSGAMEData/ArtProduction/RuneSword20260913/GuardKuboldV24/Install-20261122/
"""
import ast
import hashlib
import json
import math  # noqa: F401  (used by the exec'd SwordIdleClose helpers)
import shutil
from pathlib import Path

import unreal as u

P = Path(__file__).resolve().parent
ROOT = Path(u.Paths.project_dir()).resolve()
BATCH = Path('F:/FPSGAMEData/ArtProduction/RuneSword20260913/GuardKuboldV24/Install-20261122')
REVISION = 'GuardKuboldV24'
IDLE_SOURCE = ROOT / 'SourceAssets/SwordIdleClose20260926'
tree = ast.parse((IDLE_SOURCE / 'author_idle_close.py').read_text(encoding='utf-8'))
helpers = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name not in ('sample', 'asset_path')]
exec(compile(ast.Module(body=helpers, type_ignores=[]), 'supported_idle_math', 'exec'), globals())
IDENTITY = {'p': (0, 0, 0), 'q': (0, 0, 0, 1), 's': (1, 1, 1)}
STANDARD = '/Game/Weapons/AzureRunesword20260913'
LONG = '/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations'
PROFILE = '/Game/Weapons/AnimationProfiles20261001/Melee/DA_Sword_LongGrip'
CLIPS = ('Guard', 'GuardHit', 'GuardBreak')
TARGETS = [(v, folder, clip, (P / 'Export' / sub / f'A_RuneSword_{clip}.fbx'))
           for v, folder, sub in (('Standard', STANDARD, ''), ('LongGrip', LONG, 'LongGrip')) for clip in CLIPS]
# Installed V23 packages, read 2026-11-22 before this install.
BASELINE = {
    ('Standard', 'Guard'): 'c5d403d5cdd8b3fee980adbefa50abea3b9a8a0e60d1470501580f77eda0ad2d',
    ('Standard', 'GuardHit'): 'f8c712177d70d0b7a983ede18e3ec420deb1ee0a24d3be98b99c0fc0a7bae85a',
    ('Standard', 'GuardBreak'): '14436e13f49406bec222a20e6e76bd866e3f18e13dfbb6985c03ed369a886ee7',
    ('LongGrip', 'Guard'): 'b9a3b0ca91a99a5f0790a8e1c837890283e2679d0d72c6a54a4a99ad1e2e9ab4',
    ('LongGrip', 'GuardHit'): '02e24b6cb7d662b4fa5b0cfe729246e239df86a1a34290e891314257138aadc9',
    ('LongGrip', 'GuardBreak'): '53093869cff2ad767c7c5ecff2a30b7e1315aea71b7227f6af269600e86ab7cc',
}
PROFILE_BASELINE = 'ac702f2c362798a99c245fc54565e5e6de64107c051880447a390f48ee859ac6'


def disk_of(path):
    return ROOT / 'Content' / (path.removeprefix('/Game/') + '.uasset')


def sha(path):
    return hashlib.sha256(disk_of(path).read_bytes()).hexdigest()


dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
mesh = u.load_asset('/Game/Weapons/AzureRunesword20260913/SK_AzureRunesword_Manny')
component = u.SkeletalMeshComponent()
component.set_skeletal_mesh_asset(mesh)
names = [str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
parents = {n: str(component.get_parent_bone(n)) for n in names}
edited = [n for n in names if n == 'WPN_root' or any(n == stem + '_' + side for side in ('r', 'l') for stem in
          ('upperarm', 'lowerarm', 'hand', 'upperarm_twist_01', 'upperarm_twist_02', 'lowerarm_twist_01', 'lowerarm_twist_02'))]
needed = list(dict.fromkeys(edited + [parents[n] for n in edited if parents[n] != 'None']))
options = u.AnimPoseEvaluationOptions()
options.evaluation_type = u.AnimDataEvalType.SOURCE
options.optional_skeletal_mesh = mesh


def sample(sequence, t):
    pose = u.AnimPoseExtensions.get_anim_pose_at_time(sequence, t, options)
    world = {n: unpack(u.AnimPoseExtensions.get_bone_pose(pose, n, u.AnimPoseSpaces.WORLD)) for n in needed}
    local = {n: unpack(u.AnimPoseExtensions.get_bone_pose(pose, n, u.AnimPoseSpaces.LOCAL)) for n in edited}
    return world, local
def start_handoff(sequence, idle, variant):
    """Frame 0 becomes the folder's installed idle; the offset fades over the first 0.20 s while the pose is still
    near idle (proximity weight). The hold section is not touched."""
    source_idle, _ = sample(sequence, 0)
    target_idle, target_keys = sample(idle, 0)
    offset = sub(target_idle['WPN_root']['p'], source_idle['WPN_root']['p'])
    frames = sequence.get_editor_property('data_model_interface').get_number_of_frames()
    seconds = sequence.get_play_length()
    rows, previous, touched = [], {}, 0
    for frame in range(frames + 1):
        t = frame * seconds / frames
        world, local = sample(sequence, t)
        weight = (1 - smooth(t / .20)) * proximity(world, source_idle)
        keys = {n: dict(k) for n, k in local.items()}
        if weight > 1e-6:
            touched = frame
            desired, _ = solve_pose(world, mul(offset, weight), weight, parents, edited)
            for n in edited:
                keys[n] = relative(desired[n], desired.get(parents[n], IDENTITY))
                keys[n]['s'] = local[n]['s']
        if frame == 0:
            keys = {n: dict(k) for n, k in target_keys.items()}
        for n, k in keys.items():
            if n in previous and dot(k['q'], previous[n]) < 0:
                k['q'] = mul(k['q'], -1)
            previous[n] = k['q']
        rows.append({'seconds': t, 'posture_weight': weight, 'bones': keys})
    controller = sequence.get_editor_property('controller')
    controller.open_bracket('Guard V24 raise starts from the installed idle', False)
    try:
        for n in edited:
            keys = [r['bones'][n] for r in rows]
            if not controller.set_bone_track_keys(n, [u.Vector(*k['p']) for k in keys],
                                                  [u.Quat(*k['q']) for k in keys], [u.Vector(*k['s']) for k in keys], False):
                raise RuntimeError('Could not write handoff track ' + n)
    finally:
        controller.close_bracket(False)
    out = BATCH / 'Final' / variant
    out.mkdir(parents=True, exist_ok=True)
    keys_file = out / 'Guard_idle_handoff_keys.json'
    keys_file.write_text(json.dumps({'asset': sequence.get_path_name(), 'revision': REVISION, 'frames': frames,
                                     'seconds': seconds, 'offset_cm': offset, 'edited_bones': edited,
                                     'last_blended_frame': touched, 'samples': rows[:touched + 2]},
                                    separators=(',', ':')), encoding='utf-8')
    export = u.AssetExportTask()
    export.object = sequence
    export.filename = str(out / 'A_RuneSword_Guard.fbx')
    export.automated = True
    export.prompt = False
    export.replace_identical = True
    export.options = u.FbxExportOption()
    if not u.Exporter.run_asset_export_task(export):
        raise RuntimeError('Final FBX export failed')
    import_data = sequence.get_editor_property('asset_import_data')
    if import_data:
        import_data.scripted_add_filename(export.filename, 0, 'Guard V24 with the installed idle at the start')
    return {'frames': frames, 'seconds': seconds, 'idle_offset_cm': offset, 'last_blended_frame': touched,
            'full_fbx': export.filename, 'handoff_keys': str(keys_file)}


def profile_entries(profile):
    rows = []
    for clip in profile.get_editor_property('clips'):
        base, kept = clip.get_editor_property('base'), clip.get_editor_property('retained')
        rows.append({'base': base.get_path_name() if base else None, 'retained': kept.get_path_name() if kept else None,
                     'duration': float(clip.get_editor_property('duration')),
                     'tracks': [str(t.get_editor_property('bone')) for t in clip.get_editor_property('tracks')]})
    return rows
BATCH.mkdir(parents=True, exist_ok=True)
receipt_path = BATCH / 'import_receipt.json'
receipt = json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else {
    'revision': REVISION, 'author_source': str(P), 'assets': [], 'profile': None, 'runtime_tested': False}
saved = {(r['variant'], r['clip']): r for r in receipt['assets'] if r.get('saved')}
for variant, folder, clip, source in TARGETS:
    path = folder + '/A_RuneSword_' + clip
    if path in dirty:
        raise RuntimeError('Unsaved target retained: ' + path)
    if not source.exists():
        raise RuntimeError('Missing authored FBX ' + str(source))
    if not u.load_asset(path):
        raise RuntimeError('Installed clip missing: ' + path)
    digest = sha(path)
    if (variant, clip) in saved:
        if digest != saved[(variant, clip)]['after_sha256']:
            raise RuntimeError('Saved V24 changed since; retained: ' + path)
    elif digest != BASELINE[(variant, clip)]:
        raise RuntimeError('Guard clip changed since 2026-11-22; retained: ' + path)
if PROFILE in dirty:
    raise RuntimeError('Unsaved profile retained: ' + PROFILE)
profile_digest = sha(PROFILE)
if receipt['profile'] is None and profile_digest != PROFILE_BASELINE:
    raise RuntimeError('DA_Sword_LongGrip changed since 2026-11-22; retained')

flag = 'Interchange.FeatureFlags.Import.FBX'
previous_flag = u.SystemLibrary.get_console_variable_int_value(flag)
try:
    u.SystemLibrary.execute_console_command(None, flag + ' 0')
    for variant, folder, clip, source in TARGETS:
        if (variant, clip) in saved:
            continue
        path = folder + '/A_RuneSword_' + clip
        current = u.load_asset(path)
        before_hash = sha(path)
        backup = BATCH / 'Before' / variant / ('A_RuneSword_' + clip + '.uasset')
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            shutil.copy2(disk_of(path), backup)
        compression = current.get_editor_property('bone_compression_settings')
        before_length = current.get_play_length()
        ui = u.FbxImportUI()
        ui.automated_import_should_detect_type = False
        ui.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
        ui.import_mesh = False
        ui.import_animations = True
        ui.import_materials = False
        ui.import_textures = False
        ui.skeleton = mesh.skeleton
        ui.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
        ui.anim_sequence_import_data.set_editor_property('custom_sample_rate', 120)
        task = u.AssetImportTask()
        task.filename = str(source)
        task.destination_path = folder
        task.destination_name = 'A_RuneSword_' + clip
        task.automated = True
        task.replace_existing = True
        task.save = False
        task.options = ui
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        sequence = u.load_asset(path)
        if not task.imported_object_paths or not sequence:
            raise RuntimeError('Import failed ' + path)
        if compression:
            sequence.set_editor_property('bone_compression_settings', compression)
        authored = {'frames': sequence.get_editor_property('data_model_interface').get_number_of_frames(),
                    'seconds': sequence.get_play_length(), 'handoff': 'none (authored hold / stunned poses)'}
        if clip == 'Guard':
            authored = start_handoff(sequence, u.load_asset(folder + '/A_RuneSword_Idle'), variant)
            authored['handoff'] = 'start only (installed idle at frame 0, faded by 0.20 s)'
        sequence.modify()
        if not u.EditorLoadingAndSavingUtils.save_packages([sequence.get_package()], False):
            raise RuntimeError('Could not save ' + path)
        receipt['assets'].append({'variant': variant, 'clip': clip, 'asset': path, 'author_fbx': str(source),
                                  'backup': str(backup), 'saved': True, 'before_seconds': before_length,
                                  'before_sha256': before_hash, 'after_sha256': sha(path), **authored})
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
        print('GUARD_V24_SAVED', variant, clip, path, flush=True)
finally:
    u.SystemLibrary.execute_console_command(None, flag + ' ' + str(previous_flag))

# Long-grip profile: rebake only the entries that already exist for these three Standard clips.
if receipt['profile'] is None:
    profile = u.load_asset(PROFILE)
    before_rows = profile_entries(profile)
    backup = BATCH / 'Before' / 'DA_Sword_LongGrip.uasset'
    if not backup.exists():
        shutil.copy2(disk_of(PROFILE), backup)
    changes = []
    for clip in CLIPS:
        base = u.load_asset(STANDARD + '/A_RuneSword_' + clip)
        authored = u.load_asset(LONG + '/A_RuneSword_' + clip)
        row = next((r for r in before_rows if r['base'] == base.get_path_name()), None)
        if row is None:
            changes.append({'clip': clip, 'action': 'none (no entry; LongGrip loads its own asset)'})
        elif row['retained']:
            profile.keep_clip(base, u.load_asset(row['retained'].split('.')[0]))
            changes.append({'clip': clip, 'action': 'kept retained ' + row['retained']})
        else:
            if not profile.bake_clip(base, authored):
                raise RuntimeError('Could not bake long-grip ' + clip)
            changes.append({'clip': clip, 'action': 'rebaked', 'seconds': base.get_play_length()})
    after_rows = profile_entries(profile)
    if any(not c['action'].startswith('none') for c in changes):
        if not u.EditorLoadingAndSavingUtils.save_packages([profile.get_package()], False):
            raise RuntimeError('Could not save ' + PROFILE)
    receipt['profile'] = {'asset': PROFILE, 'backup': str(backup), 'before_sha256': profile_digest,
                          'after_sha256': sha(PROFILE), 'changes': changes,
                          'entries_before': [r for r in before_rows if r['base'] and r['base'].split('/')[-1].split('.')[0] in
                                             ['A_RuneSword_' + c for c in CLIPS]],
                          'entries_after': [r for r in after_rows if r['base'] and r['base'].split('/')[-1].split('.')[0] in
                                            ['A_RuneSword_' + c for c in CLIPS]]}
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('GUARD_V24_PROFILE', json.dumps(changes), flush=True)
receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('GUARD_V24_COMPLETE', len(receipt['assets']), flush=True)
