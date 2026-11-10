"""Save the two skill animations through the project's serialized UE bridge."""
from pathlib import Path
import json
import unreal as u
P=Path(__file__).resolve().parent
DEST='/Game/Skills/ChainSlash20261107/Animations'
OWNER='ChainSlash20261107'
lib=u.EditorAssetLibrary
saved={}
for grip in ('Standard','LongGrip'):
    data=json.loads((P/(grip+'.json')).read_text());frames=data['frames']
    name='A_ChainSlash_'+grip;path=DEST+'/'+name
    exists=lib.does_asset_exist(path)
    if exists:
        seq=u.load_asset(path)
        if lib.get_metadata_tag(seq,'ChainSlash.Author')!=OWNER:raise RuntimeError('Unowned asset '+path)
        if any(p.get_name()==path for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
            raise RuntimeError('Preserving unsaved changes '+path)
    else:
        factory=u.AnimSequenceFactory();factory.set_editor_property('target_skeleton',u.load_asset(data['skeleton']))
        seq=u.AssetToolsHelpers.get_asset_tools().create_asset(name,DEST,u.AnimSequence,factory)
        if not seq:raise RuntimeError('Asset creation failed '+path)
    ctl=seq.get_editor_property('controller');ctl.open_bracket('Author four-cut Lian Zhan',False)
    try:
        ctl.set_frame_rate(u.FrameRate(data['fps'],1),False)
        ctl.set_number_of_frames(u.FrameNumber(len(frames)-1),False)
        for bone in frames[0]:
            if not exists:ctl.add_bone_curve(bone,False)
            keys=[f[bone] for f in frames]
            if not ctl.set_bone_track_keys(bone,[u.Vector(*k['p']) for k in keys],
                [u.Quat(*k['q'][1:],k['q'][0]) for k in keys],[u.Vector(*k['s']) for k in keys],False):
                raise RuntimeError('Track write failed '+bone)
    finally:ctl.close_bracket(False)
    seq.get_editor_property('platform_target_frame_rate').set_editor_property('default',u.FrameRate(data['fps'],1))
    seq.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'))
    seq.set_editor_property('enable_root_motion',False)
    if not exists:u.AnimationLibrary.add_animation_notify_track(seq,'ChainSlashTiming')
    u.AnimationLibrary.remove_all_animation_sync_markers(seq)
    for name,time in data['markers']:u.AnimationLibrary.add_animation_sync_marker(seq,name,time,'ChainSlashTiming')
    for key,value in {'Author':OWNER,'Name':'连斩','WeaponRequirement':'TwoHandedSword','Stage':'PlayableSkill',
                      'Reference':'NTrzxPIXer4 37.30-40.00s','Acceptance':'PendingUserReview'}.items():
        lib.set_metadata_tag(seq,'ChainSlash.'+key,value)
    if not lib.save_loaded_asset(seq,False):raise RuntimeError('Save failed '+path)
    saved[grip]=dict(asset=seq.get_path_name(),frames=len(frames),fps=data['fps'],seconds=(len(frames)-1)/data['fps'])
    (P/'saved-assets.json').write_text(json.dumps(saved,ensure_ascii=False,indent=2))
    print('CHAIN_SLASH_SAVED',grip,path)
