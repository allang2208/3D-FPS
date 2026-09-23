import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;D='/Game/Weapons/PKMLowpoly20260922/Accessories14/Meshes'
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('End PIE before PKM rear-grip import')
report=json.loads((O/'reargrips_import.json').read_text()) if (O/'reargrips_import.json').exists() else {}
spec=json.loads((O/'reargrips.json').read_text());A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 for key,info in spec.items():
  if key in report:continue
  path=D+'/'+info['name'];mesh=u.load_asset(path)
  if not mesh:raise RuntimeError('Missing current PKM grip '+path)
  bindings={str(s.material_slot_name):s.material_interface for s in mesh.static_materials}
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.set_editor_property('reset_to_fbx_on_material_conflict',True)
  d=opt.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False;d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;d.vertex_color_import_option=u.VertexColorImportOption.REPLACE
  t=u.AssetImportTask();t.filename=str(O/'Exports'/(info['name']+'.fbx'));t.destination_path=D;t.destination_name=info['name'];t.options=opt;t.factory=u.FbxFactory();t.automated=True;t.replace_existing=True;t.replace_existing_settings=True;t.save=False
  A.import_asset_tasks([t]);mesh=u.load_asset(path)
  if not t.imported_object_paths:raise RuntimeError('Import failed '+key)
  slots=mesh.static_materials
  for i,s in enumerate(slots):s.material_interface=bindings[str(s.material_slot_name)];slots[i]=s
  mesh.set_editor_property('static_materials',slots);E.set_metadata_tag(mesh,'PKMContactRevision','GripContact15; factory receiver seat')
  if not E.save_loaded_asset(mesh,False):raise RuntimeError('Save failed '+key)
  report[key]={'asset':path,'materials':{n:m.get_path_name() for n,m in bindings.items()},'saved':True};(O/'reargrips_import.json').write_text(json.dumps(report,indent=2))
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
print('PKM15_REARGRIPS_SAVED')
