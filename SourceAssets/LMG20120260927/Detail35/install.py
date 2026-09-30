"""Install local precision edits while retaining native arms, feeds and animation bindings."""
import unreal as u,json,shutil,hashlib
from pathlib import Path
O=Path(__file__).parent;PROJECT=O.parents[2];P='/Game/Weapons/LMG201/Detail35'
BODY='/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10';PROD='/Game/Weapons/LMG201/Production20260927';WET='/Game/Weapons/LMG201/Accessories22/DA_LMG201_AttachmentWetMaterials'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils;M=u.GeometryScript_Materials;B=u.GeometryScript_BoneWeights;Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List;Ed=u.GeometryScript_MeshEdits
source=json.loads((O/'inputs.json').read_text())['assets'];fit=json.loads((O/'model.json').read_text());controls=json.loads((O/'controls.json').read_text());matdata=json.loads((O/'materials.json').read_text());materials=matdata['slot_bindings']
if matdata['status']!='compiled_and_saved':raise RuntimeError('Material production incomplete')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; preserve assets and defer import')
targets=[BODY,PROD+'/SM_LMG201_FrontSight',PROD+'/SM_LMG201_RearSight',WET]
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p in dirty for p in targets):raise RuntimeError('A target has unsaved changes; preserve it')
receipt=json.loads((O/'delivery.json').read_text()) if (O/'delivery.json').exists() else {'status':'installing','backups':{},'saved':{},'tested':False,'rendered':False,'new_runtime_components':0,'animations_changed':False,'old_assets_deleted':False}
def record():(O/'delivery.json').write_text(json.dumps(receipt,indent=2))
def file(path):return PROJECT/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(path):return hashlib.sha256(file(path).read_bytes()).hexdigest()
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
for key in ['Body','FrontSight','RearSight']:
 path=source[key]['asset'].split('.')[0];expected=receipt['saved'].get(path,{}).get('sha256',source[key]['sha256'])
 if sha(path)!=expected:raise RuntimeError('Concurrent target change '+path)
def backup(path):
 if path in receipt['backups']:return
 dest=P+'/Previous/'+path.rsplit('/',1)[1]+'_PreD35'
 if E.does_asset_exist(dest):raise RuntimeError('Unowned backup already exists '+dest)
 old=E.duplicate_asset(path,dest)
 if not old:raise RuntimeError('Cannot retain old asset '+path)
 save(old);src=file(path);dst=O/'Before'/src.relative_to(PROJECT/'Content');dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);receipt['backups'][path]={'asset':old.get_path_name(),'bytes':str(dst),'sha256':sha(path)};record()
for path in targets:backup(path)
manifest=O.parent/'Material21/bindings.json';mb=O/'Before/Material21_bindings.json'
if not mb.exists():shutil.copy2(manifest,mb)
current=u.load_asset(BODY)
def dynamic(a):
 fn=G.copy_mesh_from_skeletal_mesh if isinstance(a,u.SkeletalMesh) else G.copy_mesh_from_static_mesh
 dm,res=fn(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if res!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+a.get_path_name())
 return dm
def copy_to(dm,a,slots):
 opt=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[s.material_interface for s in slots],new_material_slot_names=[s.material_slot_name for s in slots],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
 fn=G.copy_mesh_to_skeletal_mesh if isinstance(a,u.SkeletalMesh) else G.copy_mesh_to_static_mesh
 _,res=fn(dm,a,opt,u.GeometryScriptMeshWriteLOD())
 if res!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write '+a.get_path_name())
 a.set_editor_property('materials' if isinstance(a,u.SkeletalMesh) else 'static_materials',slots)
