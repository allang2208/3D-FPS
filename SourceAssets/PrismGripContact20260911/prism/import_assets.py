import unreal,json
from pathlib import Path
O=Path(__file__).parent;DEST='/Game/Weapons/M4PrismHorizontalGrip'
mesh=unreal.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416');assert mesh
report={}
references={
 'idle':'M4ContactImpactFinal/A_AKM_idle','aim':'M4ContactImpactFinal/A_AKM_aim',
 'fire':'M4ContactImpactFinal/A_AKM_fire','aim_fire':'M4ContactImpactFinal/A_AKM_aim_fire',
 'equip':'M4WrapGripFinal/A_M4_HK416_equip_charge',
 'reload':'M4TacticalTossFinal/A_M4_HK416_reload','reload_empty':'M4SlapImpactFinal/A_M4_HK416_reload_empty',
 'drum_reload':'M4DrumDrop/Contact/A_M4_DrumContact_reload','drum_reload_empty':'M4DrumDrop/Contact/A_M4_DrumContact_reload_empty'}
for clip,info in json.loads((O/'animation_build.json').read_text()).items():
 name='A_M4_Prism_'+clip;options=unreal.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION;options.skeleton=mesh.skeleton;options.import_materials=False;options.import_textures=False;options.create_physics_asset=False;options.import_mesh=False;options.import_animations=True
 options.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);options.anim_sequence_import_data.set_editor_property('custom_sample_rate',info['sample_rate'])
 task=unreal.AssetImportTask();task.filename=str(O/(name+'.fbx'));task.destination_path=DEST;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=True;task.options=options
 unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);a=unreal.load_asset(DEST+'/'+name);assert a
 a.set_editor_property('bone_compression_settings',unreal.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));assert unreal.EditorAssetLibrary.save_loaded_asset(a,False);assert abs(a.get_play_length()-info['duration'])<.0001
 opt=unreal.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;err=0
 for k in range(round(info['duration']*60)+1):
  opt.evaluation_type=unreal.AnimDataEvalType.RAW;p=unreal.AnimPoseExtensions.get_anim_pose_at_time(a,k/60,opt)
  opt.evaluation_type=unreal.AnimDataEvalType.COMPRESSED;q=unreal.AnimPoseExtensions.get_anim_pose_at_time(a,k/60,opt)
  for n in ['hand_l','hand_r','WPN_SOCKET_Magazine','lowerarm_twist_01_l','index_03_l','thumb_03_l']:
   x=unreal.AnimPoseExtensions.get_bone_pose(p,n,unreal.AnimPoseSpaces.WORLD);y=unreal.AnimPoseExtensions.get_bone_pose(q,n,unreal.AnimPoseSpaces.WORLD);err=max(err,x.translation.distance(y.translation))
 assert err<.05,(clip,err)
 base=unreal.load_asset('/Game/Weapons/'+references[clip]);assert base
 unchanged_error=0;contact_error=0;opt.evaluation_type=unreal.AnimDataEvalType.RAW
 for frame in range(info['frames']+1):
  p=unreal.AnimPoseExtensions.get_anim_pose_at_time(a,frame/60,opt);q=unreal.AnimPoseExtensions.get_anim_pose_at_time(base,frame/60,opt)
  for n in ['WPN_root','hand_r','index_03_r','WPN_SOCKET_Magazine']:
   x=unreal.AnimPoseExtensions.get_bone_pose(p,n,unreal.AnimPoseSpaces.WORLD);y=unreal.AnimPoseExtensions.get_bone_pose(q,n,unreal.AnimPoseSpaces.WORLD);unchanged_error=max(unchanged_error,x.translation.distance(y.translation))
  interval=info.get('unchanged_contact_interval_frames')
  if interval and interval[0]<=frame<=interval[1]:
   for n in ['hand_l','index_03_l','thumb_03_l','lowerarm_l']:
    x=unreal.AnimPoseExtensions.get_bone_pose(p,n,unreal.AnimPoseSpaces.WORLD);y=unreal.AnimPoseExtensions.get_bone_pose(q,n,unreal.AnimPoseSpaces.WORLD);contact_error=max(contact_error,x.translation.distance(y.translation))
 report[clip]={'duration':a.get_play_length(),'compression_error_cm':err,'asset':a.get_path_name(),'reference':base.get_path_name(),'right_weapon_difference_cm':unchanged_error,'preserved_contact_difference_cm':contact_error}
 (O/'import_report.json').write_text(json.dumps(report,indent=2))
unreal.log('PRISM_IMPORT_PASS')
