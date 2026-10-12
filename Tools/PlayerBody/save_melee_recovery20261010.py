"""Save independent recovery assets, leaving both V2 and V3 packages intact."""
import hashlib
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT/'SourceAssets/ThirdPersonMeleeRegression20261010'
DEST = '/Game/Characters/JasonPlayer20261003/KwangSwordRecovery20261010/Animations'
if u.EditorLevelLibrary.get_pie_worlds(True):
    raise RuntimeError('Exit PIE before saving the recovered Kwang animations.')
data = json.loads((OUT/'adapted-actions.json').read_text())
source_hash = hashlib.sha256((OUT/'adapted-actions.json').read_bytes()).hexdigest()
lib = u.EditorAssetLibrary
mesh = u.load_asset(data['mesh'])
factory = u.AnimSequenceFactory()
factory.set_editor_property('target_skeleton', mesh.skeleton)
factory.set_editor_property('preview_skeletal_mesh', mesh)
receipt = dict(clips={}, complete=False, source_hash=source_hash,
               accepted_source_hash=data['recovery_source_sha256'], source_url=data['source_url'])
for label, c in data['clips'].items():
    name = 'J_Kwang_' + label.replace('.', '_')
    clip = u.load_asset(DEST+'/'+name) if lib.does_asset_exist(DEST+'/'+name) else None
    if clip:
        if lib.get_metadata_tag(clip, 'GripSourceHash') != source_hash:
            raise RuntimeError('Recovery package belongs to another source: '+clip.get_path_name())
    else:
        clip = u.AssetToolsHelpers.get_asset_tools().create_asset(name, DEST, u.AnimSequence, factory)
        ctl = clip.get_editor_property('controller')
        frames = c['frames']
        ctl.open_bracket('Recover accepted Kwang arm chain '+label, False)
        try:
            ctl.set_frame_rate(u.FrameRate(c['rate'], 1), False)
            ctl.set_number_of_frames(u.FrameNumber(len(frames)-1), False)
            for j, bone in enumerate(data['names']):
                ctl.add_bone_curve(bone, False)
                keys = [f[j] for f in frames]
                if not ctl.set_bone_track_keys(bone, [u.Vector(*t[:3]) for t in keys],
                    [u.Quat(*t[3:7]) for t in keys], [u.Vector(*t[7:]) for t in keys], False):
                    raise RuntimeError('Cannot write '+bone)
        finally:
            ctl.close_bracket(False)
        u.AnimationLibrary.add_curve(clip, 'SwordGripRoll')
        u.AnimationLibrary.add_float_curve_keys(clip, 'SwordGripRoll',
            [0., (len(frames)-1)/c['rate']], [0., 0.])
        clip.set_preview_skeletal_mesh(mesh)
        clip.set_editor_property('enable_root_motion', False)
        clip.set_editor_property('force_root_lock', True)
        clip.set_editor_property('root_motion_root_lock', u.RootMotionRootLock.REF_POSE)
        u.AnimationLibrary.add_animation_notify_track(clip, 'SwordTiming')
        for marker, fraction in [('Contact', c['contact']), ('Release', c['release']), ('NativeSwordGrip', 0.)]:
            u.AnimationLibrary.add_animation_sync_marker(clip, marker, fraction*clip.get_play_length(), 'SwordTiming')
        for key, value in dict(ThirdPersonSource=data['provenance'], SourceAnimation=c['source'],
            SourceURL=data['source_url'], SourceRange=json.dumps(c['source_range']),
            AuthoringScript='SourceAssets/ThirdPersonMeleeRegression20261010/restore_accepted_arms.py',
            GripRevision='20261010-accepted-arm-recovery', GripSourceHash=source_hash,
            AcceptedSourceHash=data['recovery_source_sha256'],
            GripCurve='SwordGripRoll: zero; accepted fixed grip frame',
            BladeConvention='Accepted Kwang V2 blade frame and body timing preserved').items():
            lib.set_metadata_tag(clip, key, value)
    # NotifyPopulated also synchronizes compressed sampling with authored 60 Hz.
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):
        raise RuntimeError('Cannot finalize '+clip.get_path_name())
    if not lib.save_loaded_asset(clip, False):
        raise RuntimeError('Cannot save '+clip.get_path_name())
    receipt['clips']['Melee.FullBody.'+label] = clip.get_path_name()
    (OUT/'assets-saved.json').write_text(json.dumps(receipt, indent=2))
    print('KWANG_RECOVERY_SAVED '+clip.get_path_name())
receipt['complete'] = True
(OUT/'assets-saved.json').write_text(json.dumps(receipt, indent=2))
print('KWANG_RECOVERY_SAVE_COMPLETE')
