"""Create, compress, save and register native Jason staff casting clips."""
import hashlib
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/ThirdPersonStaffCast20261009'
DEST='/Game/Characters/JasonPlayer20261003/StaffCast20261009/Animations'
payload=(OUT/'authored.json').read_bytes()
digest=hashlib.sha256(payload).hexdigest()
d=json.loads(payload)
lib=u.EditorAssetLibrary
mesh=u.load_asset(d['mesh'])
factory=u.AnimSequenceFactory()
factory.set_editor_property('target_skeleton',mesh.skeleton)
factory.set_editor_property('preview_skeletal_mesh',mesh)
receipt=dict(clips={},source_hash=digest,provenance=d['provenance'],license_file=d['license_file'],runtime_tested=False)
for key,c in d['clips'].items():
    name='J_KayKit_'+key.replace('.','_')
    path=DEST+'/'+name
    clip=u.load_asset(path) if lib.does_asset_exist(path) else None
    if clip and lib.get_metadata_tag(clip,'AuthoringScript')!='Tools/PlayerBody/author_staff_cast20261009.py':
        raise RuntimeError('Refusing to overwrite an animation owned by another author '+path)
    fresh=not clip
    if fresh or lib.get_metadata_tag(clip,'StaffCastSourceHash')!=digest:
        if fresh:clip=u.AssetToolsHelpers.get_asset_tools().create_asset(name,DEST,u.AnimSequence,factory)
        clip.get_editor_property('platform_target_frame_rate').set_editor_property('default',u.FrameRate(c['rate'],1))
        ctl=clip.get_editor_property('controller')
        frames=c['frames']
        ctl.open_bracket('Adapt KayKit staff casting to Jason',False)
        try:
            ctl.set_frame_rate(u.FrameRate(c['rate'],1),False)
            ctl.set_number_of_frames(u.FrameNumber(len(frames)-1),False)
            for j,bone in enumerate(d['names']):
                if fresh:ctl.add_bone_curve(bone,False)
                keys=[f[j] for f in frames]
                if not ctl.set_bone_track_keys(bone,[u.Vector(*t[:3]) for t in keys],
                        [u.Quat(*t[3:7]) for t in keys],[u.Vector(*t[7:]) for t in keys],False):
                    raise RuntimeError('Cannot write '+bone)
        finally: ctl.close_bracket(False)
        clip.set_preview_skeletal_mesh(mesh)
        clip.set_editor_property('enable_root_motion',False)
        clip.set_editor_property('force_root_lock',True)
        clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.REF_POSE)
        u.AnimationLibrary.remove_all_animation_sync_markers(clip)
        if fresh:u.AnimationLibrary.add_animation_notify_track(clip,'CombatTiming')
        for marker,fraction in [('Contact',c['contact']),('Release',c['release'])]:
            u.AnimationLibrary.add_animation_sync_marker(clip,marker,fraction*clip.get_play_length(),'CombatTiming')
        for tag,value in dict(StaffCastSourceHash=digest,ThirdPersonSource=d['provenance'],
                              SourceAsset=c['source'],SourceURL=d['source_url'],
                              AuthoringScript='Tools/PlayerBody/author_staff_cast20261009.py').items():
            lib.set_metadata_tag(clip,tag,value)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):
        raise RuntimeError('Cannot finalize '+path)
    if not lib.save_loaded_asset(clip,False): raise RuntimeError('Cannot save '+path)
    receipt['clips'][key]=clip.get_path_name()
    print('STAFF_CAST_ASSET_SAVED '+clip.get_path_name())

# Read immediately before the scoped merge, retaining parallel configuration edits.
config=ROOT/'Content/ColdSteelData/player_body.json'
cfg=json.loads(config.read_text(encoding='utf-8-sig'))
cfg['clips'].update(receipt['clips'])
config.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'assets-saved.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('STAFF_CAST_REGISTERED')
