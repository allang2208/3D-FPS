"""Save geometry and the 201-only material family without starting PIE."""
from pathlib import Path
O=Path(__file__).parent
old=(O.parent/'Assembly40/install.py').read_text()
prefix=old.split('if u.get_editor_subsystem')[0].replace('Assembly40','SightFinish41').replace('A40','S41')
exec(compile(prefix,str(O/'install.py'),'exec'),globals())
sub=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if sub and sub.get_game_world():raise RuntimeError('PIE active; targets retained')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
targets=json.loads((O/'finish_targets.json').read_text());finish=json.loads((O/'materials.json').read_text());mapping=finish['mapping']
if finish.get('status')!='compiled_and_saved':raise RuntimeError('Finish authoring incomplete')
for path,row in targets.items():
 package=path.split('.')[0];expected=receipt['saved'].get(package,{}).get('sha256',row['sha256'])
 if package in dirty or sha(package)!=expected:raise RuntimeError('Concurrent target retained '+path)
wetpath=cap['Wet']['asset']
if wetpath in dirty or sha(wetpath)!=receipt['saved'].get(wetpath,{}).get('sha256',cap['Wet']['sha256']):raise RuntimeError('Concurrent wet table retained')
def backup(path):
 package=path.split('.')[0]
 if package not in receipt['backups']:
  dest=O/'Before'/file(package).relative_to(PROJECT/'Content');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file(package),dest);receipt['backups'][package]={'bytes':str(dest),'sha256':sha(package)};record()
def mapped(m):return load(mapping.get(m.get_path_name(),m.get_path_name())) if m else None
current=load(cap['Body']['asset']);lookup={str(s.material_slot_name):mapped(s.material_interface) for s in current.materials}
cover=mapped(load('/Game/Weapons/LMG201/Assembly40/Materials/M_LMG201_A40_Cover'))
satin=mapped(load('/Game/Weapons/LMG201/Assembly40/Materials/M_LMG201_A40_Satin'))
lookup.update({'M_LMG201_S41_Cover':cover,'M_LMG201_S41_Satin':satin,'M_LMG201_Trigger_S41':satin})
# Reuse the known native FBX importer, preserving reference skeleton and normals.
exec(compile(old[old.index('def imported('):old.index("path=cap['Body']['asset'];source_sha")],str(O/'install.py'),'exec'),globals())
path=cap['Body']['asset'];source_sha=hashlib.sha256(Path(model['body_fbx']).read_bytes()).hexdigest()
if receipt['saved'].get(path,{}).get('source_sha256')!=source_sha:
 backup(path);source,partslots,digest=imported('SK_LMG201_S41_Parts',model['body_fbx'],True)
 for s in partslots:
  if str(s.material_slot_name)=='M_LMG201_Trigger_S41':s.material_slot_name=u.Name('M_LMG201_Trigger')
 native=dynamic(current);added=dynamic(source);slots=[s.copy() for s in current.materials]
 replaced={'M_LMG201_H39_Cover','M_LMG201_H39_Interior','M_LMG201_H39_Receiver','M_LMG201_Magazine','M_LMG201_Trigger','M_LMG201_A40_Cover','M_LMG201_A40_Interior','M_LMG201_A40_Satin','M_LMG201_S41_Cover','M_LMG201_S41_Satin'}
 _,tl,_=Q.get_all_triangle_indices(native,False);triangles=L.convert_triangle_list_to_array(tl);remove=[];counts={}
 for ti in range(len(triangles)):
  mid,valid=M.get_triangle_material_id(native,ti)
  if valid and str(slots[mid].material_slot_name) in replaced:
   remove.append(ti);key=str(slots[mid].material_slot_name);counts[key]=counts.get(key,0)+1
 for key in ['M_LMG201_H39_Receiver','M_LMG201_Magazine','M_LMG201_Trigger']:
  if not counts.get(key):raise RuntimeError('Missing replacement section '+key)
 Ed.delete_triangles_from_mesh(native,L.convert_array_to_index_list(remove,u.GeometryScriptIndexType.TRIANGLE),True);B.copy_bones_from_mesh(native,added,u.GeometryScriptCopyBonesFromMeshOptions(reindex_weights=True))
 names={str(s.material_slot_name):i for i,s in enumerate(slots)}
 for i,s in enumerate(slots):s.material_interface=mapped(s.material_interface);slots[i]=s
 for s in partslots:
  key=str(s.material_slot_name)
  if key not in names:names[key]=len(slots);slots.append(s.copy())
  else:
   target=slots[names[key]];target.material_interface=s.material_interface;slots[names[key]]=target
 for i,s in enumerate(partslots):M.remap_material_i_ds(added,i,1000+i)
 for i,s in enumerate(partslots):M.remap_material_i_ds(added,1000+i,names[str(s.material_slot_name)])
 Ed.append_mesh(native,added,u.Transform(),True)
 candidate=u.load_asset(P+'/SK_LMG201_S41_Installed') or E.duplicate_asset(path,P+'/SK_LMG201_S41_Installed');copy_to(native,candidate,slots);save(candidate);copy_to(native,current,slots)
 current.get_editor_property('asset_import_data').scripted_add_filename(str(O/'Exports/After_Body.fbx'),0,'SightFinish41 saved body')
 E.set_metadata_tag(current,'201Revision','SightFinish41: open ADS notch, connected trigger guard and blade, QBZ191-referenced finish');E.set_metadata_tag(current,'201DetailSource',str(O/'LMG201_SightFinish41.blend'));save(current);receipt['saved'][path]={'sha256':sha(path),'source_sha256':digest,'removed_by_slot':counts};record()
