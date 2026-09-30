"""Replace only old/new cloth-feed belt sections with rigid authored metal parts."""
import unreal as u,json,gzip,hashlib,shutil,collections
from pathlib import Path
O=Path(__file__).parent;PROJECT=O.parents[2]
BODY='/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10'
CANDIDATE='/Game/Weapons/LMG201/BeltRebuild52/SK_LMG201_BeltRebuild52_Candidate'
source=json.loads((O/'source.json').read_text())
E=u.EditorAssetLibrary;G=u.GeometryScript_AssetUtils;Ed=u.GeometryScript_MeshEdits;B=u.GeometryScript_BoneWeights;Q=u.GeometryScript_MeshQueries;IL=u.GeometryScript_List;M=u.GeometryScript_Materials
def file(p):return PROJECT/'Content'/(p.removeprefix('/Game/')+'.uasset')
def sha(p):return hashlib.sha256(file(p).read_bytes()).hexdigest()
def load(p):
 a=u.load_asset(p)
 if not a:raise RuntimeError('Missing '+p)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
def dynamic(a):
 dm,status=G.copy_mesh_from_skeletal_mesh(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Mesh read failed')
 return dm
def isbelt(name):return name.startswith(('M_LMG201_Cloth33__OldBelt','M_LMG201_Cloth33__NewBelt'))
def preflight():
 if sha(BODY)!=source['sha256']:raise RuntimeError('Concurrent body retained; refresh snapshot')
 if BODY in {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:raise RuntimeError('Unsaved body retained')
 sub=u.get_editor_subsystem(u.UnrealEditorSubsystem)
 if sub and sub.get_game_world():raise RuntimeError('PIE retained; no asset write')
def copyto(dm,a,slots):
 opt=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[s.material_interface for s in slots],new_material_slot_names=[s.material_slot_name for s in slots],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
 _,status=G.copy_mesh_to_skeletal_mesh(dm,a,opt,u.GeometryScriptMeshWriteLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Mesh write failed')
 a.materials=[s.copy() for s in slots]
def check(a):
 dm=dynamic(a);_,bl=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bl}
 _,tl,_=Q.get_all_triangle_indices(dm,False);triangles=IL.convert_triangle_list_to_array(tl);counts=collections.Counter();selected=set()
 for ti,t in enumerate(triangles):
  m,valid=M.get_triangle_material_id(dm,ti)
  if not valid:continue
  n=str(a.materials[m].material_slot_name);counts[n]+=1
  if isbelt(n):
   if '_B52_' not in n:raise RuntimeError('Retired belt still has geometry')
   selected.update([t.x,t.y,t.z])
 cells=collections.Counter();lo=[float('inf')]*3;hi=[-float('inf')]*3
 for vi in selected:
  p,valid=Q.get_vertex_position(dm,vi);_,ws,valid=B.get_vertex_bone_weights(dm,vi)
  active=[w for w in ws if w.weight>0]
  if not valid or len(active)!=1 or abs(active[0].weight-1)>1e-4:raise RuntimeError('Non-rigid cartridge vertex')
  cells[names[active[0].bone_index]]+=1
  for axis,value in enumerate(p.to_tuple()):lo[axis]=min(lo[axis],value);hi[axis]=max(hi[axis],value)
 expected={'LMG201_Belt_%02d'%i for i in range(9)}|{'New_LMG201_Belt_%02d'%i for i in range(9) if i!=6}
 if set(cells)!=expected:raise RuntimeError('Missing/new unintended cell binding')
 if max(hi[i]-lo[i] for i in range(3))>30:raise RuntimeError('Belt unit conversion mismatch')
 for n,count in source['triangles_by_slot'].items():
  if not isbelt(n) and counts[n]!=count:raise RuntimeError('Unrelated geometry changed '+n)
 return {'triangles_by_belt_slot':{n:c for n,c in counts.items() if isbelt(n)},'rigid_cells':dict(cells),'bounds_cm':[lo,hi]}
def prepare():
 preflight()
 exec(compile((O/'materials.py').read_text(),str(O/'materials.py'),'exec'),{'__file__':str(O/'materials.py'),'__name__':'__main__'})
 materials=json.loads((O/'materials.json').read_text());body=load(BODY);native=dynamic(body);slots=[s.copy() for s in body.materials]
 _,tl,_=Q.get_all_triangle_indices(native,False);tris=IL.convert_triangle_list_to_array(tl);remove=[]
 for ti in range(len(tris)):
  mid,valid=M.get_triangle_material_id(native,ti)
  if valid and isbelt(str(slots[mid].material_slot_name)):remove.append(ti)
 if not remove:raise RuntimeError('Old/new belts missing')
 Ed.delete_triangles_from_mesh(native,IL.convert_array_to_index_list(remove,u.GeometryScriptIndexType.TRIANGLE),True)
 _,bones=B.get_all_bones_info(native);bi={str(b.name):b.index for b in bones}
 names={str(s.material_slot_name):i for i,s in enumerate(slots)}
 with gzip.open(O/'mesh_buffers.json.gz','rt') as f:parts=json.load(f)
 for row in parts:
  name=row['slot']
  if name not in names:
   s=u.SkeletalMaterial();s.material_slot_name=name;s.material_interface=load(materials[row['role']]);names[name]=len(slots);slots.append(s)
  added=u.DynamicMesh()
  buf=u.GeometryScriptSimpleMeshBuffers(vertices=[u.Vector(*v) for v in row['p']],normals=[u.Vector(*v) for v in row['n']],uv0=[u.Vector2D(*v) for v in row['uv']],triangles=[u.IntVector(*v) for v in row['t']],vertex_colors=[u.LinearColor(*row['color']) for _ in row['p']])
  Ed.append_buffers_to_mesh(added,buf,names[name],True)
  B.copy_bones_from_mesh(native,added,u.GeometryScriptCopyBonesFromMeshOptions(reindex_weights=False))
  B.mesh_create_bone_weights(added)
  B.set_all_vertex_bone_weights(added,[u.GeometryScriptBoneWeight(bone_index=bi[row['bone']],weight=1.)])
  Ed.append_mesh(native,added,u.Transform(),True)
 candidate=u.load_asset(CANDIDATE) or E.duplicate_asset(BODY,CANDIDATE)
 copyto(native,candidate,slots);proof=check(candidate)
 E.set_metadata_tag(candidate,'201BeltRebuildRevision','BeltRebuild52: rigid case/projectile/link; two receiver cells; no cloth atlas')
 save(candidate)
 receipt={'status':'candidate_saved','source_sha256':source['sha256'],'candidate':CANDIDATE,'candidate_sha256':sha(CANDIDATE),'candidate_geometry':proof,'removed_belt_triangles':len(remove),'runtime_tested':False,'animations_modified':False,'native_code_modified':True,'source_model':str(O/'LMG201_BeltRebuild52.blend')}
 (O/'delivery.json').write_text(json.dumps(receipt,indent=2));print('BELT52_CANDIDATE_SAVED',proof,flush=True)
def publish():
 preflight();receipt=json.loads((O/'delivery.json').read_text())
 if sha(CANDIDATE)!=receipt['candidate_sha256']:raise RuntimeError('Candidate changed')
 candidate=load(CANDIDATE);body=load(BODY);proof=check(candidate)
 backup=O/'Before'/file(BODY).relative_to(PROJECT/'Content');backup.parent.mkdir(parents=True,exist_ok=True)
 if backup.exists():raise RuntimeError('Existing backup retained')
 shutil.copy2(file(BODY),backup)
 copyto(dynamic(candidate),body,[s.copy() for s in candidate.materials])
 E.set_metadata_tag(body,'201BeltRebuildRevision','BeltRebuild52: regular metal cartridges and links, receiver run, nine-cell feed pool')
 E.set_metadata_tag(body,'201BeltMotionSource',str(O/'LMG201_BeltRebuild52.blend'))
 save(body)
 receipt.update(status='current_body_saved',saved={BODY:{'sha256':sha(BODY)}},backup=str(backup),independent_candidate_read=proof)
 (O/'delivery.json').write_text(json.dumps(receipt,indent=2))
 bindings={str(s.material_slot_name):s.material_interface.get_path_name() if s.material_interface else None for s in body.materials}
 (O/'bindings.json').write_text(json.dumps({body.get_path_name():bindings},indent=2))
 manifest=O.parent/'Material21/bindings.json';data=json.loads(manifest.read_text());data['meshes'][body.get_path_name()]=bindings;data['current_belt_motion_revision']='BeltRebuild52';manifest.write_text(json.dumps(data,indent=2))
 print('BELT52_CURRENT_SAVED',receipt['saved'],flush=True)
