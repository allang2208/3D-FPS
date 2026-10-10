"""Save and register only the relaxed left spellbook support pose."""
import hashlib
import json
from pathlib import Path

import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/ThirdPersonBookCarryRelax20261010'
DEST = '/Game/Characters/JasonPlayer20261003/BookCarryRelax20261010/Animations'
AUTHOR = 'Tools/PlayerBody/author_book_carry_relax20261010.py'
NAME = 'J_BookCarry_Relaxed'
PATH = DEST + '/' + NAME
KEY = 'Staff.BookCarry'
config = ROOT / 'Content/ColdSteelData/player_body.json'

# Do not create partial assets while PIE forbids editor asset saving.
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('BOOK_CARRY_SAVE_REQUIRES_END_PLAY')

payload = (OUT / 'authored.json').read_bytes()
data = json.loads(payload)
cfg = json.loads(config.read_text(encoding='utf-8-sig'))
previous = cfg['clips'][KEY]
baseline = json.loads((ROOT / 'SourceAssets/ThirdPersonStaffCarryClearance20261010/assets-saved.json').read_text())['clips'][KEY]
if cfg['body_mesh'] != data['mesh'] or previous not in (baseline, PATH + '.' + NAME):
    raise RuntimeError('Active body or book pose changed; retain the current configuration')

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
controller = clip.get_editor_property('controller')
controller.open_bracket('Relax accepted left book support', False)
try:
    controller.set_frame_rate(u.FrameRate(c['rate'], 1), False)
    controller.set_number_of_frames(u.FrameNumber(len(c['frames']) - 1), False)
    for i, bone in enumerate(data['names']):
        if fresh:
            controller.add_bone_curve(bone, False)
        keys = [frame[i] for frame in c['frames']]
        if not controller.set_bone_track_keys(bone, [u.Vector(*t[:3]) for t in keys],
                                              [u.Quat(*t[3:7]) for t in keys],
                                              [u.Vector(*t[7:]) for t in keys], False):
            raise RuntimeError('Cannot write ' + bone)
finally:
    controller.close_bracket(False)
clip.set_preview_skeletal_mesh(mesh)
clip.set_editor_property('enable_root_motion', False)
clip.set_editor_property('force_root_lock', True)
clip.set_editor_property('root_motion_root_lock', u.RootMotionRootLock.REF_POSE)
u.AnimationLibrary.remove_all_animation_sync_markers(clip)
source_hash = hashlib.sha256(payload).hexdigest()
for tag, value in {'AuthoringScript': AUTHOR, 'SourceAsset': c['source'],
                   'SourceHash': source_hash, 'MotionScope': data['scope']}.items():
    lib.set_metadata_tag(clip, tag, value)
if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):
    raise RuntimeError('Finalize failed ' + PATH)
if not lib.save_loaded_asset(clip, False):
    raise RuntimeError('Save failed ' + PATH)

# Re-read immediately before the scoped registration, retaining parallel edits.
cfg = json.loads(config.read_text(encoding='utf-8-sig'))
if cfg['body_mesh'] != data['mesh'] or cfg['clips'][KEY] != previous:
    raise RuntimeError('Book pose configuration changed during saving; new asset retained')
cfg['clips'][KEY] = clip.get_path_name()
config.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
receipt = dict(clips={KEY: clip.get_path_name()}, previous_clip=previous,
               source_hash=source_hash, runtime_tested=False)
(OUT / 'assets-saved.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print('BOOK_CARRY_RELAX_SAVED_AND_REGISTERED', clip.get_path_name())
