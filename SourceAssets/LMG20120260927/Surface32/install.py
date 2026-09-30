"""Install edited original surfaces without adding runtime components."""
import unreal as u,json,shutil,hashlib
from pathlib import Path
O=Path(__file__).parent;PROJECT=O.parents[2];P='/Game/Weapons/LMG201/Surface32';BODY='/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10';PROD='/Game/Weapons/LMG201/Production20260927';WET='/Game/Weapons/LMG201/Accessories22/DA_LMG201_AttachmentWetMaterials'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils;M=u.GeometryScript_Materials;B=u.GeometryScript_BoneWeights;Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List;Ed=u.GeometryScript_MeshEdits;ME=u.MaterialEditingLibrary
fit=json.loads((O/'exports.json').read_text());materials=json.loads((O/'materials.json').read_text())['materials']
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; save deferred')
targets=[BODY,PROD+'/SM_LMG201_FrontSight',PROD+'/SM_LMG201_RearSight',WET]
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(t in dirty for t in targets):raise RuntimeError('A target has unsaved work; preserve it')
receipt=json.loads((O/'delivery.json').read_text()) if (O/'delivery.json').exists() else {'status':'installing','backups':{},'saved':{},'tested':False,'rendered':False,'new_components':0,'animations_changed':False}
def record():(O/'delivery.json').write_text(json.dumps(receipt,indent=2))
def file(path):return PROJECT/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(path):return hashlib.sha256(file(path).read_bytes()).hexdigest()
def save(asset):
 if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
def backup(path):
 if path in receipt['backups']:return
 dest=P+'/Previous/'+path.rsplit('/',1)[1]+'_PreS32'
 if E.does_asset_exist(dest):raise RuntimeError('Backup path already exists '+dest)
 old=E.duplicate_asset(path,dest)
 if not old:raise RuntimeError('Cannot retain previous asset '+path)
 save(old);src=file(path);dst=O/'Before'/src.relative_to(PROJECT/'Content');dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
 receipt['backups'][path]={'asset':old.get_path_name(),'bytes':str(dst),'sha256':sha(path)};record()
def dynamic(asset):
 fn=G.copy_mesh_from_skeletal_mesh if isinstance(asset,u.SkeletalMesh) else G.copy_mesh_from_static_mesh
 dm,result=fn(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+asset.get_path_name())
 return dm
def copy_to(dm,asset,slots):
 opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[s.material_interface for s in slots],new_material_slot_names=[s.material_slot_name for s in slots],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
 fn=G.copy_mesh_to_skeletal_mesh if isinstance(asset,u.SkeletalMesh) else G.copy_mesh_to_static_mesh
 _,res=fn(dm,asset,opts,u.GeometryScriptMeshWriteLOD())
 if res!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Mesh write failed '+asset.get_path_name())
 asset.set_editor_property('materials' if isinstance(asset,u.SkeletalMesh) else 'static_materials',slots)
