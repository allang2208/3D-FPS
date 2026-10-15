"""Save the second attack and its authoritative hand trajectory on the original M66."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/GroundSlamV13')
DEST='/Game/Monsters/IncineratorBossM66';E=u.EditorAssetLibrary;P=u.AnimPoseExtensions
if not globals().get('M66_COMMANDLET',False) and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('End PIE before saving M66 ground slam')
if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('M66 packages have unsaved changes')
bp=u.load_asset(DEST+'/BP_M66RigPreview');clip=u.load_asset(DEST+'/GroundSlamV13/A_M66_GroundSlam_V13')
if not bp or not clip:raise RuntimeError('M66 character or ground slam missing')
cdo=u.get_default_object(bp.generated_class());mesh=cdo.get_editor_property('visual_mesh')
if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('M66 slam finalization failed')
options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.SOURCE;options.optional_skeletal_mesh=mesh
first=P.get_anim_pose_at_time(clip,0.,options);root=P.get_ref_bone_pose(first,'M66_Rig',u.AnimPoseSpaces.WORLD)
names=['Bone_037','Bone_036']
for finger in (57,61,65,69,73):names.extend('Bone_%03d'%n for n in (finger,finger-2,finger-3))
times=[1.48]+[i/60. for i in range(89,104)]+[1.72]
frames=[];rows=[]
for seconds in times:
    pose=P.get_anim_pose_at_time(clip,seconds,options)
    points=[P.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD).translation for n in names]
    frame=u.M66SweepFrame();frame.set_editor_property('time',seconds);frame.set_editor_property('points',points)
    frames.append(frame);rows.append({'time':seconds,'points':[[p.x,p.y,p.z] for p in points]})
if not E.save_loaded_asset(clip,False):raise RuntimeError('M66 finalized slam save failed')
settings={'slam_clip':clip,'slam_frames':frames,'slam_reference_root':root,
          'slam_damage':135.,'slam_trigger_range':330.,'slam_hit_radius':32.,'slam_cooldown':6.}
for name,value in settings.items():cdo.set_editor_property(name,value)
E.set_metadata_tag(bp,'M66.GroundSlam','V13: full-chain Rampage ground smash; 3.5 s, contact 1.48-1.72 s; alternates with accepted sweep when reachable and ready')
u.BlueprintEditorLibrary.compile_blueprint(bp)
if not E.save_loaded_asset(bp,False):raise RuntimeError('M66 ground slam character save failed')
report={'complete':True,'saved':[clip.get_path_name(),bp.get_path_name()],'visual_mesh':mesh.get_path_name(),
        'frames':len(frames),'points_per_frame':len(names),'contact_seconds':[1.48,1.72],'duration_seconds':3.5,
        'physical_damage':135,'trigger_range_cm':330,'hit_radius_cm':32,'cooldown_seconds':6,'recovery_after_clip_seconds':1,
        'sweep_preserved':cdo.get_editor_property('sweep_clip').get_path_name(),
        'sweep_damage_preserved':cdo.get_editor_property('sweep_damage'),'back_smoke_enabled':cdo.get_editor_property('enable_back_smoke'),
        'server_authoritative':True,'runtime_tested':False,'multiplayer_tested':False,'rendered':False}
(ROOT/'Records/contact_samples.json').write_text(json.dumps({'bones':names,'frames':rows},indent=2),encoding='utf-8')
(ROOT/'Records/character_install.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M66_GROUND_SLAM_V13_SAVED '+json.dumps(report))
