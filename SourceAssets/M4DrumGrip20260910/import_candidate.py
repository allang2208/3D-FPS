import unreal,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/M4DrumGrip20260910');DEST='/Game/Weapons/M4DrumGripCandidate'
old=unreal.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416');assert old
def imp(name,mesh=False):
 o=unreal.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=unreal.FBXImportType.FBXIT_SKELETAL_MESH if mesh else unreal.FBXImportType.FBXIT_ANIMATION
 o.skeleton=old.skeleton;o.import_materials=False;o.import_textures=False;o.create_physics_asset=False;o.import_mesh=mesh;o.import_as_skeletal=mesh;o.import_animations=not mesh
 if not mesh:o.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);o.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
 t=unreal.AssetImportTask();t.filename=str(O/(name+'.fbx'));t.destination_path=DEST;t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=True;t.options=o
 unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);a=unreal.load_asset(DEST+'/'+name);assert a;return a
mesh=imp('SK_M4_DrumGripPreview',True)
materials={str(m.material_slot_name):m.material_interface for m in old.materials}
drum=unreal.load_asset('/Game/Weapons/M4Drum/SM_M4_LargeDrum')
for m in drum.static_materials:materials[str(m.material_slot_name)]=m.material_interface
slots=mesh.materials
for i,m in enumerate(slots):
 if str(m.material_slot_name) in materials:m.material_interface=materials[str(m.material_slot_name)];slots[i]=m
mesh.set_editor_property('materials',slots);unreal.EditorAssetLibrary.save_loaded_asset(mesh,False)
report={}
for clip,length in [('reload',2.1),('reload_empty',2.7)]:
 a=imp('A_M4_DrumGrip_'+clip);a.set_editor_property('bone_compression_settings',unreal.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));unreal.EditorAssetLibrary.save_loaded_asset(a,False)
 assert abs(a.get_play_length()-length)<.0001
 opt=unreal.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=old
 err=0
 for i in range(round(length*120)+1):
  opt.evaluation_type=unreal.AnimDataEvalType.RAW;p=unreal.AnimPoseExtensions.get_anim_pose_at_time(a,i/120,opt)
  opt.evaluation_type=unreal.AnimDataEvalType.COMPRESSED;q=unreal.AnimPoseExtensions.get_anim_pose_at_time(a,i/120,opt)
  for n in ['hand_l','hand_r','WPN_SOCKET_Magazine','index_03_l','thumb_03_l']:
   x=unreal.AnimPoseExtensions.get_bone_pose(p,n,unreal.AnimPoseSpaces.WORLD);y=unreal.AnimPoseExtensions.get_bone_pose(q,n,unreal.AnimPoseSpaces.WORLD);err=max(err,x.translation.distance(y.translation))
 assert err<.05
 report[clip]={'duration':a.get_play_length(),'keys':a.get_editor_property('number_of_sampled_keys'),'compression_error_cm':err}
(O/'import_report.json').write_text(json.dumps(report,indent=2));unreal.log('DRUM_GRIP_IMPORT_PASS')
