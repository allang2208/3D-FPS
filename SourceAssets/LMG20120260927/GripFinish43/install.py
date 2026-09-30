"""Scoped G43 geometry, material and right-arm authoring save; no game launch."""
from pathlib import Path
O=Path(__file__).parent
old=(O.parent/'Assembly40/install.py').read_text()
exec(compile(old.split('if u.get_editor_subsystem')[0].replace('Assembly40','GripFinish43').replace('A40','G43'),str(O/'install.py'),'exec'),globals())
import re
mat=json.loads((O/'materials.json').read_text());motion=json.loads((O/'animations.json').read_text())
BODY='/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10'
GRIPS={k:'/Game/Weapons/LMG201/Accessories22/Meshes/SM_LMG201_'+n for k,n in [('stable','stable_antislip_reargrip'),('balanced','balanced_reargrip'),('phantom','phantom_reargrip')]}
sub=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if sub and sub.get_game_world():raise RuntimeError('PIE active; existing assets retained')
if mat['status']!='compiled_and_saved':raise RuntimeError('Finish assets not ready')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
expected={p:r['sha256'] for p,r in cap['meshes'].items()}
expected[cap['wet']['asset']]=cap['wet']['sha256']
expected.update({p:r['sha256_before'] for p,r in motion['clips'].items()})
for p,h in expected.items():
 if p.split('.')[0] in dirty or sha(p)!=receipt['saved'].get(p,{}).get('sha256',h):raise RuntimeError('Concurrent target retained '+p)

def backup(p):
 if p not in receipt['backups']:
  dest=O/'Before'/file(p).relative_to(PROJECT/'Content');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file(p),dest);receipt['backups'][p]={'bytes':str(dest),'sha256':sha(p)};record()

current=load(BODY);lookup={str(s.material_slot_name):s.material_interface for s in current.materials}
lookup.update({'M_LMG201_S42_Cover':lookup['M_LMG201_S41_Cover'],'M_LMG201_S42_Satin':lookup['M_LMG201_Trigger'],'M_LMG201_S42_Interior':lookup['M_LMG201_A40_Interior'],'M_LMG201_Trigger_S42':lookup['M_LMG201_Trigger'],'M_LMG201_H39_Interior':load('/Game/Weapons/LMG201/HardSurface39/Materials/M_LMG201_H39_Interior')})
lookup.update({k:load(v) for k,v in mat['bindings'][BODY].items()});lookup.update({k:load(v) for k,v in mat['new_slots'].items()})
lookup['M_LMG201_Trigger_S42']=lookup['M_LMG201_Trigger']
for p in GRIPS.values():
 for s in cap['meshes'][p]['slots']:
  if s['material']:
   name=s['material'].rsplit('.',1)[-1];a=load(mat['bindings'][p].get(s['slot'],s['material']))
   for suffix in ['', '.001','.002','.003','_001','_002','_003']:lookup[name+suffix]=a
lookup['M_LMG201_Inside.001']=lookup['M_LMG201_Inside_001']=load('/Game/Weapons/LMG201/Refinement01/Materials/M_LMG201_Inside')
exec(compile(old[old.index('def imported('):old.index("path=cap['Body']['asset'];source_sha")],str(O/'install.py'),'exec'),globals())

