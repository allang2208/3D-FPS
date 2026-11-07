from pathlib import Path
import unreal as u,json,gzip
O=Path(__file__).resolve().parent
meta=json.loads((O/'Inputs/current.json').read_text())
Q,G,L=u.GeometryScript_MeshQueries,u.GeometryScript_AssetUtils,u.GeometryScript_List
def xyz(v):return [v.x,v.y,v.z]
def copy(a,static,lod=0):
    fn=G.copy_mesh_from_static_mesh if static else G.copy_mesh_from_skeletal_mesh
    dm,status=fn(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False,use_build_scale=False),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL,lod_index=lod))
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('read '+a.get_name())
    return dm
def arrays(dm):
    _,ps,_=Q.get_all_vertex_positions(dm,False);_,fs,_=Q.get_all_triangle_indices(dm,False)
    _,ms,_=u.GeometryScript_Materials.get_all_triangle_material_i_ds(dm)
    return [xyz(v) for v in L.convert_vector_list_to_array(ps)],[xyz(v) for v in L.convert_triangle_list_to_array(fs)],list(L.convert_index_list_to_array(ms))
action=u.load_asset(meta['action']['path'])
r=[]
for li in range(action.get_num_lods()):
    r.append(arrays(copy(action,True,li)))
with gzip.open(O/'Inputs/action-triangles.json.gz','wt') as f:json.dump(r,f,separators=(',',':'))
host=u.load_asset(meta['host']['path']); dm=copy(host,False);ps,faces,ms=arrays(dm)
slot=next(i for i,s in enumerate(host.materials) if str(s.material_slot_name)=='M24_FactoryRearSeat')
rows=[]
for i,m in enumerate(ms):
    if m!=slot:continue
    _,a,b,c,ok=Q.get_triangle_normals(dm,i); uv=[]
    for ch in range(Q.get_num_uv_sets(dm)):
        p,q,s,valid=Q.get_triangle_u_vs(dm,ch,i);uv.append([[v.x,v.y] for v in (p,q,s)])
    rows.append(dict(pos=[ps[j] for j in faces[i]],norm=[xyz(v) for v in (a,b,c)],uv=uv))
(O/'Inputs/factory-seat.json').write_text(json.dumps(rows,separators=(',',':')))
print('M24_SEAT',len(rows),[len(a[1]) for a in r])
