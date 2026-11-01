"""Publish the independent M24 rear receiver, pistol grips and pose profiles."""
import unreal as u,json,gzip,shutil,ast,copy,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent;D='/Game/Weapons/M24/ReceiverGripRebuild20261031'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
spec=json.loads((O/'geometry_contract.json').read_text());source=json.load(gzip.open(O/'Inputs/m24_motion.json.gz','rt'));profiles=json.load(gzip.open(O/'grip_profiles.json.gz','rt'))
inputs=json.loads((O/'Inputs/source_assets.json').read_text());host_path=inputs['M24']['path']
R={'complete':False,'saved':[],'runtime_tested':False,'host_partitioned':False}
def record():(O/'install_receipt.json').write_text(json.dumps(R,indent=2))
def load(p):
 a=u.load_asset(p)
 if not a:raise RuntimeError('Missing '+p)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
 R['saved'].append(a.get_path_name());record()
tree=ast.parse((O.parent/'M24ReloadRefine20261028/install.py').read_text())
exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='packed')),'packed','exec'))
targets=[host_path]+['/Game/Weapons/M24/MotionPolish20261027/'+n for n in ('DA_M24_SupportGrip','DA_M24_Mag10')]
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name() in targets or p.get_name().startswith(D)]
if dirty:raise RuntimeError('Unsaved work retained: '+str(dirty))
if not hasattr(u.M24ChassisAssetTools,'split_factory_rear_seat'):
 raise RuntimeError('The ordinary Editor DLL must be built before publishing the new receiver section.')
host=load(host_path);hostfile=Path(u.Paths.project_content_dir())/(host_path.removeprefix('/Game/')+'.uasset')
already=any(str(m.material_slot_name)=='M24_FactoryRearSeat' for m in host.materials)
if not already and hashlib.sha256(hostfile.read_bytes()).hexdigest()!=inputs['M24']['sha256']:
 raise RuntimeError('The live M24 mesh changed during authoring; retained it.')
# Carry independent changes to left-hand/magazine/weapon tracks into the new
# conditional profiles; concurrent edits to the owned right arm stop publication.
owned=set(json.loads((O/'grasp_authoring.json').read_text())['owned_bones'])
for family,name in {'base':'DA_M24_SupportGrip','mag10':'DA_M24_Mag10'}.items():
 live=packed(load('/Game/Weapons/M24/MotionPolish20261027/'+name),family)
 expected={c['base']:c for c in source['profiles'][family]['clips']}
 result={c['base']:c for c in profiles[family]['clips']}
 for c in live['clips']:
  if c['base'] not in result:raise RuntimeError('M24 acquired a new action during authoring: '+c['base'])
  before={t['bone']:t for t in expected[c['base']]['tracks'] if t['bone'] in owned}
  now={t['bone']:t for t in c['tracks'] if t['bone'] in owned}
  if before!=now or c['duration']!=expected[c['base']]['duration']:raise RuntimeError('Concurrent right-arm/action change retained: '+c['base'])
  result[c['base']]['tracks']=[t for t in c['tracks'] if t['bone'] not in owned]+[t for t in result[c['base']]['tracks'] if t['bone'] in owned]
path=D+'/Materials/MI_M24_ReceiverSeat'
surface=load(path) if E.does_asset_exist(path) else E.duplicate_asset('/Game/Weapons/M24/AdvancedAction20261029/Materials/MI_M24_AAS_CoatedMetal',path)
if not surface:raise RuntimeError('Material creation refused; finish PIE before importing.')
# The new seat has its own metric UVs, so it must not use the old chassis AO atlas.
L.set_material_instance_texture_parameter_value(surface,'SurfaceMask',load('/Game/Weapons/M24/RearGrip20261029/Textures/T_M24_GripSurfaceMask'))
for k,v in dict(MaskUVChannel=0,EdgeWear=0,EdgeHighlight=0,CavityDarken=0,CavityRoughness=0,AOStrength=0,HandlingPolish=0,Roughness=.395).items():
 L.set_material_instance_scalar_parameter_value(surface,k,v)
L.update_material_instance(surface);save(surface)
materials={k:load(v) for k,v in spec['materials'].items()}
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 for name,file in spec['exports'].items():
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
  imp=opt.static_mesh_import_data;imp.combine_meshes=True;imp.auto_generate_collision=False;imp.generate_lightmap_u_vs=False;imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
  task=u.AssetImportTask();task.filename=file;task.destination_path=D+'/Meshes';task.destination_name=name;task.options=opt;task.factory=u.FbxFactory();task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
  mesh=load(task.destination_path+'/'+name)
  for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,materials[str(slot.material_slot_name)])
  sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
  bs=sub.get_lod_build_settings(mesh,0);bs.recompute_normals=False;bs.recompute_tangents=False;bs.use_full_precision_u_vs=True;bs.use_high_precision_tangent_basis=True
  u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh);sub.set_lod_build_settings(mesh,0,bs)
  lod=u.StaticMeshReductionOptions();lod.auto_compute_lod_screen_size=False;lod.reduction_settings=[u.StaticMeshReductionSettings(percent_triangles=p,screen_size=s) for p,s in ((1.,1.),(.5,.18),(.2,.075))];sub.set_lods(mesh,lod)
  # Freeze the authored LODs and replace degenerate corner tangent bases left
  # by the imported donor seams and the recut mounting-neck caps.
  if not u.M24ChassisAssetTools.bake_stock_tangent_basis(mesh):raise RuntimeError('Tangent basis authoring failed '+name)
  E.set_metadata_tag(mesh,'Source',str(O/'M24_ReceiverGrip_Editable.blend'))
  E.set_metadata_tag(mesh,'M24Assembly','Measured native/advanced receiver seats; genuine independent pistol grips; no factory stock wrist reuse')
  save(mesh)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
for family,specification in profiles.items():
 name='DA_M24_skeleton_'+family;path=D+'/Profiles/'+name
 if E.does_asset_exist(path):profile=load(path)
 else:
  factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeaponGripProfile);profile=A.create_asset(name,D+'/Profiles',u.WeaponGripProfile,factory)
 if not profile or not profile.set_shared_clips_from_json(json.dumps(specification)):raise RuntimeError('Profile import failed '+name)
 E.set_metadata_tag(profile,'Source',str(O/'author_grasp.py'));save(profile)
backup=O/'Before';backup.mkdir(exist_ok=True)
if not (backup/hostfile.name).exists():shutil.copy2(hostfile,backup/hostfile.name)
centers=[u.Vector(*v) for v in json.loads((O/'Inputs/native_rear_seat_faces.json').read_text())]
if not u.M24ChassisAssetTools.split_factory_rear_seat(host,centers):raise RuntimeError('Rear receiver partition refused; host retained')
save(host);R['host_partitioned']=True;R['complete']=True;record()
print('M24_RECEIVER_GRIP_SAVED',len(R['saved']),flush=True)
