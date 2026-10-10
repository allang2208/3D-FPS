"""Save the complete staff clearance arm and independent book carry poses."""
import json
import hashlib
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/ThirdPersonStaffCarryClearance20261010'
DEST='/Game/Characters/JasonPlayer20261003/StaffCarryClearance20261010/Animations'
payload=(OUT/'authored.json').read_bytes();data=json.loads(payload)
mesh=u.load_asset(data['mesh']);lib=u.EditorAssetLibrary
factory=u.AnimSequenceFactory()
factory.set_editor_property('target_skeleton',mesh.skeleton)
factory.set_editor_property('preview_skeletal_mesh',mesh)
receipt=dict(clips={},source_hash=hashlib.sha256(payload).hexdigest(),runtime_tested=False)
for key,c in data['clips'].items():
    name='J_StaffClearance_'+key.split('.')[-1];path=DEST+'/'+name
    clip=u.load_asset(path) if lib.does_asset_exist(path) else None
    if clip and lib.get_metadata_tag(clip,'AuthoringScript')!='Tools/PlayerBody/author_staff_carry_clearance20261010.py':
        raise RuntimeError('Existing asset has different author: '+path)
    fresh=not clip
    if fresh:clip=u.AssetToolsHelpers.get_asset_tools().create_asset(name,DEST,u.AnimSequence,factory)
    ctl=clip.get_editor_property('controller');frames=c['frames']
    ctl.open_bracket('Retarget Motifect right arm with native lengths',False)
    try:
        ctl.set_frame_rate(u.FrameRate(c['rate'],1),False)
        ctl.set_number_of_frames(u.FrameNumber(len(frames)-1),False)
        for i,bone in enumerate(data['names']):
            if fresh:ctl.add_bone_curve(bone,False)
            keys=[f[i] for f in frames]
            if not ctl.set_bone_track_keys(bone,[u.Vector(*t[:3]) for t in keys],
                    [u.Quat(*t[3:7]) for t in keys],[u.Vector(*t[7:]) for t in keys],False):
                raise RuntimeError('Cannot write '+bone)
    finally:ctl.close_bracket(False)
    clip.set_preview_skeletal_mesh(mesh)
    clip.set_editor_property('enable_root_motion',False)
    clip.set_editor_property('force_root_lock',True)
    clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.REF_POSE)
    u.AnimationLibrary.remove_all_animation_sync_markers(clip)
    if 'contact' in c:
        if fresh:u.AnimationLibrary.add_animation_notify_track(clip,'CombatTiming')
        u.AnimationLibrary.add_animation_sync_marker(clip,'Contact',c['contact']*clip.get_play_length(),'CombatTiming')
    for tag,value in {'AuthoringScript':'Tools/PlayerBody/author_staff_carry_clearance20261010.py',
        'SourceAsset':c['source'],'SourceURL':data['source_url'],'SourceHash':receipt['source_hash'],
        'SourceFrameRange':str(c['range']),'MotionScope':'Complete staff arm staging or book support; existing fingers and mounts retained'}.items():
        lib.set_metadata_tag(clip,tag,value)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Finalize failed '+path)
    if not lib.save_loaded_asset(clip,False):raise RuntimeError('Save failed '+path)
    receipt['clips'][key]=clip.get_path_name()
    print('STAFF_CLEARANCE_SAVED',clip.get_path_name())
config=ROOT/'Content/ColdSteelData/player_body.json'
cfg=json.loads(config.read_text(encoding='utf-8-sig'))
if cfg['body_mesh']!=data['mesh']:raise RuntimeError('Body mesh changed during authoring')
cfg['clips'].update(receipt['clips'])
config.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'assets-saved.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print('STAFF_CLEARANCE_REGISTERED')
