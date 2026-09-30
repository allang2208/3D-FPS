"""Background import and scoped save of S42 art. No gameplay/preview launch."""
from pathlib import Path
O=Path(__file__).parent
old=(O.parent/'Assembly40/install.py').read_text()
prefix=old.split('if u.get_editor_subsystem')[0].replace('Assembly40','SurfaceReform42').replace('A40','S42')
exec(compile(prefix,str(O/'install.py'),'exec'),globals())
sub=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if sub and sub.get_game_world():raise RuntimeError('PIE active; targets retained')
keys=['Body','BipodBase','BipodLegA','BipodLegB']
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for key in keys:
 path=cap[key]['asset'];expected=receipt['saved'].get(path,{}).get('sha256',cap[key]['sha256'])
 if path in dirty or sha(path)!=expected:raise RuntimeError('Concurrent target retained '+path)

def backup(path):
 if path not in receipt['backups']:
  dest=O/'Before'/file(path).relative_to(PROJECT/'Content');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file(path),dest);receipt['backups'][path]={'bytes':str(dest),'sha256':sha(path)};record()

current=load(cap['Body']['asset']);lookup={str(s.material_slot_name):s.material_interface for s in current.materials}
cover=lookup['M_LMG201_S41_Cover'];satin=lookup['M_LMG201_Trigger'];inside=lookup['M_LMG201_A40_Interior']
lookup.update({'M_LMG201_S42_Cover':cover,'M_LMG201_S42_Satin':satin,'M_LMG201_S42_Interior':inside,'M_LMG201_Trigger_S42':satin,'M_LMG201_H39_Interior':load('/Game/Weapons/LMG201/HardSurface39/Materials/M_LMG201_H39_Interior')})
for key in keys[1:]:
 for s in load(cap[key]['asset']).static_materials:
  if s.material_interface:lookup[s.material_interface.get_name()]=s.material_interface
lookup['M_LMG201_Inside.001']=lookup['M_LMG201_Inside_001']=load('/Game/Weapons/LMG201/Refinement01/Materials/M_LMG201_Inside')
exec(compile(old[old.index('def imported('):old.index("path=cap['Body']['asset'];source_sha")],str(O/'install.py'),'exec'),globals())

path=cap['Body']['asset'];source_sha=hashlib.sha256(Path(model['body_fbx']).read_bytes()).hexdigest()
if receipt['saved'].get(path,{}).get('source_sha256')!=source_sha:
 source,partslots,digest=imported('SK_LMG201_S42_Parts',model['body_fbx'],True)
 for i,s in enumerate(partslots):
  if str(s.material_slot_name)=='M_LMG201_Trigger_S42':s.material_slot_name=u.Name('M_LMG201_Trigger');partslots[i]=s
 native=dynamic(current);added=dynamic(source);slots=[s.copy() for s in current.materials]
 replaced={'M_LMG201_H39_Cover','M_LMG201_H39_Interior','M_LMG201_H39_Receiver','M_LMG201_F37_Interior','M_LMG201_Magazine','M_LMG201_Trigger','M_LMG201_A40_Cover','M_LMG201_A40_Interior','M_LMG201_A40_Satin','M_LMG201_S41_Cover','M_LMG201_S41_Satin','M_LMG201_S42_Cover','M_LMG201_S42_Interior','M_LMG201_S42_Satin'}
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
  else:
   target=slots[names[key]];target.material_interface=s.material_interface;slots[names[key]]=target
 for i,s in enumerate(partslots):M.remap_material_i_ds(added,i,1000+i)
 for i,s in enumerate(partslots):M.remap_material_i_ds(added,1000+i,names[str(s.material_slot_name)])
 Ed.append_mesh(native,added,u.Transform(),True)
 candidate=u.load_asset(P+'/SK_LMG201_S42_Installed') or E.duplicate_asset(path,P+'/SK_LMG201_S42_Installed');copy_to(native,candidate,slots);save(candidate)
 backup(path);copy_to(native,current,slots);current.get_editor_property('asset_import_data').scripted_add_filename(str(O/'Exports/After_Body.fbx'),0,'SurfaceReform42 saved body')
 E.set_metadata_tag(current,'201Revision','SurfaceReform42: clean asymmetric receiver skins, reference swept guard and smooth trigger blade');E.set_metadata_tag(current,'201DetailSource',str(O/'LMG201_SurfaceReform42.blend'));save(current)
 receipt['saved'][path]={'sha256':sha(path),'source_sha256':digest,'removed_by_slot':counts};record()

for key in keys[1:]:
 path=cap[key]['asset'];filename=model['static_fbx'][key];source_sha=hashlib.sha256(Path(filename).read_bytes()).hexdigest()
 if receipt['saved'].get(path,{}).get('source_sha256')==source_sha:continue
 source,partslots,digest=imported('SM_LMG201_S42_'+key,filename,False)
 sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem);settings=sub.get_lod_build_settings(source,0);settings.set_editor_property('remove_degenerates',False);sub.set_lod_build_settings(source,0,settings);save(source)
 dm=dynamic(source);a=load(path);slots=[s.copy() for s in a.static_materials];dest=[]
 for s in partslots:
  match=next((i for i,t in enumerate(slots) if t.material_interface==s.material_interface),None)
  if match is None:match=len(slots);slots.append(s.copy())
  dest.append(match)
 for i in range(len(partslots)):M.remap_material_i_ds(dm,i,1000+i)
 for i,index in enumerate(dest):M.remap_material_i_ds(dm,1000+i,index)
 candidatepath=P+'/SM_LMG201_S42_'+key+'_Installed';candidate=u.load_asset(candidatepath) or E.duplicate_asset(path,candidatepath);copy_to(dm,candidate,slots);save(candidate)
 backup(path);copy_to(dm,a,slots);settings=sub.get_lod_build_settings(a,0);settings.set_editor_property('remove_degenerates',False);sub.set_lod_build_settings(a,0,settings)
 a.get_editor_property('asset_import_data').scripted_add_filename(str(O/'Exports'/('After_'+key+'.fbx')),0,'SurfaceReform42 native pivot; refined mount and upper collars');E.set_metadata_tag(a,'201Revision','SurfaceReform42');E.set_metadata_tag(a,'201DetailSource',str(O/'LMG201_SurfaceReform42.blend'));save(a)
 receipt['saved'][path]={'sha256':sha(path),'source_sha256':digest,'pivot_changed':False};record()

bindings={}
for key in keys:
 a=load(cap[key]['asset']);slots=a.materials if key=='Body' else a.static_materials;bindings[a.get_path_name()]={str(s.material_slot_name):s.material_interface.get_path_name() if s.material_interface else None for s in slots};export(a,key)
manifest=S/'Material21/bindings.json';data=json.loads(manifest.read_text());data['meshes'].update(bindings);data['current_geometry_revision']='SurfaceReform42';manifest.write_text(json.dumps(data,indent=2));(O/'bindings.json').write_text(json.dumps(bindings,indent=2))
(O/'materials.json').write_text(json.dumps({'new_surfaces':{'coat':cover.get_path_name(),'satin':satin.get_path_name(),'interior':inside.get_path_name()},'new_material_packages':0,'old_atlas_normals_on_new_surfaces':False},indent=2))
receipt.update(status='current_s42_saved',runtime_tested=False,rendered=False,wet_table_modified=False);record();print('S42_CURRENT_SAVED',len(receipt['saved']),flush=True)
