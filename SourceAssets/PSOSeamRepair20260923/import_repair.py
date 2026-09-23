"""Install opaque PSO collar partitions and their completed texture regions."""
import unreal as u,json,shutil
from pathlib import Path
O=Path(__file__).parent;P=Path(u.Paths.project_dir()).resolve()
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
data=json.loads((O/'authoring.json').read_text());report={'meshes':[],'textures':[],'game_tested':False}
if (O/'import_receipt.json').exists():report=json.loads((O/'import_receipt.json').read_text())
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; preserve current state')
targets={m['asset'] for m in data['meshes']}
for t in data['textures']:
 folder='/Game/Weapons/SVDDragunov20260922/Surface20260923/Textures' if t['host']=='SVD' else '/Game/Weapons/PSO1Russian20260923/Textures'
 t['asset']=folder+'/'+Path(t['result']).stem;targets.add(t['asset'])
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if targets & dirty:raise RuntimeError('Unsaved repair targets '+str(targets & dirty))

def backup(path):
 f=P/'Content'/(path.removeprefix('/Game/')+'.uasset');dst=O/'Before/Content'/f.relative_to(P/'Content')
 if not dst.exists():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dst)
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Asset save failed '+a.get_path_name())
def record():(O/'import_receipt.json').write_text(json.dumps(report,indent=2))

for t in data['textures']:
 if any(r['asset']==t['asset'] and r['saved'] for r in report['textures']):continue
 path=t['asset'];tex=u.load_asset(path)
 if not tex:raise RuntimeError('Missing original texture '+path)
 backup(path)
 props={key:tex.get_editor_property(key) for key in ['srgb','compression_settings','lod_group','lod_bias','max_texture_size','mip_gen_settings','flip_green_channel']}
 task=u.AssetImportTask();task.filename=t['result'];task.destination_path=path.rsplit('/',1)[0];task.destination_name=path.rsplit('/',1)[1]
 task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
 if not task.imported_object_paths:raise RuntimeError('Texture import failed '+path)
 tex=u.load_asset(path)
 for key,value in props.items():tex.set_editor_property(key,value)
 save(tex);report['textures'].append({'asset':path,'source':t['result'],'saved':True});record()

flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
try:
 u.SystemLibrary.execute_console_command(None,flag+' 0')
 for row in data['meshes']:
  if any(r['asset']==row['asset'] and r['saved'] for r in report['meshes']):continue
  path=row['asset'];mesh=u.load_asset(path);backup(path);skeletal=row['host']=='SVD'
  slotprop='materials' if skeletal else 'static_materials'
  bindings={str(s.material_slot_name):s.material_interface for s in mesh.get_editor_property(slotprop)}
  sockets={}
  if skeletal:
   sk=mesh.skeleton;physics=mesh.physics_asset;post=mesh.get_editor_property('post_process_anim_blueprint')
  else:
   for name in ['AimCenter','AimFront']:
    s=mesh.find_socket(name)
    if not s:raise RuntimeError('Missing existing optical socket '+name)
    sockets[name]={key:s.get_editor_property(key) for key in ['relative_location','relative_rotation','relative_scale','tag']}
   nanite=mesh.get_editor_property('nanite_settings')
  opts=u.FbxImportUI();opts.automated_import_should_detect_type=False
  opts.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH if skeletal else u.FBXImportType.FBXIT_STATIC_MESH
  opts.import_as_skeletal=skeletal;opts.import_mesh=True;opts.import_animations=False;opts.import_materials=False;opts.import_textures=False
  opts.set_editor_property('reset_to_fbx_on_material_conflict',True)
  if skeletal:
   opts.create_physics_asset=False;opts.skeleton=sk
   d=opts.skeletal_mesh_import_data;d.set_editor_property('update_skeleton_reference_pose',False);d.set_editor_property('use_t0_as_ref_pose',False);d.set_editor_property('preserve_smoothing_groups',True)
   d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
  else:
   d=opts.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False
   d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;d.vertex_color_import_option=u.VertexColorImportOption.REPLACE
  task=u.AssetImportTask();task.filename=row['fbx'];task.destination_path=path.rsplit('/',1)[0];task.destination_name=path.rsplit('/',1)[1]
  task.options=opts;task.factory=u.FbxFactory();task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
  A.import_asset_tasks([task])
  if not task.imported_object_paths:raise RuntimeError('Mesh import failed '+path)
  mesh=u.load_asset(path);slots=mesh.get_editor_property(slotprop)
  if {str(s.material_slot_name) for s in slots}!=set(bindings):raise RuntimeError('Unexpected material slot change '+path)
  for i,s in enumerate(slots):s.material_interface=bindings[str(s.material_slot_name)];slots[i]=s
  mesh.set_editor_property(slotprop,slots)
  if skeletal:
   mesh.set_editor_property('physics_asset',physics);mesh.set_editor_property('post_process_anim_blueprint',post)
   if mesh.skeleton!=sk:raise RuntimeError('Skeleton changed')
  else:
   mesh.set_editor_property('nanite_settings',nanite)
   for name,props in sockets.items():
    s=mesh.find_socket(name)
    if not s:s=u.new_object(u.StaticMeshSocket,outer=mesh);s.socket_name=name;mesh.add_socket(s)
    for key,value in props.items():s.set_editor_property(key,value)
  save(mesh)
  partitions={str(s.material_slot_name):{'material':s.material_interface.get_path_name(),'blend':str(s.material_interface.get_base_material().blend_mode)} for s in mesh.get_editor_property(slotprop)}
  shell=next(v for k,v in partitions.items() if 'ScopeBody' in k or 'Shell' in k)
  if shell['blend']!=str(u.BlendMode.BLEND_OPAQUE):raise RuntimeError('Collars must bind opaque shell')
  report['meshes'].append({'asset':path,'saved':True,'slots':partitions,'sockets_preserved':list(sockets),'source':row['fbx']});record()
  print('PSO_SEAM_MESH_SAVED',row['host'],flush=True)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
report['completed']=True;record();print('PSO_SEAM_REPAIR_SAVED',len(report['meshes']),len(report['textures']),flush=True)
