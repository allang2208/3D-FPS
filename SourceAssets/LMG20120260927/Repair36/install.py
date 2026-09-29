"""Replace only the failed moving lid and rebind private, correctly compiled finishes."""
import unreal as u,json,hashlib,shutil
from pathlib import Path
O=Path(__file__).parent;PROJECT=O.parents[2];P='/Game/Weapons/LMG201/Repair36';BODY='/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10';PROD='/Game/Weapons/LMG201/Production20260927';WET='/Game/Weapons/LMG201/Accessories22/DA_LMG201_AttachmentWetMaterials';PROPS='/Game/Weapons/LMG201/ClothFeed33/Parts/SK_LMG201_Cloth33_Props'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights;M=u.GeometryScript_Materials;Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List;Ed=u.GeometryScript_MeshEdits
capture=json.loads((O/'capture.json').read_text());lid=json.loads((O/'lid.json').read_text());matdata=json.loads((O/'materials.json').read_text());bindings=matdata['slot_bindings']
if lid['outlier_vertices']!=0 or matdata['status']!='compiled_and_saved':raise RuntimeError('Source repair incomplete')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; defer target writes')
targets=[BODY,PROD+'/SM_LMG201_FrontSight',PROD+'/SM_LMG201_RearSight',PROPS,WET]
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p in dirty for p in targets):raise RuntimeError('Target has unsaved edits')
receipt=json.loads((O/'delivery.json').read_text()) if (O/'delivery.json').exists() else {'status':'installing','backups':{},'saved':{},'new_runtime_components':0,'animations_changed':False,'old_assets_deleted':False}
def record():(O/'delivery.json').write_text(json.dumps(receipt,indent=2))
def file(p):return PROJECT/'Content'/(p.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(p):return hashlib.sha256(file(p).read_bytes()).hexdigest()
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
if sha(BODY)!=receipt['saved'].get(BODY,{}).get('sha256',capture['sha256']):raise RuntimeError('Body changed after capture; preserve concurrent work')
for path in targets:
 if path in receipt['backups']:continue
 dest=P+'/Previous/'+path.rsplit('/',1)[1]+'_PreR36'
 if E.does_asset_exist(dest):raise RuntimeError('Unowned backup exists '+dest)
 old=E.duplicate_asset(path,dest)
 if not old:raise RuntimeError('Backup failed '+path)
 save(old);dst=O/'Before'/file(path).relative_to(PROJECT/'Content');dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file(path),dst);receipt['backups'][path]={'asset':old.get_path_name(),'bytes':str(dst),'sha256':sha(path)};record()
manifest=O.parent/'Material21/bindings.json';mb=O/'Before/Material21_bindings.json'
if not mb.exists():shutil.copy2(manifest,mb)
def dynamic(a):
 dm,res=G.copy_mesh_from_skeletal_mesh(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if res!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+a.get_path_name())
 return dm
def assign(a):
 prop='materials' if isinstance(a,u.SkeletalMesh) else 'static_materials';slots=[s.copy() for s in a.get_editor_property(prop)]
 for i,s in enumerate(slots):
  key=str(s.material_slot_name)
  if key in bindings:s.material_interface=u.load_asset(bindings[key]);slots[i]=s
 a.set_editor_property(prop,slots);return slots
def copy_to(dm,a,slots):
 opt=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[s.material_interface for s in slots],new_material_slot_names=[s.material_slot_name for s in slots],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
 _,res=G.copy_mesh_to_skeletal_mesh(dm,a,opt,u.GeometryScriptMeshWriteLOD())
 if res!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write '+a.get_path_name())
 a.set_editor_property('materials',slots)
