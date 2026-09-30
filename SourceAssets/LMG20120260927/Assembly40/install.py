"""Scoped live-editor save through the shared bridge; no PIE or game launch."""
import unreal as u,json,hashlib,shutil
from pathlib import Path
O=Path(__file__).parent;S=O.parent;PROJECT=O.parents[2];P='/Game/Weapons/LMG201/Assembly40';cap=json.loads((O/'capture.json').read_text());model=json.loads((O/'model.json').read_text());E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights;M=u.GeometryScript_Materials;Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List;Ed=u.GeometryScript_MeshEdits
receipt=json.loads((O/'delivery.json').read_text()) if (O/'delivery.json').exists() else {'status':'installing','backups':{},'saved':{},'animations_modified':False,'native_code_modified':False}
def record():(O/'delivery.json').write_text(json.dumps(receipt,indent=2))
def file(path):return PROJECT/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(path):return hashlib.sha256(file(path).read_bytes()).hexdigest()
def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing '+path)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
def dynamic(a):
 fn=G.copy_mesh_from_skeletal_mesh if isinstance(a,u.SkeletalMesh) else G.copy_mesh_from_static_mesh;dm,status=fn(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+a.get_path_name())
 return dm
def copy_to(dm,a,slots):
 opt=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[s.material_interface for s in slots],new_material_slot_names=[s.material_slot_name for s in slots],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
 fn=G.copy_mesh_to_skeletal_mesh if isinstance(a,u.SkeletalMesh) else G.copy_mesh_to_static_mesh;_,status=fn(dm,a,opt,u.GeometryScriptMeshWriteLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write '+a.get_path_name())
 a.set_editor_property('materials' if isinstance(a,u.SkeletalMesh) else 'static_materials',slots)
def export(a,key):
 ex=u.AssetExportTask();ex.object=a;ex.filename=str(O/'Exports'/('After_'+key+'.fbx'));ex.automated=True;ex.prompt=False;ex.replace_identical=True;ex.options=u.FbxExportOption();ex.options.level_of_detail=False;ex.options.collision=False;ex.options.export_morph_targets=False;ex.options.bake_material_inputs=u.FbxMaterialBakeMode.DISABLED
 if not u.Exporter.run_asset_export_task(ex):raise RuntimeError('Cannot export '+key)
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; assets retained')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for key in ['Body','RearSight','Wet']:
 path=cap[key]['asset'];expected=receipt['saved'].get(path,{}).get('sha256',cap[key]['sha256'])
 if path in dirty or sha(path)!=expected:raise RuntimeError('Concurrent or unsaved target retained '+path)
 if path not in receipt['backups']:
  dest=P+'/Previous/'+path.rsplit('/',1)[1]+'_PreA40'
  if E.does_asset_exist(dest):raise RuntimeError('Unrecorded backup '+dest)
  a=E.duplicate_asset(path,dest)
  if not a:raise RuntimeError('Cannot backup '+path)
  save(a);target=O/'Before'/file(path).relative_to(PROJECT/'Content');target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file(path),target);receipt['backups'][path]={'asset':a.get_path_name(),'bytes':str(target),'sha256':sha(path)};record()
materials={}
for role in ['Cover','Interior','Satin']:
 name='M_LMG201_A40_'+role;path=P+'/Materials/'+name;a=u.load_asset(path) or E.duplicate_asset('/Game/Weapons/LMG201/HardSurface39/Materials/M_LMG201_H39_'+role,path)
 errors=u.MaterialEditingLibrary.recompile_material(a)
 if errors:raise RuntimeError('Material compile failed '+str(errors))
 save(a);materials[name]=a.get_path_name()
(O/'materials.json').write_text(json.dumps(materials,indent=2))
current=load(cap['Body']['asset']);lookup={str(s.material_slot_name):s.material_interface for s in current.materials};lookup.update({k:load(v) for k,v in materials.items()});lookup['M_LMG201_Trigger']=load(materials['M_LMG201_A40_Satin'])
def imported(name,filename,skeletal):
 digest=hashlib.sha256(Path(filename).read_bytes()).hexdigest();path=P+'/Parts/'+name+'_'+digest[:8];a=u.load_asset(path)
 if not a:
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH if skeletal else u.FBXImportType.FBXIT_STATIC_MESH;opt.import_as_skeletal=skeletal;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
  if skeletal:
   opt.skeleton=current.skeleton;data=opt.skeletal_mesh_import_data;data.set_editor_property('update_skeleton_reference_pose',False);data.set_editor_property('use_t0_as_ref_pose',False);data.set_editor_property('preserve_smoothing_groups',True)
  else:data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.remove_degenerates=False
  data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
  task=u.AssetImportTask();task.filename=filename;task.destination_path=P+'/Parts';task.destination_name=path.rsplit('/',1)[1];task.factory=u.FbxFactory();task.options=opt;task.automated=True;task.replace_existing=False;task.save=False
  flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
  try:A.import_asset_tasks([task])
  finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
  a=load(path)
 prop='materials' if skeletal else 'static_materials';slots=[s.copy() for s in a.get_editor_property(prop)]
 for s in slots:
  key=str(s.material_slot_name)
  if key not in lookup:raise RuntimeError('Unmapped material '+key)
  s.material_interface=lookup[key]
 a.set_editor_property(prop,slots);save(a);return a,slots,digest
