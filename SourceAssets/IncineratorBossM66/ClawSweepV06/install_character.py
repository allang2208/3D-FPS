"""Save the corrected animation and replace only its authoritative contact samples."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/ClawSweepV06')
DEST='/Game/Monsters/IncineratorBossM66';E=u.EditorAssetLibrary;P=u.AnimPoseExtensions
if not globals().get('M66_COMMANDLET',False) and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('End PIE before saving M66 attack defaults')
if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('M66 packages have unsaved changes')
mesh=u.load_asset(DEST+'/SurfaceLifeV05/SK_M66_SurfaceLife_V05')
clip=u.load_asset(DEST+'/ClawSweepV06/A_M66_ClawSweep_V06')
bp=u.load_asset(DEST+'/BP_M66RigPreview')
if not mesh or not clip or not bp:raise RuntimeError('M66 current mesh, animation or Blueprint missing')
if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('M66 animation finalization failed')
if not E.save_loaded_asset(clip,False):raise RuntimeError('M66 finalized animation save failed')
options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.SOURCE;options.optional_skeletal_mesh=mesh
first=P.get_anim_pose_at_time(clip,0.,options)
reference_root=P.get_ref_bone_pose(first,'M66_Rig',u.AnimPoseSpaces.WORLD)
names=['Bone_037','Bone_036']
for finger in (57,61,65,69,73):names.extend('Bone_%03d'%i for i in (finger,finger-2,finger-3))
available={str(n) for n in P.get_bone_names(first)}
if not set(names).issubset(available):raise RuntimeError('M66 contact bones missing: '+str(set(names)-available))
frames=[];rows=[]
for index in range(60,82):
    seconds=index/60.;pose=P.get_anim_pose_at_time(clip,seconds,options)
    points=[P.get_bone_pose(pose,name,u.AnimPoseSpaces.WORLD).translation for name in names]
    frame=u.M66SweepFrame();frame.set_editor_property('time',seconds);frame.set_editor_property('points',points)
    frames.append(frame);rows.append({'time':seconds,'points':[[v.x,v.y,v.z] for v in points]})
u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
previous_clip=cdo.get_editor_property('sweep_clip')
for key,value in {'sweep_clip':clip,'sweep_frames':frames,'sweep_reference_root':reference_root}.items():
    cdo.set_editor_property(key,value)
E.set_metadata_tag(bp,'M66.Stage','V06 full-arm sweep on V05 skin; existing locomotion, life motion and reactions retained')
E.set_metadata_tag(bp,'M66.Attack01','Rampage sweep reference; anatomical wrist Bone_037; full forearm continuity and exterior recovery; original combat clock')
u.BlueprintEditorLibrary.compile_blueprint(bp)
if not E.save_loaded_asset(bp,False):raise RuntimeError('M66 attack Blueprint save failed')
report={'complete':True,'saved':[clip.get_path_name(),bp.get_path_name()],
    'previous_clip':previous_clip.get_path_name() if previous_clip else None,
    'sample_frames':len(frames),'points_per_frame':len(names),'sample_bones':names,
    'contact_seconds':[1.,1.35],'duration_seconds':2.6,'combat_balance_preserved':True,
    'visual_mesh_preserved':True,'locomotion_and_reactions_preserved':True,
    'f6_entry_id':'IncineratorBossM66Rig','runtime_tested':False,'multiplayer_tested':False}
(ROOT/'Records/contact_samples.json').write_text(json.dumps({'bones':names,'frames':rows},indent=2),encoding='utf-8')
(ROOT/'Records/character_install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('M66_CLAW_SWEEP_V06_SAVED '+json.dumps(report,ensure_ascii=False))