current=u.load_asset(BODY)
if BODY not in receipt['saved'] and 'Install30' not in str(E.get_metadata_tag(current,'201Revision')):raise RuntimeError('Current source is no longer Install30; do not replace a different revision')
for path in targets:backup(path)
manifest=O.parent/'Material21/bindings.json';mb=O/'Before/Material21_bindings.json'
if not mb.exists():shutil.copy2(manifest,mb)
def import_part(name,src,skeletal=False):
 dest=P+'/Parts/'+name;asset=u.load_asset(dest)
 if asset:return asset
 opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH if skeletal else u.FBXImportType.FBXIT_STATIC_MESH
 opt.import_as_skeletal=skeletal;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
 if skeletal:
  opt.skeleton=current.skeleton;data=opt.skeletal_mesh_import_data;data.set_editor_property('update_skeleton_reference_pose',False);data.set_editor_property('use_t0_as_ref_pose',False);data.set_editor_property('preserve_smoothing_groups',True)
 else:
  data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
 data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
 t=u.AssetImportTask();t.filename=src;t.destination_path=P+'/Parts';t.destination_name=name;t.factory=u.FbxFactory();t.options=opt;t.automated=True;t.replace_existing=False;t.save=False;A.import_asset_tasks([t]);asset=u.load_asset(dest)
 if not asset or not t.imported_object_paths:raise RuntimeError('Import failed '+name)
 prop='materials' if skeletal else 'static_materials';slots=[s.copy() for s in asset.get_editor_property(prop)]
 for s in slots:s.material_interface=u.load_asset(materials[fit['material_roles'][str(s.material_slot_name)]])
 asset.set_editor_property(prop,slots);save(asset);return asset
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
bindings={}
try:
 if BODY not in receipt['saved']:
  new=import_part('SK_LMG201_S32_Weapon',fit['exports']['Weapon'],True);native=dynamic(current);part=dynamic(new);slots=[s.copy() for s in current.materials]
  revised={str(s.material_slot_name):i for i,s in enumerate(slots) if '_R30_' in str(s.material_slot_name)}
  _,tl,_=Q.get_all_triangle_indices(native,False);tris=L.convert_triangle_list_to_array(tl);delete=[]
  revised_ids=set(revised.values())
  for i in range(len(tris)):
   mid,valid=M.get_triangle_material_id(native,i)
   if valid and mid in revised_ids:delete.append(i)
  Ed.delete_triangles_from_mesh(native,L.convert_array_to_index_list(delete,u.GeometryScriptIndexType.TRIANGLE),True)
  B.copy_bones_from_mesh(part,native,u.GeometryScriptCopyBonesFromMeshOptions(reindex_weights=True));mapping={}
  for i,s in enumerate(new.materials):
   key=str(s.material_slot_name)
   if key not in revised:raise RuntimeError('Unexpected surface slot '+key)
   mapping[i]=revised[key];entry=slots[revised[key]];entry.material_interface=s.material_interface;slots[revised[key]]=entry
  for i in mapping:M.remap_material_i_ds(part,i,1000+i)
  for i,dst in mapping.items():M.remap_material_i_ds(part,1000+i,dst)
  Ed.append_mesh(native,part,u.Transform(),True)
  candidate=u.load_asset(P+'/SK_LMG201_S32_Installed') or E.duplicate_asset(BODY,P+'/SK_LMG201_S32_Installed')
  if not candidate:raise RuntimeError('Cannot create assembled candidate')
  copy_to(native,candidate,slots);save(candidate)
  fbx=O/'Exports/SK_LMG201_S32_Installed.fbx';ex=u.AssetExportTask();ex.object=candidate;ex.filename=str(fbx);ex.automated=True;ex.prompt=False;ex.replace_identical=True;ex.options=u.FbxExportOption();ex.options.level_of_detail=False;ex.options.export_morph_targets=False;ex.options.bake_material_inputs=u.FbxMaterialBakeMode.DISABLED
  if not u.Exporter.run_asset_export_task(ex):raise RuntimeError('Cannot export full source')
  copy_to(native,current,slots);current.get_editor_property('asset_import_data').scripted_add_filename(str(fbx),0,'Surface32 full assembly')
  E.set_metadata_tag(current,'201Revision','Surface32: original R30 topology refined, low-glare PBR, native arms/magazine/controls retained')
  E.set_metadata_tag(current,'201BodySurfaceRevision','Surface32: bounded original-vertex fairing, planar panels, original UV0 structural normal')
  E.set_metadata_tag(current,'201FactoryBodyFinish','Surface32: dark matte coating, bounded wet roughness; original polymer/metal masks')
  E.set_metadata_tag(current,'201PreviousAsset',receipt['backups'][BODY]['asset']);save(current)
  receipt['saved'][BODY]={'sha256':sha(BODY),'candidate':candidate.get_path_name(),'full_fbx':str(fbx),'revised_triangles':len(delete)};record();print('S32_BODY_SAVED',flush=True)
 for key in ['FrontSight','RearSight']:
  path=PROD+'/SM_LMG201_'+key
  if path in receipt['saved']:continue
  asset=import_part('SM_LMG201_S32_'+key,fit['exports'][key]);dest=u.load_asset(path);slots=[s.copy() for s in asset.static_materials];copy_to(dynamic(asset),dest,slots)
  dest.get_editor_property('asset_import_data').scripted_add_filename(fit['exports'][key],0,'Surface32 original vertices')
  E.set_metadata_tag(dest,'201Revision','Surface32 existing sight surface refined; hinge and topology retained');save(dest);receipt['saved'][path]={'sha256':sha(path)};record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
table=u.load_asset(WET);wet=dict(table.get_editor_property('wet_materials'))
for path in materials.values():wet[path]=u.load_asset(path)
table.set_editor_property('wet_materials',wet);save(table)
for path in targets[:3]:
 asset=u.load_asset(path);slots=asset.materials if isinstance(asset,u.SkeletalMesh) else asset.static_materials
 bindings[asset.get_path_name()]={str(s.material_slot_name):s.material_interface.get_path_name() for s in slots}
data=json.loads(manifest.read_text());data['meshes'].update(bindings);manifest.write_text(json.dumps(data,indent=2),encoding='utf8');(O/'bindings.json').write_text(json.dumps({'meshes':bindings},indent=2))
receipt.update(status='current_201_refined_and_saved',materials=materials,normal_texture='Install30/T_201_R29_Surface_Normal unchanged',old_assets_deleted=False,retained_native=['arms','magazine','controls','bipod','animations','attachment transforms'],wet_catalog=WET);record();print('S32_COMPLETE',json.dumps(receipt['saved']),flush=True)
