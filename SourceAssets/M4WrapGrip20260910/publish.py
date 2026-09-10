"""Publish only the three standard M4 clips after candidate mesh review.
Leave the parallel drum-grip candidate assets and C++ untouched.
"""
import unreal,json,hashlib,shutil
from pathlib import Path
O=Path(__file__).resolve().parent;project=O.parents[1];destination='/Game/Weapons/M4WrapGripFinal';report={}
# Publish only the currently checked, natural-finger generation.
latest_fbx=max(p.stat().st_mtime for p in O.glob('A_M4_MAT_*.fbx'))
for check in ['triangle_contact_probe.json','mechanical_contract.json']:
 assert (O/check).stat().st_mtime>latest_fbx,('Stale candidate validation',check)
for rows in json.loads((O/'triangle_contact_probe.json').read_text()).values():
 assert all(row['triangle_pairs']==0 for row in rows)
assert 'natural_limits' in json.loads((O/'wrap_fit.json').read_text())
backup=O/'Before';backup.mkdir(exist_ok=True)
mesh=unreal.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416');assert mesh
for clip in ['reload','reload_empty','equip_charge']:
 name='A_M4_HK416_'+clip;file=project/'Content/Weapons/M4WrapGripFinal'/(name+'.uasset');saved=backup/file.name
 if not saved.exists():shutil.copy2(project/'Content/Weapons/M4AnimationAuditFinal'/file.name,saved)
 task=unreal.AssetImportTask();task.filename=str(O/('A_M4_MAT_'+clip+'.fbx'));task.destination_path=destination;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=True
 options=unreal.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION;options.skeleton=mesh.skeleton;options.import_mesh=False;options.import_animations=True;options.import_materials=False;options.import_textures=False;options.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);options.anim_sequence_import_data.set_editor_property('custom_sample_rate',480);task.options=options
 unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);a=unreal.load_asset(destination+'/'+name);assert a
 a.set_editor_property('bone_compression_settings',unreal.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));assert unreal.EditorAssetLibrary.save_loaded_asset(a,False)
 report[clip]={'path':a.get_path_name(),'duration':a.get_play_length(),'before_sha256':hashlib.sha256(saved.read_bytes()).hexdigest(),'after_sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
 report[clip]['keys']=a.get_editor_property('number_of_sampled_keys');assert report[clip]['keys']==round(a.get_play_length()*480)+1
 opt=unreal.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;err=0
 for f in range(round(a.get_play_length()*480)+1):
  opt.evaluation_type=unreal.AnimDataEvalType.RAW;raw=unreal.AnimPoseExtensions.get_anim_pose_at_time(a,f/480,opt);opt.evaluation_type=unreal.AnimDataEvalType.COMPRESSED;packed=unreal.AnimPoseExtensions.get_anim_pose_at_time(a,f/480,opt)
  for n in ['hand_l','index_03_l','thumb_03_l','WPN_SOCKET_Magazine','WPN_ChargingHandle']:
   x=unreal.AnimPoseExtensions.get_bone_pose(raw,n,unreal.AnimPoseSpaces.WORLD);y=unreal.AnimPoseExtensions.get_bone_pose(packed,n,unreal.AnimPoseSpaces.WORLD);err=max(err,x.translation.distance(y.translation))
 assert err<.01,(clip,err);report[clip]['compression_error_cm']=err

(O/'publish_report.json').write_text(json.dumps(report,indent=2));unreal.log('M4_WRAP_GRIP_PUBLISHED')
