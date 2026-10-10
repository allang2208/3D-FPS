"""Save the native third-person book push without changing its carry or grip."""
import hashlib
import json
from pathlib import Path

import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/ThirdPersonBookPush20261010'
DEST = '/Game/Characters/JasonPlayer20261003/BookPush20261010/Animations'
NAME = 'J_BookPush_NativeArm'
PATH = DEST + '/' + NAME
AUTHOR = 'Tools/PlayerBody/author_book_push20261010.py'
KEY = 'Staff.BookPush'
config = ROOT / 'Content/ColdSteelData/player_body.json'
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('BOOK_PUSH_SAVE_REQUIRES_END_PLAY')
payload = (OUT / 'authored.json').read_bytes()
data = json.loads(payload)
cfg = json.loads(config.read_text(encoding='utf-8-sig'))
previous = cfg['clips'].get(KEY)
carry_path = json.loads((ROOT / 'SourceAssets/ThirdPersonBookCarryRelax20261010/assets-saved.json').read_text())['clips']['Staff.BookCarry']
if cfg['body_mesh'] != data['mesh'] or cfg['clips']['Staff.BookCarry'] != carry_path or previous not in (None, PATH + '.' + NAME):
    raise RuntimeError('Active book carry or push changed; retain current configuration')
mesh = u.load_asset(data['mesh'])
lib = u.EditorAssetLibrary
clip = u.load_asset(PATH) if lib.does_asset_exist(PATH) else None
if clip and lib.get_metadata_tag(clip, 'AuthoringScript') != AUTHOR:
    raise RuntimeError('Existing asset has different author: ' + PATH)
fresh = not clip
if fresh:
    factory = u.AnimSequenceFactory()
    factory.set_editor_property('target_skeleton', mesh.skeleton)
    factory.set_editor_property('preview_skeletal_mesh', mesh)
    clip = u.AssetToolsHelpers.get_asset_tools().create_asset(NAME, DEST, u.AnimSequence, factory)
c = data['clips'][KEY]
clip.get_editor_property('platform_target_frame_rate').set_editor_property('default', u.FrameRate(c['rate'], 1))
ctl = clip.get_editor_property('controller')
ctl.open_bracket('Book push from accepted native left arm', False)
try:
    ctl.set_frame_rate(u.FrameRate(c['rate'], 1), False)
    ctl.set_number_of_frames(u.FrameNumber(len(c['frames']) - 1), False)
    for i, bone in enumerate(data['names']):
        if fresh:
            ctl.add_bone_curve(bone, False)
        keys = [f[i] for f in c['frames']]
        if not ctl.set_bone_track_keys(bone, [u.Vector(*t[:3]) for t in keys],
                                      [u.Quat(*t[3:7]) for t in keys], [u.Vector(*t[7:]) for t in keys], False):
            raise RuntimeError('Cannot write ' + bone)
finally:
    ctl.close_bracket(False)
clip.set_preview_skeletal_mesh(mesh)
clip.set_editor_property('enable_root_motion', False)
clip.set_editor_property('force_root_lock', True)
clip.set_editor_property('root_motion_root_lock', u.RootMotionRootLock.REF_POSE)
u.AnimationLibrary.remove_all_animation_sync_markers(clip)
if fresh:
    u.AnimationLibrary.add_animation_notify_track(clip, 'CombatTiming')
for marker, fraction in [('Contact', c['contact']), ('Release', c['release']), ('NativeBookArm', 0.)]:
    u.AnimationLibrary.add_animation_sync_marker(clip, marker, fraction * clip.get_play_length(), 'CombatTiming')
source_hash = hashlib.sha256(payload).hexdigest()
for tag, value in {'AuthoringScript': AUTHOR, 'SourceAsset': c['source'],
                   'SourceHash': source_hash, 'MotionScope': data['scope']}.items():
    lib.set_metadata_tag(clip, tag, value)
if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):
    raise RuntimeError('Finalize failed ' + PATH)
if not lib.save_loaded_asset(clip, False):
    raise RuntimeError('Save failed ' + PATH)
cfg = json.loads(config.read_text(encoding='utf-8-sig'))
if cfg['body_mesh'] != data['mesh'] or cfg['clips'].get(KEY) != previous:
    raise RuntimeError('Book push configuration changed during saving; new asset retained')
cfg['clips'][KEY] = clip.get_path_name()
config.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
receipt = dict(clips={KEY: clip.get_path_name()}, previous_clip=previous,
               source_hash=source_hash, runtime_tested=False)
(OUT / 'assets-saved.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print('BOOK_PUSH_SAVED_AND_REGISTERED', clip.get_path_name())
