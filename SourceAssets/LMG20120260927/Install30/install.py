"""Keep independent old UE assets; replace current 201 through its existing path."""
import unreal as u,json,hashlib,shutil
from pathlib import Path
O=Path(__file__).parent;PROJECT=O.parents[2];P='/Game/Weapons/LMG201/Install30'
BODY='/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10'
PROD='/Game/Weapons/LMG201/Production20260927'
WET='/Game/Weapons/LMG201/Accessories22/DA_LMG201_AttachmentWetMaterials'
ARCHIVE=P+'/Previous'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils
M=u.GeometryScript_Materials;B=u.GeometryScript_BoneWeights;Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List;Ed=u.GeometryScript_MeshEdits
source=json.loads((O/'current.json').read_text());fit=json.loads((O/'fit.json').read_text());materials=json.loads((O/'materials.json').read_text())
if materials['status']!='compiled_and_saved':raise RuntimeError('PBR preparation incomplete')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; current 201 not changed')
targets=[BODY,PROD+'/SM_LMG201_FrontSight',PROD+'/SM_LMG201_RearSight',WET]
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p in dirty for p in targets):raise RuntimeError('A target 201 asset has unsaved work; preserve it')
def package(path):return PROJECT/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def digest(path):return hashlib.sha256(package(path).read_bytes()).hexdigest()
receipt=json.loads((O/'delivery.json').read_text()) if (O/'delivery.json').exists() else {'revision':'Install30','status':'installing','backups':{},'saved':{},'tested':False,'rendered':False,'game_started':False}
expected=receipt.get('saved',{}).get(BODY,{}).get('sha256',source['sha256'])
if digest(BODY)!=expected:raise RuntimeError('Current 201 changed since native preparation; preserve that version')
def record():(O/'delivery.json').write_text(json.dumps(receipt,indent=2))
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def dynamic(mesh):
 fn=G.copy_mesh_from_skeletal_mesh if isinstance(mesh,u.SkeletalMesh) else G.copy_mesh_from_static_mesh
 dm,result=fn(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read asset geometry '+mesh.get_path_name())
 return dm
for path in targets:
 if path in receipt['backups']:continue
 name=path.rsplit('/',1)[1];dest=ARCHIVE+'/'+name+'_PreR30'
 if E.does_asset_exist(dest):raise RuntimeError('Unowned backup path already exists '+dest)
 asset=E.duplicate_asset(path,dest)
 if not asset:raise RuntimeError('Old-asset duplicate failed '+path)
 save(asset)
 file=package(path);backup=O/'Before'/file.relative_to(PROJECT/'Content');backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,backup)
 receipt['backups'][path]={'asset':asset.get_path_name(),'original_bytes':str(backup),'sha256':digest(path)};record()
manifest=O.parent/'Material21/bindings.json';manifest_backup=O/'Before/Material21_bindings.json'
if not manifest_backup.exists():shutil.copy2(manifest,manifest_backup)
current=u.load_asset(BODY);original_slots=[s.copy() for s in current.materials]

def import_part(name,file,skeletal=False):
 opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
 opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH if skeletal else u.FBXImportType.FBXIT_STATIC_MESH
 opt.import_as_skeletal=skeletal;opt.import_mesh=True;opt.import_animations=False
 opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
 opt.set_editor_property('reset_to_fbx_on_material_conflict',True)
 if skeletal:
  opt.skeleton=current.skeleton;data=opt.skeletal_mesh_import_data
  data.set_editor_property('update_skeleton_reference_pose',False)
  data.set_editor_property('use_t0_as_ref_pose',False)
  data.set_editor_property('preserve_smoothing_groups',True)
 else:
  data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
 data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
 data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
 task=u.AssetImportTask();task.filename=file;task.destination_path=P+'/Parts';task.destination_name=name
 task.factory=u.FbxFactory();task.options=opt;task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
 A.import_asset_tasks([task]);asset=u.load_asset(task.destination_path+'/'+name)
 if not asset or not task.imported_object_paths:raise RuntimeError('FBX import failed '+name)
 prop='materials' if skeletal else 'static_materials';slots=[s.copy() for s in asset.get_editor_property(prop)]
 for s in slots:
  key=str(s.material_slot_name);kind=fit['material_roles'].get(key)
  if not kind:raise RuntimeError('Unmapped R30 slot '+key)
  s.material_interface=u.load_asset(materials['materials'][kind])
 asset.set_editor_property(prop,slots);save(asset);return asset

def copy_to(dm,asset,slots):
 opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,
  new_materials=[s.material_interface for s in slots],new_material_slot_names=[s.material_slot_name for s in slots],
  enable_recompute_normals=False,enable_recompute_tangents=True,
  bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
 fn=G.copy_mesh_to_skeletal_mesh if isinstance(asset,u.SkeletalMesh) else G.copy_mesh_to_static_mesh
 _,result=fn(dm,asset,opts,u.GeometryScriptMeshWriteLOD())
 if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Mesh assembly failed '+asset.get_path_name())
 asset.set_editor_property('materials' if isinstance(asset,u.SkeletalMesh) else 'static_materials',slots)

