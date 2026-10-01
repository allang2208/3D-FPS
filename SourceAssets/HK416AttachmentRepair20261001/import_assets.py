"""Save the corrected HK416 stock geometry and factory-section identity."""
import unreal as u,json,re
from pathlib import Path
O=Path(__file__).parent;C=O.parent/'HK416CommonAttachments20260930'
H='/Game/Weapons/HK416/Reworked20260930';D='/Game/Weapons/HK416/CommonAttachments20260930'
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir())).resolve()!=(O.parents[1]/'Content').resolve():raise RuntimeError('Wrong project content')
models=json.loads((O/'stock_models.json').read_text()); prior=json.loads((O/'actual_assets.json').read_text())
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
receipt={'meshes':{},'material_build':{},'tested':False}
def save(obj):
 if not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outermost()],False):raise RuntimeError('Cannot save '+obj.get_path_name())
def record():(O/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
mesh=u.load_asset(H+'/SK_HK416_Manny');slots=list(mesh.materials)
for i,slot in enumerate(slots):
 if str(slot.material_slot_name)=='M_HK416_Stock':
  slot.material_slot_name='M_HK416_FactoryStock';slots[i]=slot
mesh.set_editor_property('materials',slots);save(mesh)
receipt['factory_stock_slot']='M_HK416_FactoryStock';record()
flag='Interchange.FeatureFlags.Import.FBX';before=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 for key,part in models['parts'].items():
  existing=u.load_asset(D+'/Meshes/'+part['name'])
  saved_bindings={re.sub(r'[._]\d{3}$','',str(s.material_slot_name)):s.material_interface for s in existing.static_materials}
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
  opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.override_full_name=True
  data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
  data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
  task=u.AssetImportTask();task.filename=part['file'];task.destination_path=D+'/Meshes';task.destination_name=part['name']
  task.automated=True;task.replace_existing=True;task.save=False;task.options=opt;A.import_asset_tasks([task])
  mesh=u.load_asset(D+'/Meshes/'+part['name']);slots=list(mesh.static_materials)
  canonical=lambda s:re.sub(r'[._]\d{3}$','',s)
  for i,slot in enumerate(slots):
   slot.material_interface=saved_bindings[canonical(str(slot.material_slot_name))];slots[i]=slot
  mesh.set_editor_property('static_materials',slots)
  editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
  if editor:
   settings=editor.get_lod_build_settings(mesh,0)
   settings.use_full_precision_u_vs=True;settings.recompute_normals=False;settings.recompute_tangents=True;editor.set_lod_build_settings(mesh,0,settings)
  E.set_metadata_tag(mesh,'HK416StockInterface','20261001 closed native receiver contour; per-part donor rim; UV0 preserved')
  save(mesh);receipt['meshes'][key]=mesh.get_path_name();record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(before))
for path in prior['materials']:
 if not path.startswith(D+'/Materials/'):continue
 m=u.load_asset(path);errors=L.recompile_material(m)
 receipt['material_build'][path]=[str(x) for x in errors];record()
 if not errors:save(m)
print('HK416_STOCK_REPAIR_SAVED',len(receipt['meshes']),'material_build_errors',sum(bool(v) for v in receipt['material_build'].values()))