path=cap['RearSight']['asset'];source_sha=hashlib.sha256(Path(model['rear_fbx']).read_bytes()).hexdigest()
if receipt['saved'].get(path,{}).get('source_sha256')!=source_sha:
 backup(path);source,partslots,digest=imported('SM_LMG201_S41_RearSight',model['rear_fbx'],False);sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem);settings=sub.get_lod_build_settings(source,0);settings.set_editor_property('remove_degenerates',False);sub.set_lod_build_settings(source,0,settings);save(source)
 dm=dynamic(source);a=load(path);slots=[s.copy() for s in a.static_materials]
 for i,s in enumerate(slots):s.material_interface=mapped(s.material_interface);slots[i]=s
 for i,s in enumerate(partslots):M.remap_material_i_ds(dm,i,1000+i)
 for i,s in enumerate(partslots):M.remap_material_i_ds(dm,1000+i,1 if 'Satin' in str(s.material_slot_name) else 0)
 copy_to(dm,a,slots);a.get_editor_property('asset_import_data').scripted_add_filename(str(O/'Exports/After_RearSight.fbx'),0,'SightFinish41 broad recessed notch at original aim line');E.set_metadata_tag(a,'201Revision','SightFinish41');save(a);receipt['saved'][path]={'sha256':sha(path),'source_sha256':digest};record()
# Apply the same 201 finish only where the saved mesh actually references a
# changed material. Slot names, nonmetal regions, optics and geometry stay.
for path in targets:
 if path.split('.')[0] in [cap['Body']['asset'],cap['RearSight']['asset']]:continue
 a=load(path);skeletal=isinstance(a,u.SkeletalMesh);prop='materials' if skeletal else 'static_materials';slots=[s.copy() for s in a.get_editor_property(prop)];changed=False
 for i,s in enumerate(slots):
  if s.material_interface and s.material_interface.get_path_name() in mapping:s.material_interface=mapped(s.material_interface);slots[i]=s;changed=True
 if changed:
  backup(path);a.set_editor_property(prop,slots);save(a);receipt['saved'][path.split('.')[0]]={'sha256':sha(path),'change':'material bindings only'};record()
backup(wetpath);wet=load(wetpath);wetmap=dict(wet.get_editor_property('wet_materials'))
for original,replacement in mapping.items():
 wetmap[replacement]=load(replacement);wetmap[original]=load(replacement)
wet.set_editor_property('wet_materials',wetmap);save(wet);receipt['saved'][wetpath]={'sha256':sha(wetpath)}
bindings={}
for path in targets:
 a=load(path);slots=a.materials if isinstance(a,u.SkeletalMesh) else a.static_materials;bindings[a.get_path_name()]={str(s.material_slot_name):s.material_interface.get_path_name() if s.material_interface else None for s in slots}
for key in ['Body','RearSight']:export(load(cap[key]['asset']),key)
manifest=S/'Material21/bindings.json';data=json.loads(manifest.read_text());data['meshes'].update(bindings);data['current_geometry_revision']='SightFinish41';manifest.write_text(json.dumps(data,indent=2));(O/'bindings.json').write_text(json.dumps(bindings,indent=2))
receipt.update(status='current_s41_saved',material_count=len(mapping),game_tested=False);record();print('S41_CURRENT_SAVED',len(receipt['saved']),len(mapping),flush=True)