bindings={};flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 if BODY not in receipt['saved']:
  new=import_part('SK_LMG201_R30_Weapon',fit['exports']['Weapon'],True)
  part=dynamic(new);native=dynamic(current)
  # Keep current V7 arms and accepted magazine directly from the loaded UE mesh.
  # Small animated controls may share a steel/interior slot with the old body;
  # their original bone ownership selects them without retaining old hull faces.
  _,bones=B.get_all_bones_info(native)
  keep_bones={b.index for b in bones if str(b.name) in ['WPN_Trigger','WPN_ChargingHandle','WPN_BoltCatch','WPN_Bolt']}
  keep_slots={i for i,s in enumerate(original_slots) if str(s.material_slot_name).startswith(('M_LMG201_MannySkin_','M_LMG201_Magazine'))}
  _,tl,_=Q.get_all_triangle_indices(native,False);triangles=L.convert_triangle_list_to_array(tl)
  cache={};delete=[];retained={}
  def control(vi):
   if vi not in cache:
    _,weights,valid=B.get_vertex_bone_weights(native,vi)
    cache[vi]=valid and sum(w.weight for w in weights if w.bone_index in keep_bones)>.99
   return cache[vi]
  for ti,t in enumerate(triangles):
   mid,valid=M.get_triangle_material_id(native,ti)
   if not valid:continue
   if mid in keep_slots or all(control(vi) for vi in (t.x,t.y,t.z)):
    key=str(original_slots[mid].material_slot_name);retained[key]=retained.get(key,0)+1
   else:delete.append(ti)
  ids=L.convert_array_to_index_list(delete,u.GeometryScriptIndexType.TRIANGLE);Ed.delete_triangles_from_mesh(native,ids,True)
  B.copy_bones_from_mesh(part,native,u.GeometryScriptCopyBonesFromMeshOptions(reindex_weights=True))
  slots=original_slots[:];mapping={}
  for i,s in enumerate(new.materials):mapping[i]=len(slots);slots.append(s.copy())
  for i in mapping:M.remap_material_i_ds(part,i,1000+i)
  for i,dst in mapping.items():M.remap_material_i_ds(part,1000+i,dst)
  Ed.append_mesh(native,part,u.Transform(),True)
  candidate_path=P+'/SK_LMG201_R30_Installed'
  candidate=u.load_asset(candidate_path) or E.duplicate_asset(BODY,candidate_path)
  if not candidate:raise RuntimeError('Cannot create independent installed candidate')
  copy_to(native,candidate,slots);E.set_metadata_tag(candidate,'201Revision','Install30 R29 surface, native arms/magazine/controls retained');save(candidate)
  # A full assembled FBX backs the current asset's normal reimport source.
  fbx=O/'Exports/SK_LMG201_R30_Installed.fbx'
  ex=u.AssetExportTask();ex.object=candidate;ex.filename=str(fbx);ex.automated=True;ex.prompt=False;ex.replace_identical=True
  ex.options=u.FbxExportOption();ex.options.level_of_detail=False;ex.options.export_morph_targets=False
  # Textures are already baked. UseMeshData would create a render-only skinned
  # component for material baking and assert under NullRHI in a commandlet.
  ex.options.bake_material_inputs=u.FbxMaterialBakeMode.DISABLED
  if not u.Exporter.run_asset_export_task(ex):raise RuntimeError('Cannot save assembled FBX source')
  copy_to(native,current,slots)
  current.get_editor_property('asset_import_data').scripted_add_filename(str(fbx),0,'Install30 full assembly')
  E.set_metadata_tag(current,'201Revision','Install30: fitted R29 Meshy refinement; factory-magazine reload remains active')
  E.set_metadata_tag(current,'201PreviousAsset',receipt['backups'][BODY]['asset'])
  E.set_metadata_tag(current,'201BodySurfaceRevision','Refine29 surface fairing and PBR; full assembled source under Install30')
  save(current)
  receipt['saved'][BODY]={'sha256':digest(BODY),'candidate':candidate.get_path_name(),'kept_native_triangles':retained,'replaced_triangles':len(delete),'full_fbx':str(fbx)};record()
  print('R30_CURRENT_201_SAVED',flush=True)
 for name in ['FrontSight','RearSight','AmmoBag','AmmoBelt']:
  target=PROD+'/SM_LMG201_'+name if name in ['FrontSight','RearSight'] else P+'/Parts/SM_LMG201_R30_'+name
  if target in receipt['saved']:continue
  asset=import_part('SM_LMG201_R30_'+name,fit['exports'][name])
  if name in ['FrontSight','RearSight']:
   dest=u.load_asset(target);slots=[s.copy() for s in asset.static_materials]
   copy_to(dynamic(asset),dest,slots)
   dest.get_editor_property('asset_import_data').scripted_add_filename(fit['exports'][name],0,'Install30')
   E.set_metadata_tag(dest,'201PreviousAsset',receipt['backups'][target]['asset']);save(dest)
   bindings[dest.get_path_name()]={str(s.material_slot_name):s.material_interface.get_path_name() for s in slots}
  receipt['saved'][target]={'sha256':digest(target),'storage_only':name in ['AmmoBag','AmmoBelt']};record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))

table=u.load_asset(WET);wet=dict(table.get_editor_property('wet_materials'))
for path in materials['materials'].values():wet[path]=u.load_asset(path)
table.set_editor_property('wet_materials',wet);save(table)
bindings[current.get_path_name()]={str(s.material_slot_name):s.material_interface.get_path_name() for s in current.materials}
for name in ['FrontSight','RearSight']:
 asset=u.load_asset(PROD+'/SM_LMG201_'+name);bindings[asset.get_path_name()]={str(s.material_slot_name):s.material_interface.get_path_name() for s in asset.static_materials}
data=json.loads(manifest.read_text());data['meshes'].update(bindings);manifest.write_text(json.dumps(data,indent=2),encoding='utf8')
(O/'bindings.json').write_text(json.dumps({'meshes':bindings},indent=2))
receipt.update(status='current_201_replaced_and_saved',materials=materials['materials'],wet_catalog=WET,
 animations_changed=False,gameplay_changed=False,old_assets_deleted=False,
 factory_magazine_preserved=True,bag_and_belt='standalone storage only; no retired box reload enabled')
record();print('R30_INSTALL_COMPLETE',json.dumps(receipt['saved']),flush=True)
