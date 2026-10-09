"""Read the affected gun triangles and normals from UE's saved source/render data."""
import unreal as u,json,math
from pathlib import Path
O=Path(__file__).parent
mesh=u.load_asset('/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7')
Q=u.GeometryScript_MeshQueries;G=u.GeometryScript_AssetUtils;L=u.GeometryScript_List
gun=next(i for i,m in enumerate(mesh.materials) if str(m.material_slot_name)=='TTI_Benelli_M4')
def xyz(v):return [v.x,v.y,v.z]
output={}
for label,lod in [('source',u.GeometryScriptLODType.SOURCE_MODEL),('render',u.GeometryScriptLODType.RENDER_DATA)]:
    dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD(lod_type=lod,lod_index=0))
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+label)
    _,ps,_=Q.get_all_vertex_positions(dm,False);ps=L.convert_vector_list_to_array(ps)
    _,ts,_=Q.get_all_triangle_indices(dm,False);ts=L.convert_triangle_list_to_array(ts)
    rows=[]
    for index,t in enumerate(ts):
        mat,valid=u.GeometryScript_Materials.get_triangle_material_id(dm,index)
        if mat!=gun:continue
        a,b,c=[ps[i] for i in (t.x,t.y,t.z)]
        cross=u.MathLibrary.cross_vector_vector(b-a,c-a)
        area=math.sqrt(cross.x**2+cross.y**2+cross.z**2)/2
        if area<1:continue
        uv=Q.get_triangle_u_vs(dm,0,index)
        _,n0,n1,n2,_=Q.get_triangle_normals(dm,index)
        _,valid,nt,tt,bt=Q.get_triangle_normal_tangents(dm,index)
        rows.append({'id':index,'area':area,'position':[xyz(p) for p in (a,b,c)],
            'uv':[[p.x,p.y] for p in uv[:3]],'normal':[xyz(n) for n in (n0,n1,n2)],
            'tangent_valid':valid,'tangent':[xyz(v) for v in (tt.vector0,tt.vector1,tt.vector2)],'bitangent':[xyz(v) for v in (bt.vector0,bt.vector1,bt.vector2)]})
    rows.sort(key=lambda x:x['area'],reverse=True)
    output[label]=rows[:100]
(O/'ue_surface_inputs.json').write_text(json.dumps(output),encoding='utf-8')
print('SUPER90_SURFACE_INPUTS_READ', {key:len(rows) for key,rows in output.items()})
