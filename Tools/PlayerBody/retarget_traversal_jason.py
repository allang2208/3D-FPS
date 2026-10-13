"""Save full-body traversal clips using the existing GASP-to-Jason alignment."""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/ThirdPersonTraversal20261012'
DEST = '/Game/Characters/JasonPlayer20261003/TraversalGASP20261012/Animations'
donors = json.loads((OUT / 'donors.json').read_text(encoding='utf-8'))
config = json.loads((ROOT / 'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
lib = u.EditorAssetLibrary
source = u.load_asset('/Game/Characters/UEFN_Mannequin/Meshes/SKM_UEFN_Mannequin')
target = u.load_asset(config['body_mesh'])
retargeter = u.load_asset('/Game/Characters/JasonPlayer20261003/CrouchGASP20261005/Rig/RTG_GASP_Jason_Crouch')
if not source or not target or not retargeter:
    raise RuntimeError('Existing source mesh, Jason mesh or aligned retargeter is missing')
for path in donors['clips'].values():
    if lib.does_asset_exist(DEST + '/J_' + path.rsplit('/', 1)[1]):
        raise RuntimeError('Traversal output exists; preserving saved animation: ' + path)
inputs = u.IKRetargetBatchOperationInputs()
inputs.assets_to_retarget = [lib.find_asset_data(path) for path in donors['clips'].values()]
inputs.source_mesh = source
inputs.target_mesh = target
inputs.ik_retarget_asset = retargeter
inputs.prefix = 'J_'
inputs.target_path = DEST
inputs.include_referenced_assets = False
inputs.overwrite_existing_files = False
outputs = u.IKRetargetBatchOperation.run_batch_retarget(inputs)
roles = {path.rsplit('/', 1)[1]: role for role, path in donors['clips'].items()}
# Contact and release match the first-person source phases. Vault's long
# descending tail is deliberately excluded; gameplay owns falling/landing.
ranges = {'Vault': (.27, .58, .8), 'Mantle': (.345, 1.1, 2.), 'Climb': (.74, 2.25, 3.333333333)}
saved, durations = {}, {}
for data in outputs:
    clip = data.get_asset()
    if not isinstance(clip, u.AnimSequence):
        continue
    role = roles[clip.get_name().removeprefix('J_')]
    clip.set_preview_skeletal_mesh(target)
    clip.set_editor_property('enable_root_motion', False)
    clip.set_editor_property('force_root_lock', True)
    clip.set_editor_property('root_motion_root_lock', u.RootMotionRootLock.REF_POSE)
    u.AnimationLibrary.remove_all_animation_sync_markers(clip)
    u.AnimationLibrary.add_animation_notify_track(clip, 'TraversalTiming')
    for marker, time in zip(('TraversalContact', 'TraversalRelease', 'TraversalExit'), ranges[role]):
        u.AnimationLibrary.add_animation_sync_marker(clip, marker, min(time, clip.get_play_length()), 'TraversalTiming')
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):
        raise RuntimeError('Animation finalization failed: ' + role)
    if not lib.save_loaded_asset(clip, False):
        raise RuntimeError('Animation save failed: ' + role)
    saved['Traversal.' + role] = clip.get_path_name()
    durations[role] = clip.get_play_length()
if len(saved) != len(roles):
    raise RuntimeError('Retarget did not produce all three traversal clips')
(OUT / 'assets-saved.json').write_text(json.dumps({
    'retargeter': retargeter.get_path_name(), 'target': target.get_path_name(),
    'runtime_clips': saved, 'durations': durations, 'source_phases': ranges,
}, indent=2), encoding='utf-8')
print('TRAVERSAL_ASSETS_SAVED ' + json.dumps(saved))
