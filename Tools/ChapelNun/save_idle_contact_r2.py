"""Save the nun-only native animation; do not replace the shared player idle."""
import json
from pathlib import Path
import unreal as u

editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():
    raise RuntimeError('Preserving active PIE; stop play before saving nun animation')

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/ChapelNun20261115/IdleHandsFrontR2'
d = json.loads((OUT/'authored.json').read_text(encoding='utf-8'))
folder = '/Game/Characters/ChapelNun20261115/Animations'
name = 'A_Nun_Idle_HandsFront_R2'
path = folder+'/'+name
mesh = u.load_asset(d['mesh'])
factory = u.AnimSequenceFactory()
factory.set_editor_property('target_skeleton', mesh.skeleton)
factory.set_editor_property('preview_skeletal_mesh', mesh)
lib = u.EditorAssetLibrary
if lib.does_asset_exist(path):
    raise RuntimeError('Preserving existing output. Use a new revision: '+path)
clip = u.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, u.AnimSequence, factory)
ctl = clip.get_editor_property('controller')
ctl.open_bracket('Nun clasped hands and quiet breathing', False)
try:
    ctl.set_frame_rate(u.FrameRate(d['rate'], 1), False)
    ctl.set_number_of_frames(u.FrameNumber(len(d['frames'])-1), False)
    for i, bone in enumerate(d['names']):
        ctl.add_bone_curve(bone, False)
        keys = [f[i] for f in d['frames']]
        if not ctl.set_bone_track_keys(bone, [u.Vector(*k[:3]) for k in keys],
                [u.Quat(*k[3:7]) for k in keys], [u.Vector(*k[7:]) for k in keys], False):
            raise RuntimeError('Cannot author track '+bone)
finally:
    ctl.close_bracket(False)
clip.set_editor_property('enable_root_motion', False)
clip.set_editor_property('force_root_lock', True)
clip.set_editor_property('root_motion_root_lock', u.RootMotionRootLock.REF_POSE)
lib.set_metadata_tag(clip, 'NunMotionSource', 'User standing reference; locally authored native animation')
lib.set_metadata_tag(clip, 'NunMotionRevision', 'HandsFrontR2')
if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):
    raise RuntimeError('Native animation finalization failed')
if not lib.save_loaded_asset(clip, False):
    raise RuntimeError('Native animation save failed')
receipt = dict(asset=clip.get_path_name(), skeleton=mesh.skeleton.get_path_name(),
               duration=d['duration'], frames=len(d['frames']), saved=True,
               source='User still image; no external animation download', runtime_tested=False)
(OUT/'saved_asset.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('NUN_IDLE_SAVED', clip.get_path_name(), flush=True)
