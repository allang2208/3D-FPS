"""Retarget the complete biped donor used by the current Hundred-Eyed Slag sweep."""
import unreal as u,json,math
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'V12HundredEyeSweep'
for folder in ['Records','Motion','Authoring','Exports']:(P/folder).mkdir(parents=True,exist_ok=True)
BASE='/Game/Monsters/NightWarden';DEST=BASE+'/V09Melee/HundredEyeSweepV12';RIG=DEST+'/Rig';E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
 if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Preserve active PIE')
 if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved V07 assets')
bp=u.load_asset(BASE+'/BP_NightWarden');cdo=u.get_default_object(bp.generated_class())
target=cdo.get_editor_property('mesh').get_editor_property('skeletal_mesh')
source=u.load_asset('/Game/ParagonRampage/Characters/Heroes/Rampage/Meshes/Rampage')
slag=u.get_default_object(u.HundredEyedSlagMonster)
slag_clip=next(v for k,v in slag.get_editor_property('clips').items() if str(k)=='AttackSweep_R')
clip_path='/Game/ParagonRampage/Characters/Heroes/Rampage/Animations/Attack_Biped_Melee_A';clip=u.load_asset(clip_path)
if not target or not source or not clip:raise RuntimeError('Original body or unarmed motion source missing')
def save(o):
 if not E.save_loaded_asset(o,False):raise RuntimeError('Save failed '+o.get_path_name())
def create(name,cls,factory):return u.load_asset(RIG+'/'+name) if E.does_asset_exist(RIG+'/'+name) else A.create_asset(name,RIG,cls,factory)
src_chains={'Spine':('spine_01','spine_03'),'Neck':('neck_01','neck_02'),'Head':('head','head')}
dst_chains={'Spine':('Bone_005','Bone_002'),'Neck':('Bone_018','Bone_017'),'Head':('Bone_016','Bone_016')}
for side,label,clav,arm,wrist,thigh,foot,toe in [('l','Left','023','022','020','010','008','007'),('r','Right','028','027','025','015','013','012')]:
 for name,a,b,ta,tb in [('Clavicle','clavicle','clavicle',clav,clav),('Arm','upperarm','hand',arm,wrist),('Leg','thigh','foot',thigh,foot),('Toe','ball','ball',toe,toe)]:
  src_chains[name+label]=(a+'_'+side,b+'_'+side);dst_chains[name+label]=('Bone_'+ta,'Bone_'+tb)
def ik(name,mesh,pelvis,chains):
 asset=create(name,u.IKRigDefinition,u.IKRigDefinitionFactory());ctl=u.IKRigController.get_controller(asset);ctl.set_skeletal_mesh(mesh);ctl.set_retarget_root(pelvis)
 existing={str(c.chain_name) for c in ctl.get_retarget_chains()}
 for name,(first,last) in chains.items():
  if name not in existing:ctl.add_retarget_chain(name,first,last,'')
 save(asset);return asset
sr=ik('IK_NW12_RampageSource',source,'pelvis',src_chains);tr=ik('IK_NW12_OriginalBody',target,'Bone_001',dst_chains)
rt=create('RTG_NW12_HundredEyeSweep',u.IKRetargeter,u.IKRetargetFactory());ctl=u.IKRetargeterController.get_controller(rt)
ctl.set_ik_rig(u.RetargetSourceOrTarget.SOURCE,sr);ctl.set_ik_rig(u.RetargetSourceOrTarget.TARGET,tr)
ctl.set_preview_mesh(u.RetargetSourceOrTarget.SOURCE,source);ctl.set_preview_mesh(u.RetargetSourceOrTarget.TARGET,target)
if ctl.get_num_retarget_ops()==0:ctl.add_default_ops()
ctl.auto_map_chains(u.AutoMapChainType.EXACT,True)
for i in range(ctl.get_num_retarget_ops()):
 op=ctl.get_op_controller(i)
 if isinstance(op,u.IKRetargetFKChainsController):
  settings=op.get_settings();rows=list(settings.chains_to_retarget)
  for row in rows:
   if str(row.target_chain_name).startswith(('Arm','Leg')):row.rotation_mode=u.FKChainRotationMode.ONE_TO_ONE
  settings.chains_to_retarget=rows;op.set_settings(settings)
 if isinstance(op,u.IKRetargetRootMotionController):
  op.set_source_root_bone('root');op.set_target_root_bone('NW7_Root');op.set_target_pelvis_bone('Bone_001')
