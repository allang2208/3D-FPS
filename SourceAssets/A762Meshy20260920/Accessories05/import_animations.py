import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/A762/Accessories05/Animations';A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
mesh=u.load_asset('/Game/Weapons/A762/Integrated20260920/SK_A762_Manny');auth=json.loads((O/'animations.json').read_text())
receipt=json.loads((O/'animations_import.json').read_text()) if (O/'animations_import.json').exists() else {}
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 for key,info in auth.items():
  if key in receipt:continue
  family,clip=key.split('/');name=info['name'];opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
  opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opt.skeleton=mesh.skeleton;opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False
  opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',round(info['fps']))
  t=u.AssetImportTask();t.filename=str(O/'Animations'/family/(name+'.fbx'));t.destination_path=P+'/'+family;t.destination_name=name;t.options=opt;t.factory=u.FbxFactory();t.automated=True;t.replace_existing=True;t.save=False
  A.import_asset_tasks([t]);asset=u.load_asset(P+'/'+family+'/'+name)
  if not asset or not t.imported_object_paths:raise RuntimeError('Animation import failed '+key)
  asset.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'))
  if not E.save_loaded_asset(asset,False):raise RuntimeError('Animation save failed '+key)
  receipt[key]=asset.get_path_name();(O/'animations_import.json').write_text(json.dumps(receipt,indent=2))
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
u.log('A762_ACCESSORY_ANIMATIONS_IMPORTED_AND_SAVED')