source_sha=hashlib.sha256(Path(model['body_fbx']).read_bytes()).hexdigest()
if receipt['saved'].get(BODY,{}).get('source_sha256')!=source_sha:
 source,partslots,digest=imported('SK_LMG201_G43_Parts',model['body_fbx'],True)
 rename={'M_LMG201_Trigger_S42':'M_LMG201_Trigger','M_LMG201_G43_FactoryGrip':'M_LMG201_FactoryRearGrip_G43','M_LMG201_G43_GripPolymer':'M_LMG201_FactoryRearGrip_G43_Seat'}
 for i,s in enumerate(partslots):
  s.material_slot_name=u.Name(rename.get(str(s.material_slot_name),str(s.material_slot_name)));partslots[i]=s
 native=dynamic(current);added=dynamic(source);slots=[s.copy() for s in current.materials]
 replaced={'M_LMG201_H39_Cover','M_LMG201_H39_Interior','M_LMG201_H39_Receiver','M_LMG201_F37_Interior','M_LMG201_Magazine','M_LMG201_Trigger','M_LMG201_A40_Cover','M_LMG201_A40_Interior','M_LMG201_A40_Satin','M_LMG201_S41_Cover','M_LMG201_S41_Satin','M_LMG201_S42_Cover','M_LMG201_S42_Interior','M_LMG201_S42_Satin','M_LMG201_R38_Cover','M_LMG201_R38_Interior','M_LMG201_R38_Satin','M_LMG201_FactoryRearGrip','M_LMG201_FactoryRearGrip_R30_Surface','M_LMG201_FactoryRearGrip_R30_Interior'}
 _,tl,_=Q.get_all_triangle_indices(native,False);triangles=L.convert_triangle_list_to_array(tl);remove=[];counts={}
 for ti in range(len(triangles)):
  mid,valid=M.get_triangle_material_id(native,ti)
  if valid and str(slots[mid].material_slot_name) in replaced:
   remove.append(ti);name=str(slots[mid].material_slot_name);counts[name]=counts.get(name,0)+1
 for name in ['M_LMG201_H39_Receiver','M_LMG201_Magazine','M_LMG201_Trigger','M_LMG201_R38_Cover','M_LMG201_FactoryRearGrip_R30_Surface']:
  if not counts.get(name):raise RuntimeError('Missing replacement section '+name)
 Ed.delete_triangles_from_mesh(native,L.convert_array_to_index_list(remove,u.GeometryScriptIndexType.TRIANGLE),True)
 B.copy_bones_from_mesh(native,added,u.GeometryScriptCopyBonesFromMeshOptions(reindex_weights=True))
 names={str(s.material_slot_name):i for i,s in enumerate(slots)}
 for s in partslots:
  name=str(s.material_slot_name)
  if name not in names:names[name]=len(slots);slots.append(s.copy())
  else:
   t=slots[names[name]];t.material_interface=s.material_interface;slots[names[name]]=t
 for i in range(len(partslots)):M.remap_material_i_ds(added,i,1000+i)
 for i,s in enumerate(partslots):M.remap_material_i_ds(added,1000+i,names[str(s.material_slot_name)])
 Ed.append_mesh(native,added,u.Transform(),True)
 for i,s in enumerate(slots):
  target=mat['bindings'][BODY].get(str(s.material_slot_name))
  if target:s.material_interface=load(target);slots[i]=s
 candidate=u.load_asset(P+'/SK_LMG201_G43_Installed') or E.duplicate_asset(BODY,P+'/SK_LMG201_G43_Installed');copy_to(native,candidate,slots);save(candidate)
 backup(BODY);copy_to(native,current,slots)
 current.get_editor_property('asset_import_data').scripted_add_filename(str(O/'Exports/After_Body.fbx'),0,'GripFinish43 saved assembly')
 E.set_metadata_tag(current,'201Revision','GripFinish43: connected rear seat, polymer identity, clean receiver finish');E.set_metadata_tag(current,'201DetailSource',str(O/'LMG201_GripFinish43.blend'));save(current)
 receipt['saved'][BODY]={'sha256':sha(BODY),'source_sha256':digest,'removed_by_slot':counts,'finish':True};record()

sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
for key,p in GRIPS.items():
 filename=model['grip_fbx'][key];digest=hashlib.sha256(Path(filename).read_bytes()).hexdigest()
 if receipt['saved'].get(p,{}).get('source_sha256')==digest:continue
 source,partslots,digest=imported('SM_LMG201_G43_'+key,filename,False);settings=sm.get_lod_build_settings(source,0);settings.remove_degenerates=False;sm.set_lod_build_settings(source,0,settings);save(source)
 a=load(p);dm=dynamic(source);slots=[s.copy() for s in a.static_materials];dest=[]
 donorname=cap['meshes'][p]['slots'][1]['slot']
 for s in partslots:
  name='LMG20122_Interface' if str(s.material_slot_name)=='M_LMG201_G43_GripPolymer' else donorname
  i=next(i for i,t in enumerate(slots) if str(t.material_slot_name)==name);t=slots[i];t.material_interface=s.material_interface;slots[i]=t;dest.append(i)
 for i in range(len(partslots)):M.remap_material_i_ds(dm,i,1000+i)
 for i,j in enumerate(dest):M.remap_material_i_ds(dm,1000+i,j)
 backup(p);copy_to(dm,a,slots);settings=sm.get_lod_build_settings(a,0);settings.remove_degenerates=False;sm.set_lod_build_settings(a,0,settings)
 a.get_editor_property('asset_import_data').scripted_add_filename(str(O/'Exports'/('After_'+key+'.fbx')),0,'GripFinish43 seated and fitted grip; native pivot');E.set_metadata_tag(a,'201Revision','GripFinish43');save(a)
 receipt['saved'][p]={'sha256':sha(p),'source_sha256':digest,'finish':True,'pivot_changed':False};record()