path=cap['Body']['asset'];source_sha=hashlib.sha256(Path(model['body_fbx']).read_bytes()).hexdigest()
if receipt['saved'].get(path,{}).get('source_sha256')!=source_sha:
 source,partslots,digest=imported('SK_LMG201_A40_Parts',model['body_fbx'],True);native=dynamic(current);added=dynamic(source);slots=[s.copy() for s in current.materials]
 replaced={'M_LMG201_R30_Steel','M_LMG201_H39_Cover','M_LMG201_H39_Interior','M_LMG201_H39_Receiver','M_LMG201_F37_Interior','M_LMG201_Magazine','M_LMG201_Trigger','M_LMG201_A40_Cover','M_LMG201_A40_Interior','M_LMG201_A40_Satin'}
 _,tl,_=Q.get_all_triangle_indices(native,False);triangles=L.convert_triangle_list_to_array(tl);remove=[];counts={}
 for ti in range(len(triangles)):
  mid,valid=M.get_triangle_material_id(native,ti)
  if valid and str(slots[mid].material_slot_name) in replaced:
   remove.append(ti);key=str(slots[mid].material_slot_name);counts[key]=counts.get(key,0)+1
 for key in ['M_LMG201_H39_Receiver','M_LMG201_Magazine','M_LMG201_Trigger']:
  if not counts.get(key):raise RuntimeError('Missing replacement section '+key)
 Ed.delete_triangles_from_mesh(native,L.convert_array_to_index_list(remove,u.GeometryScriptIndexType.TRIANGLE),True);B.copy_bones_from_mesh(native,added,u.GeometryScriptCopyBonesFromMeshOptions(reindex_weights=True))
 names={str(s.material_slot_name):i for i,s in enumerate(slots)}
 for s in partslots:
  key=str(s.material_slot_name)
  if key not in names:names[key]=len(slots);slots.append(s.copy())
  else:slots[names[key]].material_interface=s.material_interface
 for i,s in enumerate(partslots):M.remap_material_i_ds(added,i,1000+i)
 for i,s in enumerate(partslots):M.remap_material_i_ds(added,1000+i,names[str(s.material_slot_name)])
 Ed.append_mesh(native,added,u.Transform(),True)
 candidate=u.load_asset(P+'/SK_LMG201_A40_Installed') or E.duplicate_asset(path,P+'/SK_LMG201_A40_Installed');copy_to(native,candidate,slots);save(candidate);copy_to(native,current,slots)
 current.get_editor_property('asset_import_data').scripted_add_filename(str(O/'Exports/After_Body.fbx'),0,'Assembly40 full saved body')
 E.set_metadata_tag(current,'201Revision','Assembly40: rail contact, rear seat, local right knob, backed cover well, seated magazine neck and curved trigger');E.set_metadata_tag(current,'201DetailSource',str(O/'LMG201_Assembly40.blend'));save(current);receipt['saved'][path]={'sha256':sha(path),'source_sha256':digest,'removed_by_slot':counts};record()
path=cap['RearSight']['asset'];source_sha=hashlib.sha256(Path(model['rear_fbx']).read_bytes()).hexdigest()
if receipt['saved'].get(path,{}).get('source_sha256')!=source_sha:
 source,partslots,digest=imported('SM_LMG201_A40_RearSight',model['rear_fbx'],False);sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem);settings=sub.get_lod_build_settings(source,0);settings.set_editor_property('remove_degenerates',False);sub.set_lod_build_settings(source,0,settings);save(source)
 dm=dynamic(source);a=load(path);slots=[s.copy() for s in a.static_materials];slots[0].material_interface=load(materials['M_LMG201_A40_Cover']);slots[1].material_interface=load(materials['M_LMG201_A40_Satin'])
 for i,s in enumerate(partslots):M.remap_material_i_ds(dm,i,1000+i)
 for i,s in enumerate(partslots):M.remap_material_i_ds(dm,1000+i,1 if 'Satin' in str(s.material_slot_name) else 0)
 copy_to(dm,a,slots);a.get_editor_property('asset_import_data').scripted_add_filename(str(O/'Exports/After_RearSight.fbx'),0,'Assembly40 connected folding head at native hinge');E.set_metadata_tag(a,'201Revision','Assembly40: connected lower bridge and notched leaf; native pivot retained');save(a);receipt['saved'][path]={'sha256':sha(path),'source_sha256':digest};record()
path=cap['Wet']['asset'];a=load(path);mapping=dict(a.get_editor_property('wet_materials'))
for p in materials.values():mapping[p]=load(p)
a.set_editor_property('wet_materials',mapping);save(a);receipt['saved'][path]={'sha256':sha(path)}
bindings={}
for key in ['Body','RearSight']:
 a=load(cap[key]['asset']);slots=a.materials if key=='Body' else a.static_materials;bindings[a.get_path_name()]={str(s.material_slot_name):s.material_interface.get_path_name() if s.material_interface else None for s in slots};export(a,key)
manifest=S/'Material21/bindings.json';data=json.loads(manifest.read_text());data['meshes'].update(bindings);data['current_geometry_revision']='Assembly40';manifest.write_text(json.dumps(data,indent=2));(O/'bindings.json').write_text(json.dumps(bindings,indent=2))
receipt['status']='current_a40_saved';record();print('A40_CURRENT_SAVED',json.dumps(receipt['saved']),flush=True)
