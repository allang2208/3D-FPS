import unreal,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/M4DrumGrip20260910/Revision5');DEST='/Game/Weapons/M4DrumDrop/Flow'
mesh=unreal.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416');assert mesh
report={}
for clip,length in [('reload',2.1),('reload_empty',2.7)]:
 name='A_M4_DrumFlow_'+clip
 options=unreal.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION
 options.skeleton=mesh.skeleton;options.import_materials=False;options.import_textures=False;options.create_physics_asset=False;options.import_mesh=False;options.import_animations=True
 options.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);options.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
 task=unreal.AssetImportTask();task.filename=str(O/(name+'.fbx'));task.destination_path=DEST;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=True;task.options=options
 unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);a=unreal.load_asset(DEST+'/'+name);assert a
 a.set_editor_property('bone_compression_settings',unreal.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));assert unreal.EditorAssetLibrary.save_loaded_asset(a,False)
 assert abs(a.get_play_length()-length)<.0001
 opt=unreal.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;err=0;step=0;previous=None
 for i in range(round(length*120)+1):
  opt.evaluation_type=unreal.AnimDataEvalType.RAW;p=unreal.AnimPoseExtensions.get_anim_pose_at_time(a,i/120,opt)
  opt.evaluation_type=unreal.AnimDataEvalType.COMPRESSED;q=unreal.AnimPoseExtensions.get_anim_pose_at_time(a,i/120,opt)
  for n in ['hand_l','hand_r','WPN_SOCKET_Magazine','lowerarm_twist_01_l','index_03_l','thumb_03_l']:
   x=unreal.AnimPoseExtensions.get_bone_pose(p,n,unreal.AnimPoseSpaces.WORLD);y=unreal.AnimPoseExtensions.get_bone_pose(q,n,unreal.AnimPoseSpaces.WORLD);err=max(err,x.translation.distance(y.translation))
 assert err<.05
 report[clip]={'asset':a.get_path_name(),'duration':a.get_play_length(),'keys':a.get_editor_property('number_of_sampled_keys'),'compression_error_cm':err,'source':task.filename}

(O/'import_report.json').write_text(json.dumps(report,indent=2));unreal.log('DRUM_WRIST_IMPORT_PASS')

