"""Replace only the ten M16 straight-magazine reload sequences."""
import unreal as u,json,shutil
from pathlib import Path
O=Path(__file__).parent;PROJECT=O.parent.parent;spec=json.loads((O/'transplant.json').read_text());E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();report={}
skeleton=u.load_asset('/Game/Weapons/M16A2/Gameplay20260919/SK_M16_Manny').skeleton
compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
for key,clip in spec['clips'].items():
 path=clip['folder']+'/'+clip['name'];old=u.load_asset(path)
 if not old:raise RuntimeError('Existing M16 reload missing: '+path)
 previous=list(old.get_editor_property('asset_import_data').extract_filenames())
 if not all('M16Refinement20260920' in p or 'M16M4Insert20260920' in p for p in previous):raise RuntimeError('Reload was changed to another source: '+path+' '+str(previous))
 original=PROJECT/'Content'/(path.removeprefix('/Game/')+'.uasset');backup=O/'PreviousAssets'/(path.removeprefix('/Game/')+'.uasset')
 if original.exists() and not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(original,backup)
 options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;options.import_mesh=False;options.import_animations=True;options.import_materials=False;options.import_textures=False;options.skeleton=skeleton
 data=options.anim_sequence_import_data;data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',120)
 task=u.AssetImportTask();task.filename=clip['file'];task.destination_path=clip['folder'];task.destination_name=clip['name'];task.automated=True;task.replace_existing=True;task.save=False;task.options=options
 A.import_asset_tasks([task]);anim=u.load_asset(path)
 anim.set_editor_property('bone_compression_settings',compression)
 E.set_metadata_tag(anim,'M16ReloadSource','Current M4 ExtMagContact full-arm and magazine insertion; M16 native seat; original empty charge from frame 111')
 E.save_loaded_asset(anim,False)
 report[key]={'asset':anim.get_path_name(),'imported_objects':list(task.imported_object_paths),'duration':anim.get_play_length(),'previous_source':previous,'source':clip['file']}
 (O/'installation.json').write_text(json.dumps(report,indent=2));print('M16_M4_INSERT_IMPORTED',key,flush=True)
print('M16_M4_INSERT_INSTALL_COMPLETE',len(report))
