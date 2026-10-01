"""Read the current A762 body and three grips; no asset writes."""
import array, hashlib, json
from pathlib import Path
import unreal as u
O=Path(__file__).parent;OUT=O/'Input';OUT.mkdir(parents=True,exist_ok=True)
P=Path(u.Paths.project_dir()).resolve()
if P!=Path('D:/FPS3D/FPSGAME').resolve():raise RuntimeError('Wrong project')
MESHES={'Body':'/Game/Weapons/A762/Integrated20260920/SK_A762_Manny'}
for k in ['phantom_reargrip','balanced_reargrip','stable_antislip_reargrip']:
    MESHES[k]='/Game/Weapons/A762/Accessories05/Meshes/SM_A762_'+k
G,Q,L,M,B=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_List,u.GeometryScript_Materials,u.GeometryScript_BoneWeights
def pick(result,cls):
    return next(x for x in result if isinstance(x,cls)) if isinstance(result,tuple) else result
meta={}
for key,path in MESHES.items():
    mesh=u.load_asset(path);dm=u.DynamicMesh()
    lod=u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL,lod_index=0)
    fn=G.copy_mesh_from_skeletal_mesh if key=='Body' else G.copy_mesh_from_static_mesh
    _,outcome=fn(mesh,dm,u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False),lod)
    if outcome!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Read failed '+path)
    if Q.get_has_vertex_id_gaps(dm) or Q.get_has_triangle_id_gaps(dm):raise RuntimeError('ID gaps '+key)
    slots=mesh.materials if key=='Body' else mesh.static_materials
    positions=L.convert_vector_list_to_array(pick(Q.get_all_vertex_positions(dm,True),u.GeometryScriptVectorList))
    triangles=L.convert_triangle_list_to_array(pick(Q.get_all_triangle_indices(dm,True),u.GeometryScriptTriangleList))
    mids=L.convert_index_list_to_array(pick(M.get_all_triangle_material_i_ds(dm),u.GeometryScriptIndexList))
    pos=array.array('f',(c for p in positions for c in (p.x,p.y,p.z)))
    tri=array.array('i',(c for t in triangles for c in (t.x,t.y,t.z)))
    mid=array.array('i',mids);uv=array.array('f');normal=array.array('f')
    for tid in range(len(triangles)):
        result=Q.get_triangle_u_vs(dm,0,tid)
        for v in result[:3]:uv.extend((v.x,v.y))
        vectors=[v for v in Q.get_triangle_normals(dm,tid) if isinstance(v,u.Vector)]
        for n in vectors[:3]:normal.extend((n.x,n.y,n.z))
    header={'key':key,'path':mesh.get_path_name(),'slots':[str(s.material_slot_name) for s in slots],
        'materials':[s.material_interface.get_path_name() if s.material_interface else None for s in slots],
        'vertices':len(positions),'triangles':len(triangles),'uv_sets':Q.get_num_uv_sets(dm)}
    with (OUT/(key+'.bin')).open('wb') as f:
        f.write((json.dumps(header)+'\n').encode())
        for a in (pos,tri,mid,uv,normal):a.tofile(f)
    file=P/'Content'/(path.removeprefix('/Game/')+'.uasset')
    meta[key]={**header,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
        'source':list(mesh.get_editor_property('asset_import_data').extract_filenames())}
    if key=='Body':
        info=next(x for x in B.get_all_bones_info(dm) if isinstance(x,(list,u.Array)))
        names=['']*len(info)
        for b in info:names[b.index]=str(b.name)
        dominant=[];weights=[]
        for vid in range(len(positions)):
            ws=next(x for x in B.get_vertex_bone_weights(dm,vid) if isinstance(x,(list,u.Array)))
            pairs=sorted(((int(w.bone_index),float(w.weight)) for w in ws),key=lambda p:-p[1])
            weights.append(pairs);dominant.append(pairs[0][0] if pairs else -1)
        (OUT/'Body_bones.json').write_text(json.dumps({'bones':names,'dominant':dominant,'weights':weights}))
    print('A762_SURFACE_DETAIL_INPUT',key,len(positions),len(triangles),flush=True)
(OUT/'current.json').write_text(json.dumps(meta,indent=2))
