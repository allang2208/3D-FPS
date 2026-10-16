"""Import two ASH-only fits with full RHI build data, leaving donors untouched."""
import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];C=json.loads((O/'capture.json').read_text());R=json.loads((O/'production.json').read_text())
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
command=u.SystemLibrary.get_command_line().lower()
if '-nullrhi' in command:raise RuntimeError('ASH final asset build requires RHI')
if '-run=pythonscript' not in command and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE active; do not overwrite loaded assets')
sms=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
receipt=json.loads((O/'install_receipt.json').read_text()) if (O/'install_receipt.json').exists() else {'saved':{},'complete':False,'gameplay_tested':False,'donors_modified':False}
def disk(path):return P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(path):return hashlib.sha256(disk(path).read_bytes()).hexdigest()
def record():(O/'install_receipt.json').write_text(json.dumps(receipt,indent=2))
def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing '+path)
 return a
if not R['complete']:raise RuntimeError('Authoring incomplete')
for key,row in R['assets'].items():
 if key in receipt['saved']:continue
 if E.does_asset_exist(row['target']):
  pending=load(row['target'])
  # A normal editor exit can save this run's pending import before socket
  # finalization. Resume only our exact authored FBX and slot bindings.
  expected={s['name']:s['material'] for s in row['slots']}
  bound={str(s.material_slot_name):s.material_interface.get_path_name() if s.material_interface else None for s in pending.static_materials}
  if Path(pending.get_editor_property('asset_import_data').get_first_filename()).resolve()!=Path(row['fbx']).resolve() or bound!=expected:raise RuntimeError('New destination occupied '+row['target'])
 if sha(row['source'])!=C['assets'][key]['sha256']:raise RuntimeError('Source changed '+key)
if sha(C['host']['path'])!=C['host']['sha256']:raise RuntimeError('Host changed')
for key,row in R['assets'].items():
 if key in receipt['saved']:continue
 original=load(row['source'])
 previous=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX');u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
 try:
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
  imp=opt.static_mesh_import_data;imp.combine_meshes=True;imp.auto_generate_collision=False;imp.generate_lightmap_u_vs=False;imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
  task=u.AssetImportTask();task.filename=row['fbx'];task.destination_path,task.destination_name=row['target'].rsplit('/',1);task.automated=True;task.replace_existing=True;task.save=False;task.options=opt;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=load(row['target'])
 finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(previous))
 expected={s['name']:s['material'] for s in row['slots']};slots=list(mesh.static_materials)
 for i,s in enumerate(slots):
  name=str(s.material_slot_name)
  if name not in expected:raise RuntimeError('Unexpected slot '+key+' '+name)
  s.material_interface=load(expected[name]);slots[i]=s
 mesh.set_editor_property('static_materials',slots);mesh.set_editor_property('nanite_settings',original.get_editor_property('nanite_settings'))
 u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh)
 settings=sms.get_lod_build_settings(mesh,0);settings.recompute_normals=False;settings.recompute_tangents=True;settings.use_mikk_t_space=True;settings.use_full_precision_u_vs=True;settings.use_high_precision_tangent_basis=True;settings.remove_degenerates=True;settings.generate_lightmap_u_vs=False;sms.set_lod_build_settings(mesh,0,settings)
 for name,spec in row['sockets'].items():
  socket=mesh.find_socket(name)
  if not socket:socket=u.new_object(u.StaticMeshSocket,outer=mesh);socket.set_editor_property('socket_name',name);mesh.add_socket(socket)
  socket.set_editor_property('relative_location',u.Vector(*spec['location']));socket.set_editor_property('relative_rotation',u.Rotator(*spec['rotation']));socket.set_editor_property('relative_scale',u.Vector(*spec['scale']))
 # Finish actual mesh/DF compilation and prevent the known ASH invalid-bounds
 # import failure before saving a newly generated asset.
 if not u.ASH12AttachmentAssetTools.finish_and_validate_build(mesh):raise RuntimeError('Mesh build data incomplete '+key)
 bounds=mesh.get_bounding_box();actual=[[bounds.min.x,bounds.min.y,bounds.min.z],[bounds.max.x,bounds.max.y,bounds.max.z]]
 if any(abs(actual[e][i]-row['bounds_cm'][e][i])>.02 for e in range(2) for i in range(3)):raise RuntimeError('FBX/render bounds disagree '+key+' actual='+str(actual)+' expected='+str(row['bounds_cm']))
 E.set_metadata_tag(mesh,'ASH12OpticSeat20261015','ASH rail contact shoe; EOTH rearward seat clears fixed front sight; optical sockets follow body')
 if not E.save_loaded_asset(mesh,False):raise RuntimeError('Save failed '+key)
 receipt['saved'][key]={'path':mesh.get_path_name(),'sha256':sha(row['target']),'source':row['source'],'sockets':row['sockets'],'render_bounds_cm':actual,'full_build_complete':True,'material_slots':expected};record();print('ASH_OPTIC_SAVED',key,flush=True)
receipt['complete']=True;record();print('ASH_TWO_OPTICS_INSTALLED',flush=True)