def import_part(name,src,skeletal=False):
 dest=P+'/Parts/'+name;a=u.load_asset(dest)
 if a:return a
 opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH if skeletal else u.FBXImportType.FBXIT_STATIC_MESH;opt.import_as_skeletal=skeletal;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
 if skeletal:
  opt.skeleton=current.skeleton;data=opt.skeletal_mesh_import_data;data.set_editor_property('update_skeleton_reference_pose',False);data.set_editor_property('use_t0_as_ref_pose',False);data.set_editor_property('preserve_smoothing_groups',True)
 else:
  data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
 data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
 t=u.AssetImportTask();t.filename=src;t.destination_path=P+'/Parts';t.destination_name=name;t.factory=u.FbxFactory();t.options=opt;t.automated=True;t.replace_existing=False;t.save=False;A.import_asset_tasks([t]);a=u.load_asset(dest)
 if not a or not t.imported_object_paths:raise RuntimeError('Import failed '+name)
 prop='materials' if skeletal else 'static_materials';slots=[s.copy() for s in a.get_editor_property(prop)]
 for s in slots:
  key=str(s.material_slot_name)
  if key not in materials:raise RuntimeError('Missing slot mapping '+key)
  s.material_interface=u.load_asset(materials[key])
 a.set_editor_property(prop,slots);save(a);return a
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 if BODY not in receipt['saved']:
  new=import_part('SK_LMG201_D35_Weapon',fit['exports']['Weapon'],True);new_controls=import_part('SK_LMG201_D35_Controls',controls['export'],True);native=dynamic(current);slots=[s.copy() for s in current.materials]
  remove={i for i,s in enumerate(slots) if '_R30_' in str(s.material_slot_name) or str(s.material_slot_name) in controls['replaces_slots']}
  _,tl,_=Q.get_all_triangle_indices(native,False);triangles=L.convert_triangle_list_to_array(tl);delete=[]
  for ti in range(len(triangles)):
   mid,valid=M.get_triangle_material_id(native,ti)
   if valid and mid in remove:delete.append(ti)
  Ed.delete_triangles_from_mesh(native,L.convert_array_to_index_list(delete,u.GeometryScriptIndexType.TRIANGLE),True)
  for asset in [new,new_controls]:
   part=dynamic(asset)
   # Existing native arm and cloth bone table is the canonical SOURCE. Only
   # imported part weights are remapped; the retained surface is not rebound.
   B.copy_bones_from_mesh(native,part,u.GeometryScriptCopyBonesFromMeshOptions(reindex_weights=True))
   names={str(s.material_slot_name):i for i,s in enumerate(slots)};mapping={}
   for i,s in enumerate(asset.materials):
    key=str(s.material_slot_name)
    if key not in names:names[key]=len(slots);slots.append(s.copy())
    else:
     entry=slots[names[key]];entry.material_interface=s.material_interface;slots[names[key]]=entry
    mapping[i]=names[key]
   for i in mapping:M.remap_material_i_ds(part,i,1000+i)
   for i,dst in mapping.items():M.remap_material_i_ds(part,1000+i,dst)
   Ed.append_mesh(native,part,u.Transform(),True)
  candidate=u.load_asset(P+'/SK_LMG201_D35_Installed') or E.duplicate_asset(BODY,P+'/SK_LMG201_D35_Installed')
  if not candidate:raise RuntimeError('Cannot create assembled asset')
  copy_to(native,candidate,slots);save(candidate)
  fbx=O/'Exports/SK_LMG201_D35_Installed.fbx';ex=u.AssetExportTask();ex.object=candidate;ex.filename=str(fbx);ex.automated=True;ex.prompt=False;ex.replace_identical=True;ex.options=u.FbxExportOption();ex.options.level_of_detail=False;ex.options.export_morph_targets=False;ex.options.bake_material_inputs=u.FbxMaterialBakeMode.DISABLED
  if not u.Exporter.run_asset_export_task(ex):raise RuntimeError('Cannot save assembled FBX')
  copy_to(native,current,slots);current.get_editor_property('asset_import_data').scripted_add_filename(str(fbx),0,'Detail35 complete current assembly')
  metadata={'201Revision':'Detail35 + ClothFeed33 + native V7: local sight, receiver, lid interior and control refinement','201CoverRevision':'Detail35: original outer shell locally faired; old flat cut cap removed; inward solid wall, rim, stepped interior and video-visible details','201BodySurfaceRevision':'Detail35: original Receiver vertices locally faired, coherent panel UV normal cleanup; unrelated Surface32 parts retained','201FactoryBodyFinish':'Detail35: region-specific matte receiver, coating and restrained satin hardware; bounded WeaponWetness','201DetailSource':str(O/'LMG201_D35_Editable.blend'),'201PreviousAsset':receipt['backups'][BODY]['asset']}
  for k,v in metadata.items():E.set_metadata_tag(current,k,v)
  save(current);receipt['saved'][BODY]={'sha256':sha(BODY),'candidate':candidate.get_path_name(),'full_fbx':str(fbx),'replaced_triangles':len(delete)};record();print('DETAIL35_BODY_SAVED',flush=True)
 for key in ['FrontSight','RearSight']:
  path=PROD+'/SM_LMG201_'+key
  if path in receipt['saved']:continue
  new=import_part('SM_LMG201_D35_'+key,fit['exports'][key]);dest=u.load_asset(path);slots=[s.copy() for s in new.static_materials];copy_to(dynamic(new),dest,slots);dest.get_editor_property('asset_import_data').scripted_add_filename(fit['exports'][key],0,'Detail35 precision topology on existing folding pivot');E.set_metadata_tag(dest,'201Revision','Detail35: clean precision sight, existing pivot and sight-line; dedicated non-atlas finish');save(dest);receipt['saved'][path]={'sha256':sha(path)};record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
table=u.load_asset(WET);wet=dict(table.get_editor_property('wet_materials'))
for path in matdata['materials'].values():wet[path]=u.load_asset(path)
table.set_editor_property('wet_materials',wet);save(table)
bindings={}
for path in targets[:3]:
 asset=u.load_asset(path);slots=asset.materials if isinstance(asset,u.SkeletalMesh) else asset.static_materials;bindings[asset.get_path_name()]={str(s.material_slot_name):s.material_interface.get_path_name() for s in slots}
data=json.loads(manifest.read_text());data['meshes'].update(bindings);manifest.write_text(json.dumps(data,indent=2),encoding='utf8');(O/'bindings.json').write_text(json.dumps({'meshes':bindings},indent=2))
receipt.update(status='current_201_detail35_saved',materials=matdata['materials'],retained=['native arms and ADS34 outfit profile','cloth box/belt','accepted animations and audio','unrelated barrel, stock, grip and handguard geometry','existing runtime component paths and attachment mounts'],wet_catalog=WET);record();print('DETAIL35_COMPLETE',json.dumps(receipt['saved']),flush=True)
