"""Import the scoped M16 reload heads and complete melee arm chains."""
import unreal as u,json,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parent.parent;E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
spec=json.loads((O/'authoring.json').read_text());baseline=json.loads((O/'runtime_sources.json').read_text());expected={v['asset']:v['source'] for v in baseline.values()};report={}
skeleton=u.load_asset('/Game/Weapons/M16A2/Gameplay20260919/SK_M16_Manny').skeleton;compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
for key,clip in spec['clips'].items():
 path=clip['folder']+'/'+clip['name'];old=u.load_asset(path)
 if not old:raise RuntimeError('Missing target animation '+path)
 previous=list(old.get_editor_property('asset_import_data').extract_filenames())
 if previous!=expected[path] and not all('M16RemovalMelee20260920' in v for v in previous):raise RuntimeError('Animation source changed during authoring: '+path+' '+str(previous))
 original=P/'Content'/(path.removeprefix('/Game/')+'.uasset');backup=O/'PreviousAssets'/(path.removeprefix('/Game/')+'.uasset')
 if original.exists() and not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(original,backup)
 options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;options.import_mesh=False;options.import_animations=True;options.import_materials=False;options.import_textures=False;options.skeleton=skeleton
 data=options.anim_sequence_import_data;data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',120)
 task=u.AssetImportTask();task.filename=clip['file'];task.destination_path=clip['folder'];task.destination_name=clip['name'];task.automated=True;task.replace_existing=True;task.save=False;task.options=options
 A.import_asset_tasks([task])
 if not task.imported_object_paths:raise RuntimeError('Animation import returned no objects: '+path)
 anim=u.load_asset(path);anim.set_editor_property('bone_compression_settings',compression)
 E.set_metadata_tag(anim,'M16ArmSource','M16RemovalMelee20260920: current M4 complete removal/melee chains; previous insertion and empty charging retained')
 saved=E.save_loaded_asset(anim,False)
 if not saved:raise RuntimeError('Could not save '+path)
 report[key]={'asset':anim.get_path_name(),'source':clip['file'],'duration':anim.get_play_length(),'saved':saved,'previous_source':previous}
 (O/'installation.json').write_text(json.dumps(report,indent=2));print('M16_ARM_IMPORTED',key,flush=True)
print('M16_ARM_INSTALL_COMPLETE',len(report))
