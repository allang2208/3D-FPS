"""Save two new single-dash sequences without touching the dual branch."""
import hashlib
import json
import runpy
from pathlib import Path
import unreal as u

OUT = Path(__file__).resolve().parent
TAG = 'SourceAssets/KukriDashFreeArm20261028/author.py'
lib = u.EditorAssetLibrary
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    level = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():
        raise RuntimeError('Active PIE: prepared free-arm assets were not modified. End play before saving.')
runpy.run_path(str(OUT / 'read_installed.py'))
receipt = dict(complete=False, bodies={}, runtime_tested=False)
readback = dict(bodies={}, evaluation='SOURCE', runtime_tested=False)
for label in ('jason', 'kaitlin'):
    raw = (OUT / (label + '-actions.json')).read_bytes()
    data = json.loads(raw)
    source = data['clips']['Dash']
    mesh = u.load_asset(data['mesh'])
    name = 'A_Kukri_Dash_FreeArm'
    folder = '/Game/Characters/JasonPlayer20261003/Kukri20261024/ComboV3/' + label.capitalize() + '/Animations/DashFreeArmV4'
    path = folder + '/' + name
    if lib.does_asset_exist(path):
        clip = u.load_asset(path)
        if lib.get_metadata_tag(clip, 'AuthoringScript') != TAG:
            raise RuntimeError('Existing candidate has another owner: ' + path)
    else:
        factory = u.AnimSequenceFactory()
        factory.target_skeleton = mesh.skeleton
        factory.preview_skeletal_mesh = mesh
        clip = u.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, u.AnimSequence, factory)
        lib.set_metadata_tag(clip, 'AuthoringScript', TAG)
    clip.set_retarget_source_asset(mesh)
    clip.update_retarget_source_asset_data()
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):
        raise RuntimeError('Initialize failed: ' + path)
    ctl = clip.get_editor_property('controller')
    tracks = {str(n).casefold() for n in u.AnimationLibrary.get_animation_track_names(clip)}
    ctl.open_bracket('Single dash native free-arm backswing', False)
    try:
        ctl.set_frame_rate(u.FrameRate(source['rate_num'], source['rate_den']), False)
        ctl.set_number_of_frames(u.FrameNumber(len(source['frames']) - 1), False)
        for i, bone in enumerate(data['names']):
            if bone.casefold() not in tracks:
                ctl.add_bone_curve(bone, False)
            rows = [frame[i] for frame in source['frames']]
            if not ctl.set_bone_track_keys(bone, [u.Vector(*x[:3]) for x in rows],
                    [u.Quat(*x[3:7]) for x in rows], [u.Vector(*x[7:]) for x in rows], False):
                raise RuntimeError('Track write failed: ' + bone)
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):
            raise RuntimeError('Track finalization failed: ' + path)
    finally:
        ctl.close_bracket(False)
    clip.set_preview_skeletal_mesh(mesh)
    clip.set_editor_property('enable_root_motion', False)
    clip.set_editor_property('force_root_lock', True)
    clip.set_editor_property('root_motion_root_lock', u.RootMotionRootLock.REF_POSE)
    if 'KukriDashTiming' not in {str(n) for n in u.AnimationLibrary.get_animation_notify_track_names(clip)}:
        u.AnimationLibrary.add_animation_notify_track(clip, 'KukriDashTiming')
    markers = {str(m.marker_name) for m in u.AnimationLibrary.get_animation_sync_markers(clip)}
    for marker, fraction in [('Contact', source['contact']), ('Release', source['release']), ('NativeSwordGrip', 0.)]:
        if marker not in markers:
            u.AnimationLibrary.add_animation_sync_marker(clip, marker, fraction * clip.get_play_length(), 'KukriDashTiming')
    for key, value in dict(AuthoringScript=TAG, SourceAnimation=source['source'], Adaptation=source['adaptation'],
            SourceLicense='Existing project animation sources; original licensing retained').items():
        lib.set_metadata_tag(clip, key, value)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip) or not lib.save_loaded_asset(clip, False):
        raise RuntimeError('Sequence was not saved: ' + path)
    receipt['bodies'][label] = dict(mesh=mesh.get_path_name(), clips={'Kukri.FullBody.Dash': clip.get_path_name()},
        source_sha256=hashlib.sha256(raw).hexdigest())
    options = u.AnimPoseEvaluationOptions()
    options.optional_skeletal_mesh = mesh
    options.evaluation_type = u.AnimDataEvalType.SOURCE
    samples = {}
    for t in [.2, .4, .55, .7, .9]:
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, t, options)
        row = {}
        for bone in ['clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l']:
            x = u.AnimPoseExtensions.get_bone_pose(pose, bone, u.AnimPoseSpaces.LOCAL)
            row[bone] = [x.rotation.x, x.rotation.y, x.rotation.z, x.rotation.w]
        samples[str(t)] = row
    readback['bodies'][label] = dict(asset=clip.get_path_name(), duration=clip.get_play_length(), frames=samples)
    (OUT / 'saved-samples.json').write_text(json.dumps(readback, indent=2))
    (OUT / 'assets-saved.json').write_text(json.dumps(receipt, indent=2))
    print('SINGLE_FREE_ARM_SAVED ' + clip.get_path_name(), flush=True)
receipt['complete'] = True
(OUT / 'assets-saved.json').write_text(json.dumps(receipt, indent=2))
print('SINGLE_FREE_ARM_SAVE_COMPLETE', flush=True)
