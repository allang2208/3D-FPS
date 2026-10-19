"""Bind the sweep and author its contact samples from the imported UE sequence."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/ClawSweepV04')
DEST='/Game/Monsters/IncineratorBossM66';E=u.EditorAssetLibrary;P=u.AnimPoseExtensions
if not globals().get('M66_COMMANDLET',False) and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('End PIE before saving M66 attack defaults')
if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('M66 packages have unsaved changes')
mesh=u.load_asset(DEST+'/RigV01/SK_M66_BackCompleted')
clip=u.load_asset(DEST+'/ClawSweepV04/A_M66_ClawSweep_V04')
bp=u.load_asset(DEST+'/BP_M66RigPreview')
if not mesh or not clip or not bp:raise RuntimeError('M66 mesh, animation or Blueprint missing')
if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('M66 animation finalization failed')
# Finalization marks the sequence dirty; persist it before the next batch step.
if not E.save_loaded_asset(clip,False):raise RuntimeError('M66 finalized attack animation save failed')
opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=u.AnimDataEvalType.SOURCE;opt.optional_skeletal_mesh=mesh
first=P.get_anim_pose_at_time(clip,0.,opt)
root=P.get_ref_bone_pose(first,'M66_Rig',u.AnimPoseSpaces.WORLD)
names=['Bone_025','Bone_036']
for finger in (57,61,65,69,73):names.extend('Bone_%03d'%i for i in (finger,finger-2,finger-3))
available={str(n) for n in P.get_bone_names(first)}
if not set(names).issubset(available):raise RuntimeError('M66 contact bones are missing: '+str(set(names)-available))
frames=[];rows=[]
for index in range(60,82):
    seconds=index/60.;pose=P.get_anim_pose_at_time(clip,seconds,opt)
    points=[P.get_bone_pose(pose,name,u.AnimPoseSpaces.WORLD).translation for name in names]
    frame=u.M66SweepFrame();frame.set_editor_property('time',seconds);frame.set_editor_property('points',points)
    frames.append(frame);rows.append({'time':seconds,'points':[[v.x,v.y,v.z] for v in points]})
u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
for key,value in {'sweep_clip':clip,'sweep_frames':frames,'sweep_reference_root':root,
    'sweep_damage':40.,'sweep_trigger_range':300.,'sweep_hit_radius':16.,'sweep_cooldown':3.6,
    'stopping_distance':230.}.items():cdo.set_editor_property(key,value)
E.set_metadata_tag(bp,'M66.Stage','Attack 01 claw sweep, locomotion/navigation and reactions; remaining boss modes are not authored')
E.set_metadata_tag(bp,'M66.Attack01','2.6 seconds; contact 1.00-1.35; fixed facing; authoritative clock and imported hand path')
u.BlueprintEditorLibrary.compile_blueprint(bp)
if not E.save_loaded_asset(bp,False):raise RuntimeError('M66 attack Blueprint save failed')
report={'complete':True,'saved':[clip.get_path_name(),bp.get_path_name()],
    'sample_frames':len(frames),'points_per_frame':len(names),'sample_bones':names,
    'contact_seconds':[1.,1.35],'duration_seconds':2.6,'cooldown_seconds':3.6,
    'damage':40.,'start_range_cm':300.,'stop_range_cm':230.,'hit_radius_cm':16.,
    'f6_entry_id':'IncineratorBossM66Rig','f6_label':'焚骸 M-35（拢灰指扫）',
    'server_authoritative':True,'runtime_tested':False,'multiplayer_tested':False}
(ROOT/'Records/contact_samples.json').write_text(json.dumps({'bones':names,'frames':rows},indent=2),encoding='utf-8')
(ROOT/'Records/character_install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('M66_CLAW_SWEEP_SAVED '+json.dumps(report,ensure_ascii=False))
