"""Publish only the three standard M4 clips after candidate mesh review.
Leave the parallel drum-grip candidate assets and C++ untouched.
"""
import unreal,json,hashlib,shutil
from pathlib import Path
O=Path(__file__).resolve().parent;project=O.parents[1];destination='/Game/Weapons/M4HK416Replica';report={}
backup=O/'Before';backup.mkdir(exist_ok=True)
mesh=unreal.load_asset(destination+'/SK_M4_FoldingSights_HK416');assert mesh
for clip in ['reload','reload_empty','equip_charge']:
 name='A_M4_HK416_'+clip;file=project/'Content/Weapons/M4HK416Replica'/(name+'.uasset');saved=backup/file.name
 if not saved.exists():shutil.copy2(file,saved)
 task=unreal.AssetImportTask();task.filename=str(O/('A_M4_MAT_'+clip+'.fbx'));task.destination_path=destination;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=True
 options=unreal.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION;options.skeleton=mesh.skeleton;options.import_mesh=False;options.import_animations=True;options.import_materials=False;options.import_textures=False;options.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);options.anim_sequence_import_data.set_editor_property('custom_sample_rate',60);task.options=options
 unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);a=unreal.load_asset(destination+'/'+name);assert a
 a.set_editor_property('bone_compression_settings',unreal.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));unreal.EditorAssetLibrary.save_loaded_asset(a,False)
 report[clip]={'path':a.get_path_name(),'duration':a.get_play_length(),'before_sha256':hashlib.sha256(saved.read_bytes()).hexdigest(),'after_sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
(O/'publish_report.json').write_text(json.dumps(report,indent=2));unreal.log('M4_HAND_REPAIR_PUBLISHED')
