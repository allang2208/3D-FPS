"""Import the ten authored AKM-only clips into the running editor."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).resolve().parents[1]
build=json.loads((O/'build_receipt.json').read_text())
sources=json.loads((O/'source_manifest.json').read_text())
E=u.EditorAssetLibrary
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Stop PIE before importing animation assets')
report_file=O/'import_receipt.json'
report=json.loads(report_file.read_text()) if report_file.exists() else {}
for key,meta in build.items():
 if report.get(key,{}).get('saved') and report[key].get('revision')==meta.get('revision'):continue
 folder,name=meta['asset'].rsplit('/',1)
 opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
 opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
 opt.skeleton=u.load_asset(sources[key]['skeleton']);opt.import_mesh=False;opt.import_animations=True
 opt.import_materials=False;opt.import_textures=False
 opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
 opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
 task=u.AssetImportTask();task.filename=meta['fbx'];task.destination_path=folder;task.destination_name=name
 task.options=opt;task.automated=True;task.replace_existing=True;task.save=False
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
 if not task.imported_object_paths:raise RuntimeError('No imported object: '+key)
 a=u.load_asset(meta['asset'])
 if not a:raise RuntimeError('Import failed '+key)
 a.set_editor_property('bone_compression_settings',u.load_asset(sources[key]['compression']))
 # Complete compression as part of preparing the imported runtime resource.
 u.AKMAnimationAuditLibrary.finish_animation_compression(a)
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+key)
 report[key]={'asset':a.get_path_name(),'saved':True,'revision':meta.get('revision'),'source':meta['fbx'],'game_tested':False}
 report_file.write_text(json.dumps(report,indent=2),encoding='utf-8')
 print('AKM_FREE_DROP_SAVED '+key)
print('AKM_FREE_DROP_IMPORT_COMPLETE '+str(len(report)))
