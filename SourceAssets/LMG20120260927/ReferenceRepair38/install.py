"""Replace only rejected receiver/cover sections; keep all unrelated native data."""
import unreal as u,json,hashlib,shutil
from pathlib import Path
O=Path(__file__).parent;S=O.parent;PROJECT=O.parents[2];P='/Game/Weapons/LMG201/ReferenceRepair38'
BODY='/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10';WET='/Game/Weapons/LMG201/Accessories22/DA_LMG201_AttachmentWetMaterials'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
M=u.GeometryScript_Materials;Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List;Ed=u.GeometryScript_MeshEdits
model=json.loads((O/'model.json').read_text());materials=json.loads((O/'materials.json').read_text())
if materials['status']!='compiled_and_saved':raise RuntimeError('Materials incomplete')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; current asset retained')
receipt={'status':'installing','backups':{},'saved':{},'animations_changed':False,'skeleton_replaced':False,'game_tested':False,'reference_match_accepted':False}
if (O/'delivery.json').exists():receipt=json.loads((O/'delivery.json').read_text())
def record():(O/'delivery.json').write_text(json.dumps(receipt,indent=2))
def load(p):
 a=u.load_asset(p)
 if not a:raise RuntimeError('Missing '+p)
 return a
def file(p):return PROJECT/'Content'/(p.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(p):return hashlib.sha256(file(p).read_bytes()).hexdigest()
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
def dynamic(a):
 dm,res=G.copy_mesh_from_skeletal_mesh(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if res!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+a.get_path_name())
 return dm
def copy_to(dm,a,slots):
 opt=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[s.material_interface for s in slots],new_material_slot_names=[s.material_slot_name for s in slots],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
 _,res=G.copy_mesh_to_skeletal_mesh(dm,a,opt,u.GeometryScriptMeshWriteLOD())
 if res!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write '+a.get_path_name())
 a.set_editor_property('materials',slots)

dirty={x.get_path_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty&{BODY,WET}:raise RuntimeError('Unsaved target retained '+str(dirty))
baseline=json.loads((O/'capture.json').read_text())
expected=receipt['saved'].get(BODY,{}).get('sha256',baseline['sha256'])
if sha(BODY)!=expected:raise RuntimeError('Current body changed since source capture; retained')
for path in [BODY,WET]:
 if path in receipt['backups']:continue
 dest=P+'/Previous/'+path.rsplit('/',1)[1]+'_PreR38'
 if E.does_asset_exist(dest):raise RuntimeError('Backup already exists without receipt '+dest)
 duplicate=E.duplicate_asset(path,dest)
 if not duplicate:raise RuntimeError('Backup failed '+path)
 save(duplicate);dst=O/'Before'/file(path).relative_to(PROJECT/'Content');dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file(path),dst)
 receipt['backups'][path]={'asset':duplicate.get_path_name(),'bytes':str(dst),'sha256':sha(path)};record()

current=load(BODY)
if BODY not in receipt['saved']:
 path=P+'/Parts/SK_LMG201_R38_ReceiverCover';part_asset=u.load_asset(path)
 if not part_asset:
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=current.skeleton
  d=opt.skeletal_mesh_import_data;d.set_editor_property('update_skeleton_reference_pose',False);d.set_editor_property('use_t0_as_ref_pose',False);d.set_editor_property('preserve_smoothing_groups',True);d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;d.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
  task=u.AssetImportTask();task.filename=model['fbx'];task.destination_path=P+'/Parts';task.destination_name='SK_LMG201_R38_ReceiverCover';task.factory=u.FbxFactory();task.options=opt;task.automated=True;task.save=False
  flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
  try:A.import_asset_tasks([task])
  finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
  part_asset=load(path)
 slots=[s.copy() for s in current.materials];lookup={str(s.material_slot_name):s.material_interface for s in slots}
 part_slots=[s.copy() for s in part_asset.materials]
 for i,s in enumerate(part_slots):
  name=str(s.material_slot_name)
  if name in materials['materials']:s.material_interface=load(materials['materials'][name])
  elif name in lookup:s.material_interface=lookup[name]
  else:raise RuntimeError('Unbound part slot '+name)
  part_slots[i]=s
 part_asset.set_editor_property('materials',part_slots);save(part_asset)
 native=dynamic(current);part=dynamic(part_asset)
 _,bones=B.get_all_bones_info(native);root=next(b for b in bones if str(b.name)=='WPN_root').world_transform
 # Shared F37 Interior also belongs to the front sight base. Use the root-local
 # longitudinal span of this imported replacement, ignoring lateral spike extent.
 def root_point(p):return u.MathLibrary.inverse_transform_location(root,p)
 def positions(dm,ti):
  valid,a,b,c=Q.get_triangle_positions(dm,ti)
  if not valid:raise RuntimeError('Invalid triangle '+str(ti))
  return [a,b,c]
 _,tl,_=Q.get_all_triangle_indices(part,False);part_tris=L.convert_triangle_list_to_array(tl)
 span=[]
 for ti in range(len(part_tris)):
  mid,valid=M.get_triangle_material_id(part,ti)
  if valid and str(part_slots[mid].material_slot_name)=='M_LMG201_F37_Receiver':span.extend(root_point(p).y for p in positions(part,ti))
 if not span:raise RuntimeError('Missing imported receiver extent')
 low,high=min(span),max(span);margin=(high-low)*.02
 replaced={'M_LMG201_F37_Receiver','M_LMG201_F37_Cover','M_LMG201_F37_CoverInterior','M_LMG201_F37_CoverSatin'}
 _,tl,_=Q.get_all_triangle_indices(native,False);triangles=L.convert_triangle_list_to_array(tl);delete=[];kept_shared=0;counts={}
 for ti in range(len(triangles)):
  mid,valid=M.get_triangle_material_id(native,ti)
  if not valid:continue
  name=str(slots[mid].material_slot_name);remove=name in replaced
  if name=='M_LMG201_F37_Interior':
   yy=sum(root_point(p).y for p in positions(native,ti))/3;remove=low-margin<=yy<=high+margin
   if not remove:kept_shared+=1
  if remove:delete.append(ti);counts[name]=counts.get(name,0)+1
 if not counts.get('M_LMG201_F37_Receiver') or not counts.get('M_LMG201_F37_Cover') or not kept_shared:raise RuntimeError('Replacement ownership unresolved '+str(counts))
 Ed.delete_triangles_from_mesh(native,L.convert_array_to_index_list(delete,u.GeometryScriptIndexType.TRIANGLE),True)
 B.copy_bones_from_mesh(native,part,u.GeometryScriptCopyBonesFromMeshOptions(reindex_weights=True))
 names={str(s.material_slot_name):i for i,s in enumerate(slots)}
 for s in part_slots:
  key=str(s.material_slot_name)
  if key not in names:names[key]=len(slots);slots.append(s.copy())
 for i,s in enumerate(part_slots):M.remap_material_i_ds(part,i,1000+i)
 for i,s in enumerate(part_slots):M.remap_material_i_ds(part,1000+i,names[str(s.material_slot_name)])
 Ed.append_mesh(native,part,u.Transform(),True)
 candidate=u.load_asset(P+'/SK_LMG201_R38_Installed') or E.duplicate_asset(BODY,P+'/SK_LMG201_R38_Installed')
 copy_to(native,candidate,slots);save(candidate);copy_to(native,current,slots)
 full=O/'Exports/SK_LMG201_R38_Installed.fbx';current.get_editor_property('asset_import_data').scripted_add_filename(str(full),0,'ReferenceRepair38 installed receiver and cover')
 E.set_metadata_tag(current,'201Revision','ReferenceRepair38: rejected F37 receiver width deformation removed, continuous reference-traced cover; not runtime or 1:1 accepted')
 E.set_metadata_tag(current,'201CoverRevision','ReferenceRepair38: formed stepped shell, continuous rim and image-traced visible inner details')
 E.set_metadata_tag(current,'201DetailSource',str(O/'LMG201_ReferenceRepair38.blend'));E.set_metadata_tag(current,'201PreviousAsset',receipt['backups'][BODY]['asset']);save(current)
 receipt['saved'][BODY]={'sha256':sha(BODY),'replaced_triangles_by_slot':counts,'preserved_front_shared_interior_triangles':kept_shared,'receiver_root_local_y_span':[low,high]};record();print('R38_BODY_SAVED',flush=True)

table=load(WET);wet=dict(table.get_editor_property('wet_materials'))
for path in materials['materials'].values():wet[path]=load(path)
table.set_editor_property('wet_materials',wet);save(table);receipt['saved'][WET]={'sha256':sha(WET)};record()
bindings={current.get_path_name():{str(s.material_slot_name):s.material_interface.get_path_name() if s.material_interface else None for s in current.materials}}
manifest=S/'Material21/bindings.json';data=json.loads(manifest.read_text());data['meshes'].update(bindings);data['current_geometry_revision']='ReferenceRepair38';manifest.write_text(json.dumps(data,indent=2));(O/'bindings.json').write_text(json.dumps(bindings,indent=2))
ex=u.AssetExportTask();ex.object=current;ex.filename=str(O/'Exports/SK_LMG201_R38_Installed.fbx');ex.automated=True;ex.prompt=False;ex.replace_identical=True;ex.options=u.FbxExportOption();ex.options.level_of_detail=False;ex.options.export_morph_targets=False;ex.options.bake_material_inputs=u.FbxMaterialBakeMode.DISABLED
if not u.Exporter.run_asset_export_task(ex):raise RuntimeError('Full export failed')
receipt.update(status='current_r38_saved',source=model['fbx'],reference_images=model['reference_images']);record();print('R38_SAVED',flush=True)
