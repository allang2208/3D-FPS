"""Resample each saved native body, retaining the female contact corrections."""
import hashlib,json,runpy
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME');REVISION=globals().get('FURNITURE_REVISION','ApartmentFastRest20261024R2');OUT=ROOT/'SourceAssets/FurnitureRest20261022'/REVISION
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
data=read(OUT/'authored.json');baseline=read(OUT/'baseline_routes.json');recipe=data['native_retime']
source_hash=hashlib.sha256((OUT/'authored.json').read_bytes()).hexdigest();E=u.EditorAssetLibrary
receipt_path=OUT/'assets_saved.json';receipt=read(receipt_path) if receipt_path.exists() else {'source_sha256':source_hash,'default':{},'variants':{},'retimed_native_sources':recipe['source_assets']}
pending_path=OUT/'pending_native.json';pending=read(pending_path) if pending_path.exists() else {}
if receipt['source_sha256']!=source_hash:raise RuntimeError('Preserve saved revision; authoring source changed.')
lengths={}
for variant,source_path in recipe['source_assets'].items():
    mesh=u.load_asset(data['mesh'] if variant=='default' else baseline['variants'][variant]['mesh'])
    source=u.load_asset(source_path)
    if not mesh or not source or source.get_editor_property('skeleton')!=mesh.skeleton:raise RuntimeError('Missing matching native source: '+variant)
    opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.evaluation_type=u.AnimDataEvalType.COMPRESSED
    # Retain authored local keys and the source's retarget reference pose.
    # Sampling a retargeted pose and retargeting again changes female proportions.
    opt.should_retarget=False
    names=[str(n) for n in u.AnimationLibrary.get_animation_track_names(source)]
    routes=receipt['default'] if variant=='default' else receipt['variants'].setdefault(variant,{})
    dest=('/Game/Characters/JasonPlayer20261003/FurnitureRest20261022/' if variant=='default' else '/Game/Characters/KaitlinPlayer20261023/')+REVISION
    lengths[variant]={}
    for role,times in recipe['samples'].items():
        if role in routes:
            lengths[variant][role]=u.load_asset(routes[role]).get_play_length();continue
        name=('A_' if variant=='default' else 'K_A_')+role.replace('.','_')
        target_path=dest+'/'+name
        existing=u.find_object(None,target_path+'.'+name)
        if existing or E.does_asset_exist(target_path):
            if pending.get(target_path)!=source_hash:raise RuntimeError('Preserve unreceipted package: '+name)
            clip=existing or u.load_asset(target_path)
        else:clip=None
        poses=[u.AnimPoseExtensions.get_anim_pose_at_time(source,min(t,source.get_play_length()),opt) for t in times]
        if not clip:
            clip=E.duplicate_asset(source_path,target_path)
            pending[target_path]=source_hash;pending_path.write_text(json.dumps(pending,indent=2))
        ctl=clip.get_editor_property('controller');ctl.open_bracket('Smooth four-second bed timing',False)
        try:
            ctl.set_frame_rate(u.FrameRate(30,1),False);ctl.set_number_of_frames(u.FrameNumber(len(times)-1),False)
            for bone in names:
                keys=[u.AnimPoseExtensions.get_bone_pose(p,bone,u.AnimPoseSpaces.LOCAL) for p in poses]
                if not ctl.set_bone_track_keys(bone,[k.translation for k in keys],[k.rotation for k in keys],[k.scale3d for k in keys],False):raise RuntimeError('Native track failed: '+bone)
        finally:ctl.close_bracket(False)
        for key in ('enable_root_motion','force_root_lock','root_motion_root_lock'):clip.set_editor_property(key,source.get_editor_property(key))
        clip.set_editor_property('rate_scale',1.)
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip) or not E.save_loaded_asset(clip,False):raise RuntimeError('Native retime save failed: '+role)
        length=clip.get_play_length()
        if abs(length-data['clips'][role]['duration'])>.001:raise RuntimeError('Native clock differs: '+role)
        routes[role]=clip.get_path_name();lengths[variant][role]=length
        receipt_path.write_text(json.dumps(receipt,indent=2));print('FAST_REST_NATIVE_SAVED',variant,role,length,flush=True)
(OUT/'save_complete.json').write_text(json.dumps({'authored_sha256':source_hash,'default_clips':len(receipt['default']),'variant_clips':{n:len(v) for n,v in receipt['variants'].items()},'saved':True,'runtime_published':False,'saved_durations':lengths},indent=2))
runpy.run_path(str(Path(__file__).with_name('read_meshy_bed_saved.py')),init_globals={'FURNITURE_REVISION':REVISION})
print('FAST_REST_SAVE_COMPLETE',flush=True)
