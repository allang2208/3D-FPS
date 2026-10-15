"""Install the retimed slam and regenerate impact-location samples at its new clock."""
import json,math
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/SlamImpactRhythmV16')
DEST='/Game/Monsters/IncineratorBossM66';E=u.EditorAssetLibrary;P=u.AnimPoseExtensions
if not globals().get('M66_COMMANDLET',False) and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('End PIE before saving the M66 fist slam')
if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('M66 packages have unsaved changes')
bp=u.load_asset(DEST+'/BP_M66RigPreview');clip=u.load_asset(DEST+'/SlamImpactRhythmV16/A_M66_FistSlam_V16')
if not bp or not clip:raise RuntimeError('M66 character or fist slam missing')
cdo=u.get_default_object(bp.generated_class());mesh=cdo.get_editor_property('visual_mesh')
if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Fist slam finalization failed')
options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.SOURCE;options.optional_skeletal_mesh=mesh
first=P.get_anim_pose_at_time(clip,0.,options);root=P.get_ref_bone_pose(first,'M66_Rig',u.AnimPoseSpaces.WORLD)
data=json.loads((ROOT/'Records/fist_contact_definition.json').read_text())
timing=json.loads((ROOT/'Records/timing_contract.json').read_text())
def sub(a,b):return [x-y for x,y in zip(a,b)]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
names=['Bone_037','Bone_036','Bone_065','Bone_061']
native=[data['source_reference_bones'][n] for n in names]
target=[P.get_ref_bone_pose(first,n,u.AnimPoseSpaces.WORLD).translation for n in names]
basis=[sub(v,native[0]) for v in native[1:]];det=dot(basis[0],cross(basis[1],basis[2]))
if abs(det)<1e-7:raise RuntimeError('Degenerate hand reference frame')
ref_wrist=P.get_ref_bone_pose(first,'Bone_037',u.AnimPoseSpaces.WORLD)
def native_to_wrist(point):
    delta=sub(point,native[0]);coeff=[dot(delta,cross(basis[1],basis[2]))/det,dot(basis[0],cross(delta,basis[2]))/det,dot(basis[0],cross(basis[1],delta))/det]
    mapped=target[0]
    for j,c in enumerate(coeff):mapped=mapped+(target[j+1]-target[0])*c
    return u.MathLibrary.inverse_transform_location(ref_wrist,mapped)
local_points=[native_to_wrist(p) for p in data['reference_points_source_m']]
start=timing['contact_start_seconds'];end=timing['impact_seconds'];fps=timing['fps']
times=[start]+[i/fps for i in range(math.floor(start*fps)+1,round(end*fps)+1)]
frames=[];rows=[]
for seconds in times:
    pose=P.get_anim_pose_at_time(clip,seconds,options);wrist=P.get_bone_pose(pose,'Bone_037',u.AnimPoseSpaces.WORLD)
    points=[u.MathLibrary.transform_location(wrist,p) for p in local_points]
    frame=u.M66SweepFrame();frame.set_editor_property('time',seconds);frame.set_editor_property('points',points)
    frames.append(frame);rows.append({'time':seconds,'points':[[p.x,p.y,p.z] for p in points]})
if not E.save_loaded_asset(clip,False):raise RuntimeError('Finalized fist slam save failed')
settings={'slam_clip':clip,'slam_frames':frames,'slam_reference_root':root,'slam_hit_radius':float(data['radius_cm'])}
for name,value in settings.items():cdo.set_editor_property(name,value)
E.set_metadata_tag(bp,'M66.GroundSlam','V16: nonlinear 0.15 s downstroke, impact at 1.50 s, 0.50 s grounded hold; V15 ground AOE and stun preserved')
u.BlueprintEditorLibrary.compile_blueprint(bp)
if not E.save_loaded_asset(bp,False):raise RuntimeError('M66 fist slam character save failed')
report={'complete':True,'saved':[clip.get_path_name(),bp.get_path_name()],'visual_mesh':mesh.get_path_name(),
    'frames':len(frames),'points_per_frame':len(local_points),'hit_radius_cm':data['radius_cm'],'contact_seconds':[start,end],
    'impact_seconds':end,'ground_hold_seconds':timing['ground_hold_seconds'],'duration_seconds':timing['end_seconds'],
    'physical_damage':cdo.get_editor_property('slam_damage'),'trigger_range_cm':cdo.get_editor_property('slam_trigger_range'),
    'cooldown_seconds':cdo.get_editor_property('slam_cooldown'),'stopping_distance_cm':cdo.get_editor_property('stopping_distance'),
    'sweep_preserved':cdo.get_editor_property('sweep_clip').get_path_name(),'back_smoke_enabled':cdo.get_editor_property('enable_back_smoke'),
    'wave_radius_cm':cdo.get_editor_property('slam_area_radius'),'wave_expansion_seconds':cdo.get_editor_property('slam_wave_seconds'),
    'stun_seconds':cdo.get_editor_property('slam_stun_seconds'),'wave_material':cdo.get_editor_property('slam_wave_material').get_path_name(),
    'server_authoritative':True,'native_source_changed':True,'runtime_tested':False,'multiplayer_tested':False,'rendered':False}
(ROOT/'Records/contact_samples.json').write_text(json.dumps({'frames':rows},indent=2))
(ROOT/'Records/character_install.json').write_text(json.dumps(report,indent=2))
print('M66_SLAM_RHYTHM_V16_SAVED '+json.dumps(report))
