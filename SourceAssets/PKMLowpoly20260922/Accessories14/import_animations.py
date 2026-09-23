"""Install one family's PKM grip clips, preserving the current private skeleton."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;D='/Game/Weapons/PKMLowpoly20260922/Accessories14'
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('End PIE before PKM animation import')
source=json.loads((O/'animations.json').read_text());report=json.loads((O/'animations_import.json').read_text()) if (O/'animations_import.json').exists() else {}
mesh=u.load_asset('/Game/Weapons/PKMLowpoly20260922/SK_PKM_Manny');A=u.AssetToolsHelpers.get_asset_tools()
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 for key,info in source.items():
  family,clip=key.split('/')
  if family!=FAMILY or key in report:continue
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.skeleton=mesh.skeleton
  opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',info['fps'])
  t=u.AssetImportTask();t.filename=str(O/'Animations'/family/(info['name']+'.fbx'));t.destination_path=D+'/Animations/'+family;t.destination_name=info['name'];t.options=opt;t.factory=u.FbxFactory();t.automated=True;t.replace_existing=True;t.save=False
  A.import_asset_tasks([t]);a=u.load_asset(t.destination_path+'/'+t.destination_name)
  if not a or not t.imported_object_paths:raise RuntimeError('Import failed '+key)
  a.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'))
  if not u.EditorAssetLibrary.save_loaded_asset(a,False):raise RuntimeError('Save failed '+key)
  report[key]={'asset':a.get_path_name(),'seconds':a.get_play_length(),'saved':True};(O/'animations_import.json').write_text(json.dumps(report,indent=2))
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
print('PKM14_GRIP_FAMILY_SAVED',FAMILY)
