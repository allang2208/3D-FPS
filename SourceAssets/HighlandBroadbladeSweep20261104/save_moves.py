"""Publish both grip-specific sword animations and their contact markers."""
from pathlib import Path
import json
import unreal as u

P = Path(__file__).resolve().parent
DEST = '/Game/Weapons/HighlandClaymore20260922/BreakSweep20261104'
lib = u.EditorAssetLibrary
saved = {}
for grip in ('Standard','LongGrip','Standard_FromReady','LongGrip_FromReady'):
    data = json.loads((P/(grip+'.json')).read_text())
    name = 'A_Highland_BreakSweep_'+grip
    path = DEST+'/'+name
    exists = lib.does_asset_exist(path)
    if exists:
        seq = u.load_asset(path)
        if lib.get_metadata_tag(seq,'Highland.Author') != 'HighlandBroadbladeSweep20261104':
            raise RuntimeError('Preserving existing asset '+path)
        if any(package.get_name()==path for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
            raise RuntimeError('Preserving unsaved changes '+path)
    else:
        factory = u.AnimSequenceFactory()
        factory.set_editor_property('target_skeleton',u.load_asset(data['skeleton']))
        seq = u.AssetToolsHelpers.get_asset_tools().create_asset(name,DEST,u.AnimSequence,factory)
        if not seq: raise RuntimeError('Cannot create '+path)
    frames = data['frames']
    controller = seq.get_editor_property('controller')
    controller.open_bracket('Author Highland lateral cut',False)
    try:
        controller.set_frame_rate(u.FrameRate(data['fps'],1),False)
        controller.set_number_of_frames(u.FrameNumber(len(frames)-1),False)
        for bone in frames[0]:
            if not exists:
                controller.add_bone_curve(bone,False)
            keys = [frame[bone] for frame in frames]
            if not controller.set_bone_track_keys(bone,[u.Vector(*k['p']) for k in keys],
                [u.Quat(*k['q'][1:],k['q'][0]) for k in keys],[u.Vector(*k['s']) for k in keys],False):
                raise RuntimeError('Cannot author '+bone)
    finally:
        controller.close_bracket(False)
    seq.get_editor_property('platform_target_frame_rate').set_editor_property('default',u.FrameRate(data['fps'],1))
    seq.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'))
    seq.set_editor_property('enable_root_motion',False)
    if not u.AnimationLibrary.get_animation_sync_markers(seq):
        u.AnimationLibrary.add_animation_notify_track(seq,'SweepTiming')
    u.AnimationLibrary.remove_all_animation_sync_markers(seq)
    for label,time in [('Contact',.30),('Release',.47),('Arrest',.55),('Recover',.66)]:
        u.AnimationLibrary.add_animation_sync_marker(seq,label,time,'SweepTiming')
    lib.set_metadata_tag(seq,'Highland.Author','HighlandBroadbladeSweep20261104')
    if not lib.save_loaded_asset(seq,False): raise RuntimeError('Cannot save '+path)
    saved[grip]=seq.get_path_name()
    (P/'saved-moves.json').write_text(json.dumps(saved,indent=2))
    print('HIGHLAND_SWEEP_SAVED',grip,path)
