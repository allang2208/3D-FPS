import unreal,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/M4DrumGrip20260910/Revision2');DEST='/Game/Weapons/M4DrumGripRebuilt'
mesh=unreal.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416');assert mesh
report={}
for clip,length in [('reload',2.1),('reload_empty',2.7)]:
 name='A_M4_DrumGrip_'+clip
 options=unreal.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION
 options.skeleton=mesh.skeleton;options.import_materials=False;options.import_textures=False;options.create_physics_asset=False;options.import_mesh=False;options.import_animations=True
 options.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);options.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
 task=unreal.AssetImportTask();task.filename=str(O/(name+'.fbx'));task.destination_path=DEST;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=True;task.options=options
 unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);a=unreal.load_asset(DEST+'/'+name);assert a
 a.set_editor_property('bone_compression_settings',unreal.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));unreal.EditorAssetLibrary.save_loaded_asset(a,False)
 assert abs(a.get_play_length()-length)<.0001
 opt=unreal.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;err=0;step=0;previous=None
 for i in range(round(length*120)+1):
  opt.evaluation_type=unreal.AnimDataEvalType.RAW;p=unreal.AnimPoseExtensions.get_anim_pose_at_time(a,i/120,opt)
  opt.evaluation_type=unreal.AnimDataEvalType.COMPRESSED;q=unreal.AnimPoseExtensions.get_anim_pose_at_time(a,i/120,opt)
  for n in ['hand_l','hand_r','WPN_SOCKET_Magazine','lowerarm_twist_01_l','index_03_l','thumb_03_l']:
   x=unreal.AnimPoseExtensions.get_bone_pose(p,n,unreal.AnimPoseSpaces.WORLD);y=unreal.AnimPoseExtensions.get_bone_pose(q,n,unreal.AnimPoseSpaces.WORLD);err=max(err,x.translation.distance(y.translation))
 assert err<.05
 report[clip]={'asset':a.get_path_name(),'duration':a.get_play_length(),'keys':a.get_editor_property('number_of_sampled_keys'),'compression_error_cm':err,'source':task.filename}
# The drum rim needs another 20 mm of support-hand clearance beyond the
# current standard-magazine pose. Keep those base clips private to the drum.
lib=unreal.AnimPoseExtensions;mathlib=unreal.MathLibrary
opt=unreal.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.evaluation_type=unreal.AnimDataEvalType.RAW
for name in ['A_AKM_idle','A_AKM_aim','A_AKM_fire','A_AKM_aim_fire','A_M4_HK416_equip_charge']:
 src=unreal.load_asset('/Game/Weapons/M4ContactImpactFinal/'+name);assert src
 a=unreal.load_asset(DEST+'/Support/'+name) or unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(name,DEST+'/Support',src);assert a
 count=src.get_editor_property('number_of_sampled_keys');positions=[];rotations=[];scales=[]
 for k in range(count):
  p=lib.get_anim_pose_at_time(src,src.get_play_length()*k/max(1,count-1),opt);root=lib.get_bone_pose(p,'WPN_root',unreal.AnimPoseSpaces.WORLD);world=lib.get_bone_pose(p,'clavicle_l',unreal.AnimPoseSpaces.WORLD);local=lib.get_bone_pose(p,'clavicle_l',unreal.AnimPoseSpaces.LOCAL)
  parent=mathlib.compose_transforms(mathlib.invert_transform(local),world);shift=mathlib.transform_location(root,unreal.Vector(0,.02,0))-root.translation
  positions.append(mathlib.inverse_transform_location(parent,world.translation+shift));rotations.append(local.rotation);scales.append(local.scale3d)
 controller=a.get_editor_property('controller');controller.open_bracket('Drum support clearance',False);assert controller.set_bone_track_keys('clavicle_l',positions,rotations,scales,False);controller.close_bracket(False)
 a.set_editor_property('bone_compression_settings',unreal.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));assert unreal.EditorAssetLibrary.save_loaded_asset(a,False)
 report[name]={'asset':a.get_path_name(),'duration':a.get_play_length(),'extra_support_shift_cm':2}
(O/'import_report.json').write_text(json.dumps(report,indent=2));unreal.log('DRUM_GRIP_REBUILT_IMPORT_PASS')
