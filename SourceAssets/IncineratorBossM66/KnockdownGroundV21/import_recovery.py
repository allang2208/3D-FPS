"""Import and save only the corrected landing/get-up clips on the existing M66."""
from pathlib import Path
import json,shutil,unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[2]
DEST='/Game/Monsters/IncineratorBossM66/KnockdownGroundV21';E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
manifest=json.loads((ROOT/'Records/animation_manifest.json').read_text('utf-8'))
bp=u.load_asset('/Game/Monsters/IncineratorBossM66/BP_M66RigPreview');cdo=u.get_default_object(bp.generated_class());mesh=cdo.get_editor_property('visual_mesh')
if any(p.get_name().startswith('/Game/Monsters/IncineratorBossM66/') for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve already-dirty M66 packages')
backup=ROOT/'Before';backup.mkdir(exist_ok=True)
bp_file=PROJECT/'Content/Monsters/IncineratorBossM66/BP_M66RigPreview.uasset'
if not (backup/bp_file.name).exists():shutil.copy2(bp_file,backup/bp_file.name)
preserved={k:cdo.get_editor_property(k).get_path_name() for k in ('visual_mesh','reaction_physics','air_clip','death_clip','sweep_clip','slam_clip','breath_clip')}
previous={k:cdo.get_editor_property(k).get_path_name() for k in ('land_clip','get_up_clip')}
report=dict(stage='importing',mesh=mesh.get_path_name(),preserved=preserved,previous=previous,saved=[],clips={},runtime_pose_samples={},runtime_poses={},game_tested=False,multiplayer_tested=False)
def transform(t):return dict(p=[t.translation.x,t.translation.y,t.translation.z],q=[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],s=[t.scale3d.x,t.scale3d.y,t.scale3d.z])
def record():(ROOT/'Records/import.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def save(asset):
 if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
 report['saved'].append(asset.get_path_name());record()
old=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX');u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
clips={};record()
try:
 for row in manifest['clips']:
  name='A_M66_'+row['role']+'_V21';path=DEST+'/'+name
  if E.does_asset_exist(path):raise RuntimeError('Preserve existing revision; use a new name if reauthoring: '+path)
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
  opt.import_as_skeletal=True;opt.import_mesh=False;opt.import_animations=True;opt.skeleton=mesh.skeleton
  opt.import_materials=False;opt.import_textures=False
  data=opt.anim_sequence_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.force_front_x_axis=True;data.import_uniform_scale=1.
  data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',60)
  data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
  task=u.AssetImportTask();task.filename=row['fbx'];task.destination_path=DEST;task.destination_name=name;task.automated=True;task.save=False;task.options=opt;task.factory=u.FbxFactory()
  A.import_asset_tasks([task]);clip=u.load_asset(path)
  if not clip or not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Animation import/compilation failed '+path)
  clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True);clip.set_editor_property('loop',False);clip.set_preview_skeletal_mesh(mesh)
  if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Animation finalization failed '+path)
  ev=u.AnimPoseEvaluationOptions();ev.evaluation_type=u.AnimDataEvalType.COMPRESSED;ev.optional_skeletal_mesh=mesh;ev.should_retarget=True;ev.extract_root_motion=False
  samples=[];full_poses=[]
  for t in (0.,row['seconds']*.25,row['seconds']*.5,row['seconds']*.75,row['seconds']):
   pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,ev)
   root=u.AnimPoseExtensions.get_bone_pose(pose,'M66_Rig',u.AnimPoseSpaces.LOCAL)
   if max(abs(v-100.) for v in (root.scale3d.x,root.scale3d.y,root.scale3d.z))>.01:raise RuntimeError('Imported root unit changed')
   pelvis=u.AnimPoseExtensions.get_bone_pose(pose,'Bone_000',u.AnimPoseSpaces.WORLD)
   samples.append(dict(time=t,pelvis_z_cm=pelvis.translation.z,root_scale=[root.scale3d.x,root.scale3d.y,root.scale3d.z]))
   full_poses.append(dict(time=t,bones={str(n):dict(component=transform(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)),reference=transform(u.AnimPoseExtensions.get_ref_bone_pose(pose,n,u.AnimPoseSpaces.WORLD))) for n in u.AnimPoseExtensions.get_bone_names(pose)}))
  if abs(clip.get_play_length()-row['seconds'])>.001:raise RuntimeError('Preserve the existing gameplay duration')
  E.set_metadata_tag(clip,'M66.Authoring','V21 body-supported landing and planted-palm recovery; current mesh and skin preserved')
  E.set_metadata_tag(clip,'M66.ReactionRole',row['role']);save(clip);clips[row['role']]=clip
  report['clips'][row['role']]=clip.get_path_name();report['runtime_pose_samples'][row['role']]=samples;report['runtime_poses'][row['role']]=full_poses;record()
 bp.modify();cdo.modify();cdo.set_editor_property('land_clip',clips['Landing']);cdo.set_editor_property('get_up_clip',clips['GetUp'])
 u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
 for key,value in preserved.items():
  if cdo.get_editor_property(key).get_path_name()!=value:raise RuntimeError('Unexpected preserved M66 property change: '+key)
 for key,role in (('land_clip','Landing'),('get_up_clip','GetUp')):
  if cdo.get_editor_property(key).get_path_name()!=clips[role].get_path_name():raise RuntimeError('Corrected reaction default was not retained: '+key)
 E.set_metadata_tag(bp,'M66.Recovery','V21 torso-supported landing, planted-palm recovery; existing authoritative phase clock and durations')
 save(bp);report['stage']='animations_and_original_character_saved';record()
 u.log('M66_KNOCKDOWN_V21_SAVED '+str(report['clips']))
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(old))
