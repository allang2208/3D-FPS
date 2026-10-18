"""Save the dedicated two-arm native clip and register the actual consumer key."""
import json,hashlib,shutil
from pathlib import Path
import unreal as u
O=Path('D:/FPS3D/FPSGAME/SourceAssets/LambTwoView20261017');R=O.parents[1]
payload=(O/'authored_body.json').read_bytes();data=json.loads(payload)
continuity=json.loads((O/'body_continuity.json').read_text())
if continuity.get('source_sha256')!=hashlib.sha256(payload).hexdigest() or continuity['max_elbow_step_cm']>3:raise RuntimeError('Complete the known elbow discontinuity repair before publishing this take')
cfgpath=R/'Content/ColdSteelData/player_body.json';cfg=json.loads(cfgpath.read_text(encoding='utf-8-sig'))
if cfg['body_mesh']!=data['mesh']:raise RuntimeError('Body identity changed during authoring')
mesh=u.load_asset(data['mesh']);dest='/Game/Characters/JasonPlayer20261003/FoodNative20261010/Animations';name='J_LargeLamb_TwoHands_20261017';path=dest+'/'+name
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
if E.does_asset_exist(path):raise RuntimeError('Preserve existing saved take; inspect receipt before replay')
factory=u.AnimSequenceFactory();factory.target_skeleton=mesh.skeleton;factory.preview_skeletal_mesh=mesh
clip=A.create_asset(name,dest,u.AnimSequence,factory);frames=data['frames'];ctl=clip.get_editor_property('controller')
clip.get_editor_property('platform_target_frame_rate').set_editor_property('default',u.FrameRate(60,1))
ctl.open_bracket('Large lamb complete native dual-arm take',False)
try:
    ctl.set_frame_rate(u.FrameRate(60,1),False);ctl.set_number_of_frames(u.FrameNumber(len(frames)-1),False)
    for j,bone in enumerate(data['names']):
        ctl.add_bone_curve(bone,False);keys=[f[j] for f in frames]
        if not ctl.set_bone_track_keys(bone,[u.Vector(*v[:3]) for v in keys],[u.Quat(*v[3:7]) for v in keys],[u.Vector(*v[7:]) for v in keys],False):raise RuntimeError('Cannot author '+bone)
finally:ctl.close_bracket(False)
clip.set_preview_skeletal_mesh(mesh)
clip.set_editor_property('enable_root_motion',False)
clip.set_editor_property('force_root_lock',True)
clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.REF_POSE)
u.AnimationLibrary.add_animation_notify_track(clip,'ConsumeTiming')
for marker,seconds in [('Contact',4.65),('Release',4.75),('NativeConsumeArm',0),('NativeTwoHandConsume',0)]:u.AnimationLibrary.add_animation_sync_marker(clip,marker,seconds,'ConsumeTiming')
for key,value in {'AuthoringScript':'SourceAssets/LambTwoView20261017/author_body.py','SourceAsset':data['source'],'SourceURL':data['source_url'],'MotionScope':'Complete native Jason dual-arm lamb take; no FPS wrist IK after blend','SourceHash':hashlib.sha256((O/'authored_body.json').read_bytes()).hexdigest()}.items():E.set_metadata_tag(clip,key,value)
if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Cannot finalize animation')
if not E.save_loaded_asset(clip,False):raise RuntimeError('Cannot save animation')
cfg=json.loads(cfgpath.read_text(encoding='utf-8-sig'));cfg['clips']['Consume.EatLargeLamb']=clip.get_path_name();cfgpath.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
receipt=dict(asset=clip.get_path_name(),frames=len(frames),duration=clip.get_play_length(),key='Consume.EatLargeLamb',completed=True,game_or_pie_started=False)
(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2));print('LAMB_TWO_HAND_BODY_SAVED',receipt)
