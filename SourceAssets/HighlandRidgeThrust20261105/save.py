from pathlib import Path
import json
import runpy
import unreal as u

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
if Path(u.Paths.project_dir()).resolve()!=ROOT:
    raise RuntimeError('Wrong target project')
OUT=ROOT/'Saved/RidgeThrustAuthor'
DEST='/Game/Weapons/HighlandClaymore20260922/RidgeThrust20261105'
LIB=u.EditorAssetLibrary
saved=[]
roles=globals().get('RIDGE_PHASES',('Charge','Release','Counter'))
stroke=runpy.run_path(str(HERE/'strike_timing.py'))
for grip in ('Standard','LongGrip'):
    for role in roles:
        data=json.loads((OUT/(grip+role+'.json')).read_text())
        frames=data['frames']
        name='A_Highland_Ridge_'+grip+'_'+role
        path=DEST+'/'+name
        exists=LIB.does_asset_exist(path)
        if exists:
            seq=u.load_asset(path)
            if LIB.get_metadata_tag(seq,'Highland.Author')!='HighlandRidgeThrust20261105' or any(
                p.get_name()==path for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
                raise RuntimeError('Preserving existing changes '+path)
        else:
            factory=u.AnimSequenceFactory()
            factory.set_editor_property('target_skeleton',u.load_asset(data['skeleton']))
            seq=u.AssetToolsHelpers.get_asset_tools().create_asset(name,DEST,u.AnimSequence,factory)
        if not seq: raise RuntimeError('Cannot create '+path)
        controller=seq.get_editor_property('controller')
        controller.open_bracket('Author Highland ridge heavy thrust',False)
        try:
            controller.set_frame_rate(u.FrameRate(data['fps'],1),False)
            controller.set_number_of_frames(u.FrameNumber(len(frames)-1),False)
            for bone in frames[0]:
                if not exists: controller.add_bone_curve(bone,False)
                keys=[f[bone] for f in frames]
                if not controller.set_bone_track_keys(bone,[u.Vector(*k['p']) for k in keys],
                    [u.Quat(*k['q'][1:],k['q'][0]) for k in keys],[u.Vector(*k['s']) for k in keys],False):
                    raise RuntimeError('Cannot key '+bone)
        finally:
            controller.close_bracket(False)
        seq.get_editor_property('platform_target_frame_rate').set_editor_property('default',u.FrameRate(data['fps'],1))
        seq.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'))
        seq.set_editor_property('enable_root_motion',False)
        if not exists:u.AnimationLibrary.add_animation_notify_track(seq,'RidgeTiming')
        u.AnimationLibrary.remove_all_animation_sync_markers(seq)
        lead=stroke['LEAD'] if role=='Counter' else 0
        marks=[('PointSet',(3176-3120)/60)] if role=='Charge' else [
            (label,(lead+key)/stroke['FPS']) for label,key in (
                ('Contact',stroke['CONTACT']),('Extension',stroke['EXTENSION']),
                ('Withdrawal',stroke['EXTENSION']+stroke['HOLD']))]
        for label,t in marks:u.AnimationLibrary.add_animation_sync_marker(seq,label,t,'RidgeTiming')
        LIB.set_metadata_tag(seq,'Highland.Author','HighlandRidgeThrust20261105')
        if not LIB.save_loaded_asset(seq,False):raise RuntimeError('Cannot save '+path)
        saved.append(seq.get_path_name());u.log('RIDGE_THRUST_SAVED '+path)
receipt={('Charge',):'saved-charge.json',('Release','Counter'):'saved-strike.json'}.get(roles,'saved-assets.json')
(OUT/receipt).write_text(json.dumps(saved,indent=2))
