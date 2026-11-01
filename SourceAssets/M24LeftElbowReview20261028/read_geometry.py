import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent
path='/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9';mesh=u.load_asset(path)
Q=u.GeometryScript_MeshQueries;G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Mesh read')
def xyz(v):return [v.x,v.y,v.z]
_,ps,_=Q.get_all_vertex_positions(dm,False);ps=list(u.GeometryScript_List.convert_vector_list_to_array(ps))
_,ts,_=Q.get_all_triangle_indices(dm,False);ts=list(u.GeometryScript_List.convert_triangle_list_to_array(ts))
_,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
skin={i for i,s in enumerate(mesh.materials) if str(s.material_slot_name).startswith('MI_Manny')}
faces=[]
for i in range(len(ts)):
 mat,ok=u.GeometryScript_Materials.get_triangle_material_id(dm,i)
 if ok and mat in skin:
  a,b,c,_=Q.get_triangle_u_vs(dm,0,i);faces.append({'id':i,'vertices':[int(x) for x in xyz(ts[i])],'uv':[[v.x,v.y] for v in (a,b,c)],'material':mat})
ids=sorted({v for f in faces for v in f['vertices']});weights={}
for i in ids:
 _,ws,ok=B.get_vertex_bone_weights(dm,i);weights[i]={names[w.bone_index]:w.weight for w in ws if w.weight>0} if ok else {}
file=Path(u.Paths.project_content_dir())/(path.removeprefix('/Game/')+'.uasset')
(O/'geometry.json').write_text(json.dumps({'path':path,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'positions':{i:xyz(ps[i]) for i in ids},'faces':faces,'weights':weights}))
print('M24_GEOMETRY_READ',len(ids),len(faces),flush=True)
