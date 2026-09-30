import unreal as u,json,hashlib,shutil
from pathlib import Path
O=Path(__file__).parent;S=O.parent;PROJECT=O.parents[2];P='/Game/Weapons/LMG201/HardSurface39'
cap=json.loads((O/'capture.json').read_text());model=json.loads((O/'model.json').read_text());materials=json.loads((O/'materials.json').read_text())['materials']
BODY=cap['Body']['asset'];BASE=cap['BipodBase']['asset'];WET=cap['Wet']['asset'];E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights;M=u.GeometryScript_Materials;Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List;Ed=u.GeometryScript_MeshEdits
receipt={'status':'installing','backups':{},'saved':{},'animations_modified':False,'bipod_legs_modified':False,'native_code_modified':False}
if (O/'delivery.json').exists():receipt=json.loads((O/'delivery.json').read_text())
def record():(O/'delivery.json').write_text(json.dumps(receipt,indent=2))
def file(path):return PROJECT/'Content'/(path.removeprefix('/Game/')+'.uasset')
def sha(path):return hashlib.sha256(file(path).read_bytes()).hexdigest()
def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing '+path)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
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
def export(a,key):
 task=u.AssetExportTask();task.object=a;task.filename=str(O/'Exports'/('After_'+key+'.fbx'));task.automated=True;task.prompt=False;task.replace_identical=True;task.options=u.FbxExportOption();task.options.level_of_detail=False;task.options.export_morph_targets=False;task.options.bake_material_inputs=u.FbxMaterialBakeMode.DISABLED
 if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export failed '+key)
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; current assets retained')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for key in ['Body','BipodBase','Wet']:
 path=cap[key]['asset'];expected=receipt['saved'].get(path,{}).get('sha256',cap[key]['sha256'])
 if path in dirty or sha(path)!=expected:raise RuntimeError('Concurrent or unsaved target retained '+path)
 if path not in receipt['backups']:
  dest=P+'/Previous/'+path.rsplit('/',1)[1]+'_PreH39'
  if E.does_asset_exist(dest):raise RuntimeError('Unrecorded backup exists '+dest)
  old=E.duplicate_asset(path,dest)
  if not old:raise RuntimeError('Cannot backup '+path)
  save(old);target=O/'Before'/file(path).relative_to(PROJECT/'Content');target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file(path),target);receipt['backups'][path]={'asset':old.get_path_name(),'bytes':str(target),'sha256':sha(path)};record()
current=load(BODY);oldlookup={str(s.material_slot_name):s.material_interface for s in current.materials}
def imported(name,fbx,skeletal):
 path=P+'/Parts/'+name;a=u.load_asset(path)
 if not a:
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH if skeletal else u.FBXImportType.FBXIT_STATIC_MESH;opt.import_as_skeletal=skeletal;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
  if skeletal:
   opt.skeleton=current.skeleton;data=opt.skeletal_mesh_import_data;data.set_editor_property('update_skeleton_reference_pose',False);data.set_editor_property('use_t0_as_ref_pose',False);data.set_editor_property('preserve_smoothing_groups',True)
  else:data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.remove_degenerates=False
  data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
  task=u.AssetImportTask();task.filename=fbx;task.destination_path=P+'/Parts';task.destination_name=name;task.factory=u.FbxFactory();task.options=opt;task.automated=True;task.replace_existing=False;task.save=False
  flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
  try:A.import_asset_tasks([task])
  finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
  a=load(path)
 prop='materials' if skeletal else 'static_materials';slots=[s.copy() for s in a.get_editor_property(prop)]
 for i,s in enumerate(slots):
  key=str(s.material_slot_name)
  if key in materials:s.material_interface=load(materials[key])
  elif key in oldlookup:s.material_interface=oldlookup[key]
  else:raise RuntimeError('Unmapped material '+key)
  slots[i]=s
 a.set_editor_property(prop,slots);save(a);return a,slots

