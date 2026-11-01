import unreal as u,json
from pathlib import Path
O=Path(__file__).resolve().parent
D='/Game/Weapons/SkeletonSniperStock20261031/M24Direct20261031'
S='/Game/Weapons/SkeletonSniperStock20261031'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
R={'complete':False,'saved':[],'animation_changed':False,'host_mesh_changed':False,'runtime_tested':False}
def load(p):
 a=u.load_asset(p)
 if not a:raise RuntimeError('Missing '+p)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
 R['saved'].append(a.get_path_name());(O/'install_receipt.json').write_text(json.dumps(R,indent=2))
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name().startswith(D)]
if dirty:raise RuntimeError('Unsaved edits retained: '+str(dirty))
path=D+'/Materials/MI_M24_IndependentGrip'
default=load(path) if E.does_asset_exist(path) else E.duplicate_asset('/Game/Weapons/M24/RearGrip20261029/Materials/MI_M24_balanced_reargrip',path)
if not default:raise RuntimeError('UE refused material creation; finish PIE before importing and saving this assembly')
L.set_material_instance_vector_parameter_value(default,'FinishColor',u.LinearColor(.017,.018,.018,1));L.set_material_instance_scalar_parameter_value(default,'Roughness',.56);L.update_material_instance(default);save(default)
materials={'SniperStock_MeshySurface':load(S+'/Materials/MI_SniperStock_MeshySurface'),'SniperStock_Interface':load(S+'/Materials/MI_SniperStock_Interface'),'M24_IndependentGrip':default}
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 spec=json.loads((O/'authoring.json').read_text())
 for key,file in spec['exports'].items():
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
  imp=opt.static_mesh_import_data;imp.combine_meshes=True;imp.auto_generate_collision=False;imp.generate_lightmap_u_vs=False;imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
  task=u.AssetImportTask();task.filename=file;task.destination_path=D+'/Meshes';task.destination_name=Path(file).stem;task.options=opt;task.factory=u.FbxFactory();task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
  mesh=load(task.destination_path+'/'+task.destination_name)
  for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,materials[str(slot.material_slot_name)])
  sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
  bs=sub.get_lod_build_settings(mesh,0);bs.recompute_normals=False;bs.recompute_tangents=False;bs.use_full_precision_u_vs=True;bs.use_high_precision_tangent_basis=True
  u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh);sub.set_lod_build_settings(mesh,0,bs)
  lod=u.StaticMeshReductionOptions();lod.auto_compute_lod_screen_size=False;lod.reduction_settings=[u.StaticMeshReductionSettings(percent_triangles=p,screen_size=s) for p,s in ((1.,1.),(.5,.18),(.2,.075))];sub.set_lods(mesh,lod)
  E.set_metadata_tag(mesh,'Source',str(O/'M24_DirectStock_Editable.blend'));E.set_metadata_tag(mesh,'M24Assembly','Direct receiver tail; separate grip; original wrist section hidden with skeleton stock')
  save(mesh)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
R['complete']=True;(O/'install_receipt.json').write_text(json.dumps(R,indent=2));print('M24_DIRECT_STOCK_SAVED',len(R['saved']),flush=True)
