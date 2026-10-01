"""Save EOTH optical geometry/materials without changing mounts or gameplay."""
import unreal as u,json,re,importlib.util
from pathlib import Path
O=Path(__file__).parent;S=O.parent/'HK416UniversalParts20260930';ROOT='/Game/Weapons/CommonHK41620260930/Meshes'
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir())).resolve()!=(O.parents[1]/'Content').resolve():raise RuntimeError('Wrong EOTH content mount')
entries=json.loads((O/'authoring.json').read_text());spec=importlib.util.spec_from_file_location('eoth_materials',S/'reticle_materials.py');materials=importlib.util.module_from_spec(spec);spec.loader.exec_module(materials)
paths={ROOT+'/'+e['name'] for e in entries.values()}|{materials.RETICLE,materials.GLASS}
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name() in paths]
if dirty:raise RuntimeError('Preserve unsaved EOTH target assets: '+str(dirty))
reticle,glass=materials.build();receipt={'materials':[reticle.get_path_name(),glass.get_path_name()],'meshes':{},'runtime_tested':False,'aim_sockets_unchanged':True}
canonical=lambda s:re.sub(r'[._]\d{3}$','',s)
flag='Interchange.FeatureFlags.Import.FBX';before=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 for key,entry in entries.items():
  path=ROOT+'/'+entry['name'];mesh=u.load_asset(path)
  bindings={canonical(str(s.material_slot_name)):s.material_interface for s in mesh.static_materials}
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
  opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.override_full_name=True
  settings=opt.static_mesh_import_data;settings.combine_meshes=True;settings.auto_generate_collision=False;settings.generate_lightmap_u_vs=False
  settings.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;settings.vertex_color_import_option=u.VertexColorImportOption.REPLACE
  task=u.AssetImportTask();task.filename=entry['fbx'];task.destination_path=ROOT;task.destination_name=entry['name'];task.automated=True;task.replace_existing=True;task.save=False;task.options=opt
  u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=u.load_asset(path);slots=list(mesh.static_materials)
  for i,slot in enumerate(slots):
   name=canonical(str(slot.material_slot_name))
   slot.material_interface=reticle if name=='M_HK416_Eo_tech_Reticle' else glass if name=='M_HK416_Glass' else bindings[name];slots[i]=slot
  mesh.set_editor_property('static_materials',slots)
  for name,p in entry['sockets_blender_m'].items():
   socket=mesh.find_socket(name)
   if not socket:socket=u.new_object(u.StaticMeshSocket,outer=mesh);socket.set_editor_property('socket_name',name);mesh.add_socket(socket)
   socket.set_editor_property('relative_location',u.Vector(p[0]*100,-p[1]*100,p[2]*100))
  editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
  if editor:
   build=editor.get_lod_build_settings(mesh,0);build.use_full_precision_u_vs=True;editor.set_lod_build_settings(mesh,0,build)
  u.EditorAssetLibrary.set_metadata_tag(mesh,'EOTHReticle','20261001 analytic AA circle-dot, exposure compensated, local temporal response, unchanged sight sockets')
  if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()],False):raise RuntimeError('EOTH mesh save '+path)
  receipt['meshes'][key]=mesh.get_path_name();(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2));print('EOTH_OPTICAL_ASSET_SAVED',key,flush=True)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(before))
print('EOTH_READABLE_RETICLE_SAVED',len(receipt['meshes']),flush=True)
