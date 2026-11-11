"""Background import of the dual-hatchet sprint-ready run set:
  Clips/HatchetDualSprintEnter.json -> A_TacticalHatchet_DualSprintEnter
  Clips/HatchetDualSprintReady.json -> A_TacticalHatchet_DualSprintReady
  Clips/HatchetDualSprintExit.json  -> A_TacticalHatchet_DualSprintExit

Run (commandlet, editor closed or not holding these packages):
  UnrealEditor-Cmd.exe FPSGAME.uproject -run=pythonscript -script=<this file> -unattended -nosplash
Same animation path as Kukri20261020/import_kukri.py (shared sword arms skeleton, 120 Hz keys, authored-rate
compression); only these clips, nothing else is re-saved.  Never runs PIE or tests.  Writes import_receipt.json here.
"""
import json
from pathlib import Path
import unreal as u

P = Path(globals().get('__file__') or r"D:\FPS3D\FPSGAME\SourceAssets\HatchetSprint20261103\import_hatchet_ready_run.py").resolve().parent
DEST = '/Game/Weapons/TacticalHatchet20261101/Animations'
ARMS = '/Game/Weapons/FrostCrystalSword20260915/Modules20260915/SK_FrostSword_Arms'
SKELETON = '/Game/Weapons/AzureRunesword20260913/SK_AzureRunesword_Manny_Skeleton'
REVISION = 'HatchetReadyRun_V3_RightSwing_20261104'
CLIPS = {
    'HatchetDualSprintEnter': 'A_TacticalHatchet_DualSprintEnter',
    'HatchetDualSprintReady': 'A_TacticalHatchet_DualSprintReady',
    'HatchetDualSprintExit': 'A_TacticalHatchet_DualSprintExit',
}
A = u.AssetToolsHelpers.get_asset_tools()
L = u.EditorAssetLibrary
receipt = dict(revision=REVISION, assets=[], animations={}, runtime_tested=False, complete=False)

arms = u.load_asset(ARMS)
skeleton = u.load_asset(SKELETON)
if not arms or not skeleton:
    raise RuntimeError('Shared sword arms or skeleton missing')
dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for clip, name in CLIPS.items():
    data = json.loads((P / 'Clips' / (clip + '.json')).read_text('utf-8'))
    path = DEST + '/' + name
    if path in dirty:
        raise RuntimeError('Preserving unsaved edits: ' + path)
    seq = u.load_asset(path)
    if not seq:
        factory = u.AnimSequenceFactory()
        factory.set_editor_property('target_skeleton', skeleton)
        factory.set_editor_property('preview_skeletal_mesh', arms)
        seq = A.create_asset(name, DEST, u.AnimSequence, factory)
        if not seq:
            raise RuntimeError('Cannot create ' + path)
    authored_rate = u.FrameRate(numerator=data['fps'], denominator=1)
    seq.get_editor_property('platform_target_frame_rate').set_editor_property('default', authored_rate)
    controller = seq.get_editor_property('controller')
    if controller is None:
        controller = u.AnimDataController()
        controller.set_model(seq.get_editor_property('data_model_interface'))
    frames = data['frames']
    controller.open_bracket('Hatchet ' + clip, False)
    try:
        controller.remove_all_bone_tracks(False)
        controller.set_frame_rate(authored_rate, False)
        controller.set_number_of_frames(u.FrameNumber(value=len(frames) - 1), False)
        for bone in data['bones']:
            if not controller.add_bone_curve(bone, False):
                raise RuntimeError('Cannot add bone ' + bone)
            keys = [f[bone] for f in frames]
            ok = controller.set_bone_track_keys(bone, [u.Vector(*k[0]) for k in keys],
                                                [u.Quat(k[1][1], k[1][2], k[1][3], k[1][0]) for k in keys],
                                                [u.Vector(*k[2]) for k in keys], False)
            if not ok:
                raise RuntimeError('Cannot key ' + bone)
    finally:
        controller.close_bracket(False)
    seq.set_preview_skeletal_mesh(arms)
    seq.set_editor_property('enable_root_motion', False)
    seq.set_editor_property('force_root_lock', False)
    L.set_metadata_tag(seq, 'Hatchet.AuthorSource', str(P / 'Clips' / (clip + '.json')))
    L.set_metadata_tag(seq, 'Hatchet.Revision', REVISION)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(seq):
        raise RuntimeError('Cannot finalize ' + path)
    if not u.EditorLoadingAndSavingUtils.save_packages([seq.get_outermost()], False):
        raise RuntimeError('Hatchet save failed: ' + path)
    receipt['assets'].append(seq.get_path_name())
    receipt['animations'][path] = dict(frames=len(frames), fps=data['fps'], seconds=(len(frames) - 1) / data['fps'],
                                       play_length=seq.get_play_length(), loop=data['loop'])
    u.log('HATCHET_ANIM_SAVED %s %.3f s' % (path, seq.get_play_length()))

receipt['complete'] = True
(P / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
u.log('HATCHET_IMPORT_COMPLETE assets=%d' % len(receipt['assets']))