for p,binds in mat['bindings'].items():
 if not binds or receipt['saved'].get(p,{}).get('finish'):continue
 a=load(p);prop='materials' if isinstance(a,u.SkeletalMesh) else 'static_materials';slots=[s.copy() for s in a.get_editor_property(prop)]
 for i,s in enumerate(slots):
  target=binds.get(str(s.material_slot_name))
  if target:s.material_interface=load(target);slots[i]=s
 backup(p);a.set_editor_property(prop,slots);E.set_metadata_tag(a,'201FinishRevision','GripFinish43');save(a)
 receipt['saved'][p]={'sha256':sha(p),'finish':True};record()

p=cap['wet']['asset']
if not receipt['saved'].get(p,{}).get('finish'):
 a=load(p);mapping=dict(a.get_editor_property('wet_materials'))
 for row in mat['jobs'].values():mapping[row['asset']]=load(row['asset'])
 backup(p);a.set_editor_property('wet_materials',mapping);save(a);receipt['saved'][p]={'sha256':sha(p),'finish':True};record()

for p,spec in motion['clips'].items():
 keysha=hashlib.sha256(Path(spec['file']).read_bytes()).hexdigest()
 if receipt['saved'].get(p,{}).get('keys_sha256')==keysha:continue
 clip=load(p);backup(p);tracks=json.loads(Path(spec['file']).read_text());controller=clip.get_editor_property('controller');data=clip.get_editor_property('data_model_interface');controller.open_bracket('201 G43 measured rear grip contact',False)
 try:
  for n,rows in tracks.items():
   if not data.is_valid_bone_track_name(n):controller.add_bone_curve(n,False)
   if not controller.set_bone_track_keys(n,[u.Vector(*v[:3]) for v in rows],[u.Quat(*v[3:7]) for v in rows],[u.Vector(*v[7:10]) for v in rows],False):raise RuntimeError('Cannot write '+n)
 finally:controller.close_bracket(False)
 E.set_metadata_tag(clip,'201RearGripRevision','GripFinish43: root-space contact IK; released poses retained; rotation tracks only');u.AKMAnimationAuditLibrary.finish_animation_compression(clip);save(clip)
 receipt['saved'][p]={'sha256':sha(p),'keys_sha256':keysha,'frames':spec['frames'],'contact_frames':spec['contact_frames']};record();print('G43_ANIMATION_SAVED',p,flush=True)

bindings={}
for p in cap['meshes']:
 a=load(p);slots=a.materials if isinstance(a,u.SkeletalMesh) else a.static_materials;bindings[a.get_path_name()]={str(s.material_slot_name):s.material_interface.get_path_name() if s.material_interface else None for s in slots}
export(current,'Body')
for k,p in GRIPS.items():export(load(p),k)
manifest=S/'Material21/bindings.json';data=json.loads(manifest.read_text());data['meshes'].update(bindings);data['current_geometry_revision']='GripFinish43';data['current_material_revision']='GripFinish43';manifest.write_text(json.dumps(data,indent=2));(O/'bindings.json').write_text(json.dumps(bindings,indent=2))
receipt.update(status='current_g43_saved',animations_modified=True,native_code_modified=True,runtime_tested=False,rendered=False);record();print('G43_CURRENT_SAVED',len(receipt['saved']),flush=True)
