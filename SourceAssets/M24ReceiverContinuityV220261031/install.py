"""Replace two M24 advanced-stock meshes; do not modify any poses or shared parts."""
import unreal as u,json,hashlib,shutil
from pathlib import Path
O=Path(__file__).resolve().parent
E,A=u.EditorAssetLibrary,u.AssetToolsHelpers.get_asset_tools()
spec=json.loads((O/'geometry_contract.json').read_text());inputs=json.loads((O/'inputs.json').read_text())
R={'complete':False,'saved':[],'runtime_tested':False,'materials_preserved':True}
def record():(O/'install_receipt.json').write_text(json.dumps(R,indent=2))
def load(p):
 a=u.load_asset(p)
 if not a:raise RuntimeError('Missing '+p)
 return a
def disk(p):return Path(u.Paths.project_content_dir())/(p.split('.')[0].removeprefix('/Game/')+'.uasset')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for name in spec['exports']:
 row=inputs['assets'][name]
 if row['path'] in dirty:raise RuntimeError('Unsaved target retained '+row['path'])
 if hashlib.sha256(disk(row['path']).read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('Concurrent mesh edit retained '+row['path'])
 dest=O/'Before'/(row['path'].removeprefix('/Game/')+'.uasset');dest.parent.mkdir(parents=True,exist_ok=True)
 if not dest.exists():shutil.copy2(disk(row['path']),dest)
materials={}
for row in inputs['assets'].values():
 for slot in row['slots']:
  if slot.get('material'):materials[slot['slot']]=slot['material']
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 for name,file in spec['exports'].items():
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
  opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
  imp=opt.static_mesh_import_data;imp.combine_meshes=True;imp.auto_generate_collision=False;imp.generate_lightmap_u_vs=False
  imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
  task=u.AssetImportTask();task.filename=file;task.destination_path=inputs['assets'][name]['path'].rsplit('/',1)[0];task.destination_name=name
  task.options=opt;task.factory=u.FbxFactory();task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
  mesh=load(task.destination_path+'/'+name)
  for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,load(materials[str(slot.material_slot_name)]))
  sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
  bs=sub.get_lod_build_settings(mesh,0);bs.recompute_normals=False;bs.recompute_tangents=False;bs.use_full_precision_u_vs=True;bs.use_high_precision_tangent_basis=True
  u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh);sub.set_lod_build_settings(mesh,0,bs)
  lod=u.StaticMeshReductionOptions();lod.auto_compute_lod_screen_size=False
  lod.reduction_settings=[u.StaticMeshReductionSettings(percent_triangles=p,screen_size=s) for p,s in ((1.,1.),(.5,.18),(.2,.075))];sub.set_lods(mesh,lod)
  if not u.M24ChassisAssetTools.bake_stock_tangent_basis(mesh):raise RuntimeError('Tangent authoring failed '+name)
  E.set_metadata_tag(mesh,'Source',str(O/'M24_ReceiverContinuityV2_Editable.blend'))
  if not E.save_loaded_asset(mesh,False):raise RuntimeError('Save failed '+name)
  R['saved'].append({'path':mesh.get_path_name(),'sha256':hashlib.sha256(disk(mesh.get_path_name()).read_bytes()).hexdigest(),'materials':[{ 'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name()} for s in mesh.static_materials]});record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
R['complete']=True;record();print('M24_RECEIVER_V2_SAVED',len(R['saved']),flush=True)
