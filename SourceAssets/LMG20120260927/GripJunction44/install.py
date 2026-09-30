"""Save four repaired grip assets and their finish mapping, retaining gun/actions."""
from pathlib import Path
O=Path(__file__).parent;old=(O.parent/'Assembly40/install.py').read_text()
exec(compile(old.split('if u.get_editor_subsystem')[0].replace('Assembly40','GripJunction44').replace('A40','J44'),str(O/'install.py'),'exec'),globals())
model=json.loads((O/'RuntimeSource/model.json').read_text())
finish=json.loads((O/'materials.json').read_text());sub=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if sub and sub.get_game_world():raise RuntimeError('PIE active; existing assets retained')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for key,row in cap.items():
 p=row['asset']
 if p in dirty or sha(p)!=receipt['saved'].get(p,{}).get('sha256',row['sha256']):raise RuntimeError('Concurrent target retained '+p)

def backup(p):
 if p in receipt['backups']:return
 target=O/'Before'/file(p).relative_to(PROJECT/'Content');target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file(p),target);receipt['backups'][p]={'bytes':str(target),'sha256':sha(p)};record()

current=load(cap['Body']['asset']);lookup={str(s.material_slot_name):s.material_interface for s in current.materials};lookup['M_LMG201_FactoryRearGrip_J44']=load(finish['factory']['material'])

def imported(key,filename,skeletal):
 digest=hashlib.sha256(Path(filename).read_bytes()).hexdigest();path=P+'/Parts/'+('SK' if skeletal else 'SM')+'_J44_'+key+'_'+digest[:8];a=u.load_asset(path)
 if not a:
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH if skeletal else u.FBXImportType.FBXIT_STATIC_MESH;opt.import_as_skeletal=skeletal;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
  if skeletal:
   opt.skeleton=current.skeleton;data=opt.skeletal_mesh_import_data;data.set_editor_property('update_skeleton_reference_pose',False);data.set_editor_property('use_t0_as_ref_pose',False);data.set_editor_property('preserve_smoothing_groups',True)
  else:
   data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.remove_degenerates=False
  data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
  task=u.AssetImportTask();task.filename=filename;task.destination_path=P+'/Parts';task.destination_name=path.rsplit('/',1)[1];task.factory=u.FbxFactory();task.options=opt;task.automated=True;task.save=False;flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
  try:A.import_asset_tasks([task])
  finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
  a=load(path)
 prop='materials' if skeletal else 'static_materials';slots=[s.copy() for s in a.get_editor_property(prop)]
 for i,s in enumerate(slots):
  name=str(s.material_slot_name)
  if skeletal:
   if name not in lookup:raise RuntimeError('Unmapped body grip material '+name)
   s.material_interface=lookup[name]
  else:s.material_interface=load(finish[key]['material'])
  slots[i]=s
 a.set_editor_property(prop,slots);save(a);return a,slots,digest