body_source_sha=hashlib.sha256(Path(model['body_fbx']).read_bytes()).hexdigest()
if BODY not in receipt['saved'] or receipt['saved'][BODY].get('source_sha256')!=body_source_sha:
 part,partslots=imported('SK_LMG201_H39_BodyParts_'+body_source_sha[:8],model['body_fbx'],True);native=dynamic(current);added=dynamic(part);slots=[s.copy() for s in current.materials]
 # All current users of the common R30 slots are included: three original
 # carry/trigger/sight-base parts travel unchanged beside the seven edited ones.
 replaced={'M_LMG201_R30_Surface','M_LMG201_R30_Interior','M_LMG201_R30_Steel','M_LMG201_F37_Receiver','M_LMG201_F37_Interior','M_LMG201_H39_Cover','M_LMG201_H39_Interior','M_LMG201_H39_Satin','M_LMG201_H39_Receiver','M_LMG201_H39_Handguard'}
 _,tl,_=Q.get_all_triangle_indices(native,False);tris=L.convert_triangle_list_to_array(tl);remove=[];counts={}
 for ti in range(len(tris)):
  mi,valid=M.get_triangle_material_id(native,ti)
  if valid and str(slots[mi].material_slot_name) in replaced:remove.append(ti);key=str(slots[mi].material_slot_name);counts[key]=counts.get(key,0)+1
 if not counts.get('M_LMG201_F37_Receiver',counts.get('M_LMG201_H39_Receiver',0)) or not counts.get('M_LMG201_R30_Surface') or not counts.get('M_LMG201_F37_Interior'):raise RuntimeError('Replacement scope incomplete '+str(counts))
 Ed.delete_triangles_from_mesh(native,L.convert_array_to_index_list(remove,u.GeometryScriptIndexType.TRIANGLE),True)
 B.copy_bones_from_mesh(native,added,u.GeometryScriptCopyBonesFromMeshOptions(reindex_weights=True))
 names={str(s.material_slot_name):i for i,s in enumerate(slots)}
 for s in partslots:
  key=str(s.material_slot_name)
  if key not in names:names[key]=len(slots);slots.append(s.copy())
 for i,s in enumerate(partslots):M.remap_material_i_ds(added,i,1000+i)
 for i,s in enumerate(partslots):M.remap_material_i_ds(added,1000+i,names[str(s.material_slot_name)])
 Ed.append_mesh(native,added,u.Transform(),True)
 candidate=u.load_asset(P+'/SK_LMG201_H39_Installed') or E.duplicate_asset(BODY,P+'/SK_LMG201_H39_Installed');copy_to(native,candidate,slots);save(candidate);copy_to(native,current,slots)
 current.get_editor_property('asset_import_data').scripted_add_filename(str(O/'Exports/After_Body.fbx'),0,'HardSurface39 complete saved assembly')
 E.set_metadata_tag(current,'201Revision','HardSurface39: precise front parts and rail; fitted receiver/handguard panels; ReferenceRepair38 cover retained')
 E.set_metadata_tag(current,'201DetailSource',str(O/'LMG201_HardSurface39.blend'));save(current);receipt['saved'][BODY]={'sha256':sha(BODY),'removed_by_slot':counts,'source_sha256':body_source_sha};record()
base_source_sha=hashlib.sha256(Path(model['base_fbx']).read_bytes()).hexdigest()
if BASE not in receipt['saved'] or receipt['saved'][BASE].get('source_sha256')!=base_source_sha or receipt['saved'][BASE].get('import_recipe')!='keep_small_faces':
 source,partslots=imported('SM_LMG201_H39_BipodBase_'+base_source_sha[:8]+'_KeepEdges',model['base_fbx'],False)
 subsystem=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem);build=subsystem.get_lod_build_settings(source,0);build.set_editor_property('remove_degenerates',False);subsystem.set_lod_build_settings(source,0,build);save(source)
 dm=dynamic(source);a=load(BASE);slots=[s.copy() for s in a.static_materials]
 slots[0].material_interface=load(materials['M_LMG201_H39_Cover']);slots[1].material_interface=load(materials['M_LMG201_H39_Interior'])
 for i,s in enumerate(partslots):M.remap_material_i_ds(dm,i,1000+i)
 for i,s in enumerate(partslots):M.remap_material_i_ds(dm,1000+i,1 if 'Interior' in str(s.material_slot_name) else 0)
 copy_to(dm,a,slots);a.get_editor_property('asset_import_data').scripted_add_filename(str(O/'Exports/After_BipodBase.fbx'),0,'H39 compact mount; native leg pivots retained');E.set_metadata_tag(a,'201Revision','HardSurface39: compact tube saddle and pivot ears, removed old long wedge base');save(a);receipt['saved'][BASE]={'sha256':sha(BASE),'source_sha256':base_source_sha,'import_recipe':'keep_small_faces'};record()
wet=load(WET);mapping=dict(wet.get_editor_property('wet_materials'))
for path in materials.values():mapping[path]=load(path)
wet.set_editor_property('wet_materials',mapping);save(wet);receipt['saved'][WET]={'sha256':sha(WET)}
bindings={}
for key in ['Body','BipodBase']:
 a=load(cap[key]['asset']);slots=a.materials if key=='Body' else a.static_materials;bindings[a.get_path_name()]={str(s.material_slot_name):s.material_interface.get_path_name() if s.material_interface else None for s in slots};export(a,key)
manifest=S/'Material21/bindings.json';data=json.loads(manifest.read_text());data['meshes'].update(bindings);data['current_geometry_revision']='HardSurface39';manifest.write_text(json.dumps(data,indent=2));(O/'bindings.json').write_text(json.dumps(bindings,indent=2))
receipt['status']='current_h39_saved';record();print('H39_CURRENT_SAVED',flush=True)
