"""Author the planted reverse cut on each installed world-body skeleton."""
from pathlib import Path
import json
import unreal as u

P=Path(__file__).resolve().parent
DEST='/Game/Weapons/HighlandClaymore20260922/BreakSweep20261104'
FPS=60
lib=u.EditorAssetLibrary
lib_anim=u.AnimationLibrary
saved={}
for kind in ('Jason','Kaitlin'):
    data=json.loads((P/(kind+'-body-tracks.json')).read_text())
    skeleton=u.load_asset(data['skeleton'])
    name='A_Highland_BreakSweep_'+kind
    path=DEST+'/'+name
    exists=lib.does_asset_exist(path)
    if exists:
        seq=u.load_asset(path)
        if lib.get_metadata_tag(seq,'Highland.Author')!='HighlandBroadbladeSweep20261104':
            raise RuntimeError('Preserving '+path)
    else:
        factory=u.AnimSequenceFactory()
        factory.set_editor_property('target_skeleton',skeleton)
        seq=u.AssetToolsHelpers.get_asset_tools().create_asset(name,DEST,u.AnimSequence,factory)
    ctl=seq.get_editor_property('controller')
    ctl.open_bracket('Plant and cut across the body',False)
    try:
        ctl.set_frame_rate(u.FrameRate(FPS,1),False)
        ctl.set_number_of_frames(u.FrameNumber(len(next(iter(data['tracks'].values())))-1),False)
        for n,rows in data['tracks'].items():
            pp=[u.Vector(*r[:3]) for r in rows]
            qq=[u.Quat(*r[3:7]) for r in rows]
            ss=[u.Vector(*r[7:]) for r in rows]
            if not exists:ctl.add_bone_curve(n,False)
            if not ctl.set_bone_track_keys(n,pp,qq,ss,False):raise RuntimeError(n)
    finally:ctl.close_bracket(False)
    if not exists:
        lib_anim.add_animation_notify_track(seq,'SweepTiming')
        for key,time in [('Contact',.30),('Release',.47)]:
            lib_anim.add_animation_sync_marker(seq,key,time,'SweepTiming')
    if 'NativeSwordGrip' not in [str(m.marker_name) for m in lib_anim.get_animation_sync_markers(seq)]:
        lib_anim.add_animation_sync_marker(seq,'NativeSwordGrip',0.,'SweepTiming')
    seq.set_editor_property('enable_root_motion',False)
    seq.set_editor_property('force_root_lock',True)
    lib.set_metadata_tag(seq,'Highland.Author','HighlandBroadbladeSweep20261104')
    if not lib.save_loaded_asset(seq,False):raise RuntimeError('Cannot save '+path)
    saved[kind]=seq.get_path_name()
    (P/'saved-body.json').write_text(json.dumps(saved,indent=2))
    print('HIGHLAND_SWEEP_BODY_SAVED',kind,path)
