"""Save only the three HK416 rear-grip repairs, keeping current finish bindings."""
import unreal as u,json,re
from pathlib import Path
O=Path(__file__).parent;D='/Game/Weapons/HK416/CommonAttachments20260930/Meshes'
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir())).resolve()!=(O.parents[1]/'Content').resolve():raise RuntimeError('Wrong project content')
models=json.loads((O/'models.json').read_text())['parts']
targets={D+'/'+part['name'] for part in models.values()}
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if targets & dirty:raise RuntimeError('Preserve unsaved rear-grip edits: '+str(sorted(targets & dirty)))
A=u.AssetToolsHelpers.get_asset_tools();receipt={'meshes':{},'runtime_tested':False}
canonical=lambda s:re.sub(r'[._]\d{3}$','',str(s))
flag='Interchange.FeatureFlags.Import.FBX';before=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 for key,part in models.items():
  path=D+'/'+part['name'];existing=u.load_asset(path)
  if not existing:raise RuntimeError('Missing live HK416 rear grip '+path)
  bindings={canonical(s.material_slot_name):s.material_interface for s in existing.get_editor_property('static_materials')}
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
  opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.override_full_name=True
  data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
  data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
  task=u.AssetImportTask();task.filename=part['file'];task.destination_path=D;task.destination_name=part['name']
  task.automated=True;task.replace_existing=True;task.save=False;task.options=opt;A.import_asset_tasks([task])
  mesh=u.load_asset(path);slots=list(mesh.get_editor_property('static_materials'))
  for i,slot in enumerate(slots):
   name=canonical(slot.material_slot_name)
   if name not in bindings or not bindings[name]:raise RuntimeError('Unknown/empty saved finish '+name)
   slot.material_interface=bindings[name];slots[i]=slot
  mesh.set_editor_property('static_materials',slots)
  u.EditorAssetLibrary.set_metadata_tag(mesh,'HK416RearGripInterface','20261001 native Hand_grip_low seat; closed continuous neck; original lower palm; no M4 tang/spacer')
  if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()],False):raise RuntimeError('Save failed '+path)
  receipt['meshes'][key]={'asset':mesh.get_path_name(),'source':part['file'],'materials':{str(s.material_slot_name):s.material_interface.get_path_name() for s in slots},'saved':True}
  (O/'import_receipt.json').write_text(json.dumps(receipt,indent=2))
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(before))
print('HK416_REARGRIP_REPAIR_SAVED',len(receipt['meshes']),flush=True)