p=cap['Body']['asset'];digest=hashlib.sha256(Path(model['body_fbx']).read_bytes()).hexdigest()
if receipt['saved'].get(p,{}).get('source_sha256')!=digest:
 source,partslots,digest=imported('factory',model['body_fbx'],True);native=dynamic(current);added=dynamic(source);slots=[s.copy() for s in current.materials]
 _,tl,_=Q.get_all_triangle_indices(native,False);triangles=L.convert_triangle_list_to_array(tl);remove=[]
 for ti in range(len(triangles)):
  mid,valid=M.get_triangle_material_id(native,ti)
  if valid and 'FactoryRearGrip' in str(slots[mid].material_slot_name):remove.append(ti)
 if not remove:raise RuntimeError('No factory grip to replace')
 Ed.delete_triangles_from_mesh(native,L.convert_array_to_index_list(remove,u.GeometryScriptIndexType.TRIANGLE),True);B.copy_bones_from_mesh(native,added,u.GeometryScriptCopyBonesFromMeshOptions(reindex_weights=True));names={str(s.material_slot_name):i for i,s in enumerate(slots)}
 for s in partslots:
  name=str(s.material_slot_name)
  if name not in names:names[name]=len(slots);slots.append(s.copy())
  else:
   t=slots[names[name]];t.material_interface=s.material_interface;slots[names[name]]=t
 for i in range(len(partslots)):M.remap_material_i_ds(added,i,1000+i)
 for i,s in enumerate(partslots):M.remap_material_i_ds(added,1000+i,names[str(s.material_slot_name)])
 Ed.append_mesh(native,added,u.Transform(),True);candidate=u.load_asset(P+'/SK_J44_Installed') or E.duplicate_asset(p,P+'/SK_J44_Installed');copy_to(native,candidate,slots);save(candidate)
 backup(p);copy_to(native,current,slots);current.get_editor_property('asset_import_data').scripted_add_filename(str(O/'Exports/After_Body.fbx'),0,'GripJunction44 continuous rear neck');E.set_metadata_tag(current,'201RearGripRevision','GripJunction44: continuous original grip neck, valid UV0, lower grip retained');E.set_metadata_tag(current,'201DetailSource',str(O/'LMG201_GripJunction44.blend'));save(current)
 receipt['saved'][p]={'sha256':sha(p),'source_sha256':digest};record()

sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
for key in ['stable','balanced','phantom']:
 p=cap[key]['asset'];filename=model['grip_fbx'][key];digest=hashlib.sha256(Path(filename).read_bytes()).hexdigest()
 if receipt['saved'].get(p,{}).get('source_sha256')==digest:continue
 source,partslots,digest=imported(key,filename,False);dm=dynamic(source);a=load(p);slots=[s.copy() for s in a.static_materials]
 for i,s in enumerate(slots):s.material_interface=load(finish[key]['material']);slots[i]=s
 # All visible head and grip faces share the existing polymer slot. The old
 # separate interface slot remains empty, retaining the original slot table.
 for i in range(len(partslots)):M.remap_material_i_ds(dm,i,1000+i)
 for i in range(len(partslots)):M.remap_material_i_ds(dm,1000+i,1)
 backup(p);copy_to(dm,a,slots);settings=sm.get_lod_build_settings(a,0);settings.remove_degenerates=False;sm.set_lod_build_settings(a,0,settings);a.get_editor_property('asset_import_data').scripted_add_filename(str(O/'Exports'/('After_'+key+'.fbx')),0,'GripJunction44 joined neck and original mounting pivot');E.set_metadata_tag(a,'201RearGripRevision','GripJunction44');save(a);receipt['saved'][p]={'sha256':sha(p),'source_sha256':digest,'pivot_changed':False};record()

p=cap['Wet']['asset']
if p not in receipt['saved']:
 a=load(p);mapping=dict(a.get_editor_property('wet_materials'))
 for row in finish.values():mapping[row['material']]=load(row['material'])
 backup(p);a.set_editor_property('wet_materials',mapping);save(a);receipt['saved'][p]={'sha256':sha(p)};record()
bindings={}
for key in ['Body','stable','balanced','phantom']:
 a=load(cap[key]['asset']);slots=a.materials if key=='Body' else a.static_materials;bindings[a.get_path_name()]={str(s.material_slot_name):s.material_interface.get_path_name() if s.material_interface else None for s in slots};export(a,key)
manifest=S/'Material21/bindings.json';data=json.loads(manifest.read_text());data['meshes'].update(bindings);data['current_reargrip_revision']='GripJunction44';manifest.write_text(json.dumps(data,indent=2));(O/'bindings.json').write_text(json.dumps(bindings,indent=2));receipt.update(status='current_j44_saved',animations_modified=False,native_code_modified=False,runtime_tested=False,rendered=False,runtime_source=model['runtime_blend'],runtime_triangles={key:model['grips'][key]['runtime_triangles'] for key in ['stable','balanced','phantom']});record();print('J44_CURRENT_SAVED',len(receipt['saved']),flush=True)