current=u.load_asset(BODY)
if BODY not in receipt['saved']:
 path=P+'/Parts/SK_LMG201_R36_Cover';part_asset=u.load_asset(path)
 if not part_asset:
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=current.skeleton
  data=opt.skeletal_mesh_import_data;data.set_editor_property('update_skeleton_reference_pose',False);data.set_editor_property('use_t0_as_ref_pose',False);data.set_editor_property('preserve_smoothing_groups',True);data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
  t=u.AssetImportTask();t.filename=lid['export'];t.destination_path=P+'/Parts';t.destination_name='SK_LMG201_R36_Cover';t.factory=u.FbxFactory();t.options=opt;t.automated=True;t.save=False
  flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
  try:A.import_asset_tasks([t])
  finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
  part_asset=u.load_asset(path)
  if not part_asset or not t.imported_object_paths:raise RuntimeError('Lid import failed')
 assign(part_asset);save(part_asset);native=dynamic(current);part=dynamic(part_asset);slots=assign(current);_,bones=B.get_all_bones_info(native);cover_id=next(b.index for b in bones if str(b.name)=='LMG201_Cover');cache={}
 def on_cover(vi):
  if vi not in cache:
   _,weights,valid=B.get_vertex_bone_weights(native,vi);cache[vi]=valid and sum(w.weight for w in weights if w.bone_index==cover_id)>.999
  return cache[vi]
 _,tl,_=Q.get_all_triangle_indices(native,False);triangles=L.convert_triangle_list_to_array(tl);delete=[];candidates={i for i,s in enumerate(slots) if str(s.material_slot_name) in lid['material_slots']}
 for ti,tri in enumerate(triangles):
  mid,valid=M.get_triangle_material_id(native,ti)
  if valid and mid in candidates and all(on_cover(v) for v in [tri.x,tri.y,tri.z]):delete.append(ti)
 if not delete:raise RuntimeError('No installed lid faces selected')
 Ed.delete_triangles_from_mesh(native,L.convert_array_to_index_list(delete,u.GeometryScriptIndexType.TRIANGLE),True);B.copy_bones_from_mesh(native,part,u.GeometryScriptCopyBonesFromMeshOptions(reindex_weights=True));names={str(s.material_slot_name):i for i,s in enumerate(slots)}
 for i,s in enumerate(part_asset.materials):M.remap_material_i_ds(part,i,1000+i)
 for i,s in enumerate(part_asset.materials):M.remap_material_i_ds(part,1000+i,names[str(s.material_slot_name)])
 Ed.append_mesh(native,part,u.Transform(),True);candidate=u.load_asset(P+'/SK_LMG201_R36_Installed') or E.duplicate_asset(BODY,P+'/SK_LMG201_R36_Installed');copy_to(native,candidate,slots);save(candidate);copy_to(native,current,slots)
 full=O/'Exports/SK_LMG201_R36_Installed.fbx';current.get_editor_property('asset_import_data').scripted_add_filename(str(full),0,'Repair36 full assembly source')
 E.set_metadata_tag(current,'201Revision','Repair36: bounded cover wall, receiver-matched coating and skeletal cloth material; Detail35 body and ClothFeed33 retained');E.set_metadata_tag(current,'201CoverRevision','Repair36: remove 12 exploded inner-shell vertices by rebuilding pre-offset lid with bounded normals');E.set_metadata_tag(current,'201DetailSource',str(O/'LMG201_R36_Lid.blend'));E.set_metadata_tag(current,'201PreviousAsset',receipt['backups'][BODY]['asset']);save(current);receipt['saved'][BODY]={'sha256':sha(BODY),'replaced_lid_triangles':len(delete),'source_fbx':str(full)};record()
for path in targets[1:-1]:
 asset=u.load_asset(path);assign(asset);save(asset);receipt['saved'][path]={'sha256':sha(path)};record()
table=u.load_asset(WET);wet=dict(table.get_editor_property('wet_materials'))
for path in matdata['materials'].values():wet[path]=u.load_asset(path)
for slot in capture['slots']:
 if slot['slot'] in bindings:wet[slot['material']]=u.load_asset(bindings[slot['slot']])
table.set_editor_property('wet_materials',wet);save(table);receipt['saved'][WET]={'sha256':sha(WET)};record()
# Read back the actual saved asset bindings, not the planned material variables.
saved_bindings={}
for path in targets[:-1]:
 asset=u.load_asset(path);slots=asset.materials if isinstance(asset,u.SkeletalMesh) else asset.static_materials;saved_bindings[asset.get_path_name()]={str(s.material_slot_name):s.material_interface.get_path_name() if s.material_interface else None for s in slots}
data=json.loads(manifest.read_text());data['meshes'].update(saved_bindings);manifest.write_text(json.dumps(data,indent=2));(O/'bindings.json').write_text(json.dumps(saved_bindings,indent=2))
full=O/'Exports/SK_LMG201_R36_Installed.fbx';ex=u.AssetExportTask();ex.object=current;ex.filename=str(full);ex.automated=True;ex.prompt=False;ex.replace_identical=True;ex.options=u.FbxExportOption();ex.options.level_of_detail=False;ex.options.export_morph_targets=False;ex.options.bake_material_inputs=u.FbxMaterialBakeMode.DISABLED
if not u.Exporter.run_asset_export_task(ex):raise RuntimeError('Cannot export final saved geometry')
receipt.update(status='current_201_repair36_saved',materials=matdata['materials'],source_lid_check=lid,game_started=False,game_tested=False);record();print('REPAIR36_SAVED',json.dumps(receipt['saved']),flush=True)