# Register the two whole-skeleton headings before aligning individual chains.
# AutoAlignAllBones resets the root offset, so use AutoAlignBones here instead.
source_options=u.AnimPoseEvaluationOptions();source_options.evaluation_type=u.AnimDataEvalType.RAW;source_options.optional_skeletal_mesh=source
source_pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,0.,source_options)
left=u.AnimPoseExtensions.get_ref_bone_pose(source_pose,'upperarm_l',u.AnimPoseSpaces.WORLD).translation;right=u.AnimPoseExtensions.get_ref_bone_pose(source_pose,'upperarm_r',u.AnimPoseSpaces.WORLD).translation
body_source=json.loads((P.parent/'Records/source_structure.json').read_text(encoding='utf-8'))
heads={b['name']:b['head_world'] for b in body_source['armatures'][0]['bones']};l,r=heads['Bone_022'],heads['Bone_027']
target_x=-(l[1]-r[1]);target_y=-(l[0]-r[0]);heading_degrees=math.degrees(math.atan2(left.y-right.y,left.x-right.x)-math.atan2(target_y,target_x))
pose_name=ctl.create_retarget_pose('RampageBodyHeadingAligned',u.RetargetSourceOrTarget.TARGET);ctl.set_current_retarget_pose(pose_name,u.RetargetSourceOrTarget.TARGET)
ctl.set_rotation_offset_for_retarget_pose_bone('NW7_Root',u.Rotator(pitch=0.,yaw=heading_degrees,roll=0.).quaternion(),u.RetargetSourceOrTarget.TARGET)
alignment_bones=['Bone_%03d'%i for i in list(range(2,6))+list(range(6,29))]
ctl.auto_align_bones(alignment_bones,u.RetargetAutoAlignMethod.CHAIN_TO_CHAIN,u.RetargetSourceOrTarget.TARGET);save(rt)
params=u.IKRetargetBatchOperationInputs();params.assets_to_retarget=[E.find_asset_data(clip_path)];params.source_mesh=source;params.target_mesh=target;params.ik_retarget_asset=rt
params.search=clip.get_name();params.replace='A_NW12_Rampage_Native';params.target_path=DEST+'/MotionSourceAligned';params.include_referenced_assets=False;params.overwrite_existing_files=True
assets=u.IKRetargetBatchOperation.run_batch_retarget(params);raw=next((x.get_asset() for x in assets if isinstance(x.get_asset(),u.AnimSequence)),None)
if not raw:raise RuntimeError('Native retarget produced no sequence')
u.SystemLibrary.execute_console_command(None,'NightWarden.FinishMotion "'+raw.get_path_name()+'"')
raw.set_preview_skeletal_mesh(target)
for prop in ['enable_root_motion','force_root_lock']:
 if raw.get_editor_property(prop):raw.set_editor_property(prop,False)
u.SystemLibrary.execute_console_command(None,'NightWarden.FinishMotion "'+raw.get_path_name()+'"');save(raw);save(target.skeleton)
component=u.new_object(u.SkeletalMeshComponent);component.set_skeletal_mesh_asset(target);bones=[str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.RAW;options.optional_skeletal_mesh=target
def pack(t):return {'p':[t.translation.x,t.translation.y,t.translation.z],'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':[t.scale3d.x,t.scale3d.y,t.scale3d.z]}
frames=[];length=raw.get_play_length()
for i in range(round(length*60)+1):
 pose=u.AnimPoseExtensions.get_anim_pose_at_time(raw,min(i/60,length),options)
 frames.append({n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in bones})
reference={n:pack(u.AnimPoseExtensions.get_ref_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in bones}
local_ref={n:pack(u.AnimPoseExtensions.get_ref_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in bones}
parents={n:str(component.get_parent_bone(n)) for n in bones}
(P/'Motion/native_attack.json').write_text(json.dumps({'fps':60,'duration':length,'heading_registration_degrees':heading_degrees,'source_asset':clip_path,'native_asset':raw.get_path_name(),'hundred_eye_asset':slag_clip.get_path_name(),'hundred_eye_duration':slag_clip.get_play_length(),'reference':reference,'reference_local':local_ref,'parents':parents,'frames':frames}),encoding='utf-8')
report={'stage':'native_motion_source_saved','source':clip_path,'native_asset':raw.get_path_name(),'retargeter':rt.get_path_name(),'duration':length,'heading_registration_degrees':heading_degrees,'frames':len(frames),'target_mesh':target.get_path_name(),'hundred_eye_asset':slag_clip.get_path_name(),'hundred_eye_duration':slag_clip.get_play_length(),'source_spine_end':'spine_03','limb_mapping':'Same three anatomical joints; Rampage twist and muscle bones are side branches, not inserted into the main chain','game_tested':False}
(P/'Records/native_retarget.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('NW12_RAMPAGE_NATIVE_SAVED '+json.dumps(report))
