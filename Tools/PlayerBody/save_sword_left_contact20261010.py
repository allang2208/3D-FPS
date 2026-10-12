"""Save the two overhead takes with the upper left grip seated on the handle."""
import hashlib
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/ThirdPersonSwordLeftContact20261010'
DEST = '/Game/Characters/JasonPlayer20261003/KwangSwordLeftContact20261010/Animations'
# New, unreferenced packages can be authored in the existing editor while PIE
# continues using its old clips. Never rewrite a revision already configured.
configured = json.loads((ROOT / 'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
if u.EditorLevelLibrary.get_pie_worlds(True) and any(
    path.startswith(DEST + '/') for path in configured['clips'].values()):
    raise RuntimeError('This revision is active; exit PIE before rewriting it.')
data = json.loads((OUT / 'candidate-actions.json').read_text())
source_hash = hashlib.sha256((OUT / 'candidate-actions.json').read_bytes()).hexdigest()
lib = u.EditorAssetLibrary
mesh = u.load_asset(data['mesh'])
factory = u.AnimSequenceFactory()
factory.set_editor_property('target_skeleton', mesh.skeleton)
factory.set_editor_property('preview_skeletal_mesh', mesh)
receipt = dict(clips={}, complete=False, source_hash=source_hash,
               accepted_arms_sha256=data['accepted_arms_sha256'], source_url=data['source_url'])
for label, take in data['clips'].items():
    name = 'J_Kwang_' + label
    path = DEST + '/' + name
    clip = u.load_asset(path) if lib.does_asset_exist(path) else None
    if clip:
        if lib.get_metadata_tag(clip, 'GripSourceHash') != source_hash:
            raise RuntimeError('Hand-pose package belongs to another source: ' + path)
    else:
        clip = u.AssetToolsHelpers.get_asset_tools().create_asset(name, DEST, u.AnimSequence, factory)
        ctl = clip.get_editor_property('controller')
        frames = take['frames']
        ctl.open_bracket('Seat upper left grip below handle rim: ' + label, False)
        try:
            ctl.set_frame_rate(u.FrameRate(take['rate'], 1), False)
            ctl.set_number_of_frames(u.FrameNumber(len(frames) - 1), False)
            for j, bone in enumerate(data['names']):
                ctl.add_bone_curve(bone, False)
                keys = [f[j] for f in frames]
                if not ctl.set_bone_track_keys(bone, [u.Vector(*t[:3]) for t in keys],
                    [u.Quat(*t[3:7]) for t in keys], [u.Vector(*t[7:]) for t in keys], False):
                    raise RuntimeError('Cannot write ' + bone)
        finally:
            ctl.close_bracket(False)
        for curve, values in take['curves'].items():
            u.AnimationLibrary.add_curve(clip, curve)
            u.AnimationLibrary.add_float_curve_keys(clip, curve, [i / take['rate'] for i in range(len(values))], values)
        clip.set_preview_skeletal_mesh(mesh)
        clip.set_editor_property('enable_root_motion', False)
        clip.set_editor_property('force_root_lock', True)
        clip.set_editor_property('root_motion_root_lock', u.RootMotionRootLock.REF_POSE)
        u.AnimationLibrary.add_animation_notify_track(clip, 'SwordTiming')
        for marker, fraction in [('Contact', take['contact']), ('Release', take['release']), ('NativeSwordGrip', 0.)]:
            u.AnimationLibrary.add_animation_sync_marker(clip, marker, fraction * clip.get_play_length(), 'SwordTiming')
        for key, value in dict(ThirdPersonSource=data['provenance'], SourceAnimation=take['source'],
            SourceURL=data['source_url'], SourceRange=json.dumps(take['source_range']),
            AuthoringScript='SourceAssets/ThirdPersonSwordLeftContact20261010/author_left_contact.py',
            GripRevision='20261010-upper-left-contact-seated', GripSourceHash=source_hash,
            AcceptedArmsHash=data['accepted_arms_sha256'],
            FingerOwnership='SwordSupportThumb: left thumb subtree only; runtime equipment retains other digits').items():
            lib.set_metadata_tag(clip, key, value)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):
        raise RuntimeError('Cannot finalize ' + path)
    if not lib.save_loaded_asset(clip, False):
        raise RuntimeError('Cannot save ' + path)
    receipt['clips']['Melee.FullBody.' + label] = clip.get_path_name()
    (OUT / 'assets-saved.json').write_text(json.dumps(receipt, indent=2))
    print('SWORD_LEFT_CONTACT_SAVED ' + clip.get_path_name())
receipt['complete'] = True
(OUT / 'assets-saved.json').write_text(json.dumps(receipt, indent=2))
print('SWORD_LEFT_CONTACT_SAVE_COMPLETE')
