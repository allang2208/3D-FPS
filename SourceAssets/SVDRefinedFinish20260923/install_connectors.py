"""Replace existing SVD adapters in place; preserve current finish, skeleton and animation assets."""
import unreal as u,json,shutil
from pathlib import Path
O=Path(__file__).parent;PROJECT=Path(u.Paths.project_dir()).resolve()
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
geo=json.loads((O/'connectors.json').read_text());finish=json.loads((O/'finish_receipt.json').read_text())
inputs=json.loads((O/'inputs.json').read_text());rp=O/'connectors_receipt.json'
receipt=json.loads(rp.read_text()) if rp.exists() else {'meshes':{},'animations_changed':False,'game_tested':False}
if not finish.get('complete'):raise RuntimeError('Finish installation must complete first')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Active play session; preserve state')
targets={inputs['meshes'][key]['asset'] for key in geo['meshes']}
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty & targets:raise RuntimeError('Unsaved target assets '+str(dirty & targets))

def record():rp.write_text(json.dumps(receipt,indent=2))
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def backup(path):
 f=PROJECT/'Content'/(path.removeprefix('/Game/')+'.uasset');dst=O/'BeforeGeometry'/f.relative_to(PROJECT/'Content')
 if not dst.exists():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dst)

# These private adapter finish bases also serve the four new rigid PSO screw heads.
for key in ['Fastener','Fastener_Wet']:
 base=u.load_asset(finish['hardware'][key]).get_base_material()
 if not base.get_editor_property('used_with_skeletal_mesh'):
  base.set_editor_property('used_with_skeletal_mesh',True)
  errors=L.recompile_material(base)
  if errors:raise RuntimeError('Hardware material compile failed '+str(errors))
  save(base)

flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 for key,row in geo['meshes'].items():
  if key in receipt['meshes']:continue
  path=inputs['meshes'][key]['asset'];old=u.load_asset(path);skeletal=row['skeletal'];backup(path)
  prop='materials' if skeletal else 'static_materials'
  bindings={str(s.material_slot_name):s.material_interface for s in old.get_editor_property(prop)}
  for label in ['SVD_AdapterFastener','SVD_ScopeMountFastener']:bindings[label]=u.load_asset(finish['hardware']['Fastener'])
  for label in ['SVD_AdapterRecess','SVD_ScopeMountRecess']:bindings[label]=u.load_asset(finish['hardware']['Recess'])
  properties={k:old.get_editor_property(k) for k in ['positive_bounds_extension','negative_bounds_extension']}
  sockets={}
  if skeletal:
   skeleton=old.skeleton
   properties.update({k:old.get_editor_property(k) for k in ['physics_asset','post_process_anim_blueprint']})
  else:
   properties['nanite_settings']=old.get_editor_property('nanite_settings')
   socket_source=u.new_object(u.StaticMeshComponent);socket_source.set_static_mesh(old)
   for socket_name in socket_source.get_all_socket_names():
    socket=old.find_socket(socket_name)
    sockets[str(socket.socket_name)]={k:socket.get_editor_property(k) for k in ['relative_location','relative_rotation','relative_scale','tag']}
  opts=u.FbxImportUI();opts.automated_import_should_detect_type=False
  opts.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH if skeletal else u.FBXImportType.FBXIT_STATIC_MESH
  opts.import_as_skeletal=skeletal;opts.import_mesh=True;opts.import_animations=False;opts.import_materials=False;opts.import_textures=False
  opts.set_editor_property('reset_to_fbx_on_material_conflict',True)
  if skeletal:
   opts.create_physics_asset=False;opts.skeleton=skeleton;d=opts.skeletal_mesh_import_data
   d.set_editor_property('update_skeleton_reference_pose',False);d.set_editor_property('use_t0_as_ref_pose',False);d.set_editor_property('preserve_smoothing_groups',True)
  else:
   d=opts.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False
   d.vertex_color_import_option=u.VertexColorImportOption.REPLACE
  d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
  task=u.AssetImportTask();task.filename=row['source'];task.destination_path=path.rsplit('/',1)[0];task.destination_name=path.rsplit('/',1)[1]
  task.options=opts;task.factory=u.FbxFactory();task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
  A.import_asset_tasks([task])
  if not task.imported_object_paths:raise RuntimeError('Import failed '+key)
  mesh=u.load_asset(path);slots=mesh.get_editor_property(prop)
  for i,s in enumerate(slots):
   s.material_interface=bindings[str(s.material_slot_name)];slots[i]=s
  mesh.set_editor_property(prop,slots)
  for k,v in properties.items():mesh.set_editor_property(k,v)
  if not skeletal:
   for name,values in sockets.items():
    sock=mesh.find_socket(name)
    if not sock:sock=u.new_object(u.StaticMeshSocket,outer=mesh);sock.socket_name=name;mesh.add_socket(sock)
    for k,v in values.items():sock.set_editor_property(k,v)
  save(mesh)
  receipt['meshes'][key]={'asset':mesh.get_path_name(),'source':row['source'],'saved':True,
   'slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in slots},
   'preserved_sockets':list(sockets),'preserved':row.get('preserved','')}
  record();print('SVD_HAND_CONNECTOR_SAVED',key,flush=True)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
receipt['complete']=True;record();print('SVD_HAND_CONNECTORS_COMPLETE',len(receipt['meshes']),flush=True)
