"""Publish only the three standard M4 clips after candidate mesh review.
Leave the parallel drum-grip candidate assets and C++ untouched.
"""
import unreal,json,hashlib,shutil
from pathlib import Path
O=Path(__file__).resolve().parent;project=O.parents[1];destination='/Game/Weapons/M4ContactImpactFinal';report={}
backup=O/'Before';backup.mkdir(exist_ok=True)
mesh=unreal.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416');assert mesh
for clip in ['reload','reload_empty','equip_charge']:
 name='A_M4_HK416_'+clip;file=project/'Content/Weapons/M4ContactImpactFinal'/(name+'.uasset');saved=backup/file.name
 if not saved.exists():shutil.copy2(project/'Content/Weapons/M4ReloadPolish'/file.name,saved)
 task=unreal.AssetImportTask();task.filename=str(O/('A_M4_MAT_'+clip+'.fbx'));task.destination_path=destination;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=True
 options=unreal.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION;options.skeleton=mesh.skeleton;options.import_mesh=False;options.import_animations=True;options.import_materials=False;options.import_textures=False;options.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);options.anim_sequence_import_data.set_editor_property('custom_sample_rate',240);task.options=options
 unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);a=unreal.load_asset(destination+'/'+name);assert a
 a.set_editor_property('bone_compression_settings',unreal.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));assert unreal.EditorAssetLibrary.save_loaded_asset(a,False)
 report[clip]={'path':a.get_path_name(),'duration':a.get_play_length(),'before_sha256':hashlib.sha256(saved.read_bytes()).hexdigest(),'after_sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
 report[clip]['keys']=a.get_editor_property('number_of_sampled_keys');assert report[clip]['keys']==round(a.get_play_length()*240)+1
 opt=unreal.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;err=0
 for f in range(round(a.get_play_length()*480)+1):
  opt.evaluation_type=unreal.AnimDataEvalType.RAW;raw=unreal.AnimPoseExtensions.get_anim_pose_at_time(a,f/480,opt);opt.evaluation_type=unreal.AnimDataEvalType.COMPRESSED;packed=unreal.AnimPoseExtensions.get_anim_pose_at_time(a,f/480,opt)
  for n in ['hand_l','index_03_l','thumb_03_l','WPN_SOCKET_Magazine','WPN_ChargingHandle']:
   x=unreal.AnimPoseExtensions.get_bone_pose(raw,n,unreal.AnimPoseSpaces.WORLD);y=unreal.AnimPoseExtensions.get_bone_pose(packed,n,unreal.AnimPoseSpaces.WORLD);err=max(err,x.translation.distance(y.translation))
 assert err<.01,(clip,err);report[clip]['compression_error_cm']=err
# Keep the 12 mm support-hand clearance identical in idle/aim/fire and action ends.
lib=unreal.AnimPoseExtensions;mathlib=unreal.MathLibrary
opt=unreal.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.evaluation_type=unreal.AnimDataEvalType.RAW
relative=[]
for path in ['/Game/Weapons/M4ReloadPolish/A_M4_HK416_reload',destination+'/A_M4_HK416_reload']:
 pose=lib.get_anim_pose_at_time(unreal.load_asset(path),0,opt);root=lib.get_bone_pose(pose,'WPN_root',unreal.AnimPoseSpaces.WORLD);hand=lib.get_bone_pose(pose,'hand_l',unreal.AnimPoseSpaces.WORLD)
 relative.append(mathlib.inverse_transform_location(root,hand.translation))
shift=relative[1]-relative[0];assert .009<shift.length()<.015,shift
report['support_hand_offset_weapon_units']=[shift.x,shift.y,shift.z]
for name in ['A_AKM_idle','A_AKM_aim','A_AKM_fire','A_AKM_aim_fire']:
 src=unreal.load_asset('/Game/Weapons/M4InfimaRigV4/'+name);assert src
 a=unreal.load_asset(destination+'/'+name) or unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(name,destination,src);assert a
 count=src.get_editor_property('number_of_sampled_keys');positions=[];rotations=[];scales=[];expected=[]
 for k in range(count):
  t=src.get_play_length()*k/max(1,count-1);pose=lib.get_anim_pose_at_time(src,t,opt);root=lib.get_bone_pose(pose,'WPN_root',unreal.AnimPoseSpaces.WORLD);world=lib.get_bone_pose(pose,'clavicle_l',unreal.AnimPoseSpaces.WORLD);local=lib.get_bone_pose(pose,'clavicle_l',unreal.AnimPoseSpaces.LOCAL)
  parent=mathlib.compose_transforms(mathlib.invert_transform(local),world);offset=mathlib.transform_location(root,shift)-root.translation;positions.append(mathlib.inverse_transform_location(parent,world.translation+offset));rotations.append(local.rotation);scales.append(local.scale3d)
  hand=lib.get_bone_pose(pose,'hand_l',unreal.AnimPoseSpaces.WORLD);expected.append(hand.translation+offset)
 controller=a.get_editor_property('controller');assert controller
 controller.open_bracket('Support palm clears magazine rim',False);assert controller.set_bone_track_keys('clavicle_l',positions,rotations,scales,False);controller.close_bracket(False)
 a.set_editor_property('bone_compression_settings',unreal.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));assert unreal.EditorAssetLibrary.save_loaded_asset(a,False)
 error=0
 for k in range(count):
  pose=lib.get_anim_pose_at_time(a,a.get_play_length()*k/max(1,count-1),opt);hand=lib.get_bone_pose(pose,'hand_l',unreal.AnimPoseSpaces.WORLD);error=max(error,hand.translation.distance(expected[k]))
 assert error<.05,(name,error);report[name]={'path':a.get_path_name(),'duration':a.get_play_length(),'keys':count,'hand_world_error_cm':error}
(O/'publish_report.json').write_text(json.dumps(report,indent=2));unreal.log('M4_CONTACT_IMPACT_PUBLISHED')
