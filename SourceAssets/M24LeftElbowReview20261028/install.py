"""Add only M24 elbow morphs; preserve mesh basis, weights, material IDs, and all animation/profile assets."""
import unreal as u,json,hashlib,shutil,math
from pathlib import Path
O=Path(__file__).resolve().parent;spec=json.loads((O/'morph_payload.json').read_text());path=spec['path']
E=u.EditorAssetLibrary;G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;Ed=u.GeometryScript_MeshEdits
file=Path(u.Paths.project_content_dir())/(path.removeprefix('/Game/')+'.uasset')
if hashlib.sha256(file.read_bytes()).hexdigest()!=spec['sha256']:raise RuntimeError('M24 mesh changed; preserve concurrent work')
if any(p.get_name()==path for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('M24 mesh has unsaved changes')
mesh=u.load_asset(path);backup=O/'Backups';backup.mkdir(exist_ok=True);shutil.copy2(file,backup/file.name)
def read():
 dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Mesh read failed')
 return dm
def xyz(v):return [v.x,v.y,v.z]
def unit(a):
 size=math.sqrt(sum(x*x for x in a));return [x/max(size,1e-12) for x in a]
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def transport(n,a,b):
 v=cross(a,b);c=sum(x*y for x,y in zip(a,b));v1=cross(v,n);v2=cross(v,v1);return unit([n[i]+v1[i]+v2[i]/max(1+c,1e-6) for i in range(3)])
dm=read();_,ps,_=Q.get_all_vertex_positions(dm,False);ps=list(u.GeometryScript_List.convert_vector_list_to_array(ps));basis=[xyz(x) for x in ps]
_,ts,_=Q.get_all_triangle_indices(dm,False);ts=list(u.GeometryScript_List.convert_triangle_list_to_array(ts));materials=[];normals={}
for ti,t in enumerate(ts):
 materials.append(u.GeometryScript_Materials.get_triangle_material_id(dm,ti)[0]);_,a,b,c,ok=Q.get_triangle_normals(dm,ti)
 if ok:
  for v,n in zip(xyz(t),(a,b,c)):
   v=int(v);old=normals.setdefault(v,[0.,0.,0.]);x=xyz(n)
   for k in range(3):old[k]+=x[k]
normals={v:unit(n) for v,n in normals.items()}
slots=[(str(s.material_slot_name),s.material_interface.get_path_name() if s.material_interface else None) for s in mesh.materials]
ss=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);settings=ss.get_lod_build_settings(mesh,0);old_threshold=settings.get_editor_property('morph_threshold_position')
settings.set_editor_property('morph_threshold_position',min(old_threshold,spec['morph_threshold_position_cm']));ss.set_lod_build_settings(mesh,0,settings)
names=list(spec['morphs'])
for i,name in enumerate(names):
 md=read()
 for row in spec['morphs'][name]:
  v=int(row[0]);p=[basis[v][k]+row[1+k] for k in range(3)];n=transport(normals[v],row[4:7],row[7:10])
  Ed.set_vertex_position(md,v,u.Vector(*p),True)
  u.GeometryScript_Normals.update_vertex_normal(md,v,True,u.Vector(*n),False,u.Vector(1,0,0),u.Vector(0,1,0),False,True)
 options=u.GeometryScriptCopyMorphTargetToAssetOptions(overwrite_existing_target=False,emit_transaction=False,defer_mesh_post_edit_change=i<len(names)-1,copy_normals=True)
 _,outcome=G.copy_morph_target_to_skeletal_mesh(md,mesh,name,options,u.GeometryScriptMeshWriteLOD())
 if outcome!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Morph write failed '+name)
 print('M24_ELBOW_MORPH',i+1,name,flush=True)
if not E.save_loaded_asset(mesh,False):raise RuntimeError('M24 mesh save failed')
on_asset=[m.get_name() for m in mesh.get_editor_property('morph_targets')]
if any(n not in on_asset for n in names):raise RuntimeError('Saved morph missing')
rb=read();_,points,_=Q.get_all_vertex_positions(rb,False);points=list(u.GeometryScript_List.convert_vector_list_to_array(points));error=max(abs(xyz(p)[k]-basis[i][k]) for i,p in enumerate(points) for k in range(3))
if error>1e-6:raise RuntimeError('Unexpected basis change')
if slots!=[(str(s.material_slot_name),s.material_interface.get_path_name() if s.material_interface else None) for s in mesh.materials]:raise RuntimeError('Unexpected material slots change')
if materials!=[u.GeometryScript_Materials.get_triangle_material_id(rb,i)[0] for i in range(len(ts))]:raise RuntimeError('Unexpected triangle material change')
(O/'install_receipt.json').write_text(json.dumps({'saved':True,'path':path,'added_morphs':names,'morph_count':len(on_asset),'basis_error_cm':error,'material_slots_and_triangle_ids_unchanged':True,'previous_morph_threshold_cm':old_threshold,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'runtime_game_tested':False},indent=2))
print('M24_ELBOW_MORPHS_SAVED',len(names),flush=True)
