import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
mesh=u.load_asset('/Game/Weapons/SVCH/Refined20261018/SK_SVCH_Refined_R4')
G,Q,LU=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_List
def pick(r,t):return next(v for v in r if isinstance(v,t))
dm=u.DynamicMesh();lod=u.GeometryScriptMeshReadLOD();lod.lod_type=u.GeometryScriptLODType.SOURCE_MODEL
G.copy_mesh_from_skeletal_mesh(mesh,dm,u.GeometryScriptCopyMeshFromAssetOptions(),lod)
pos=LU.convert_vector_list_to_array(pick(Q.get_all_vertex_positions(dm,True),u.GeometryScriptVectorList))
tris=LU.convert_triangle_list_to_array(pick(Q.get_all_triangle_indices(dm,True),u.GeometryScriptTriangleList))
ids=LU.convert_index_list_to_array(pick(u.GeometryScript_Materials.get_all_triangle_material_i_ds(dm),u.GeometryScriptIndexList))
data={'arms':[],'normal_dots':{},'materials':[]}
for s in list(mesh.get_editor_property('materials'))[9:]:data['materials'].append(s.material_interface.get_path_name())
print('SVCH_UV_SIGNATURE',Q.get_triangle_u_vs.__doc__,flush=True)
for ti,(t,slot) in enumerate(zip(tris,ids)):
    a,b,c=pos[t.x],pos[t.y],pos[t.z]
    face=(b-a).cross(c-a);face=face/max(face.length(),1e-30)
    normals=[v for v in Q.get_triangle_normals(dm,ti) if isinstance(v,u.Vector)]
    dots=[face.dot(n) for n in normals]
    data['normal_dots'].setdefault(str(slot),[]).extend(dots)
    if slot>=9:
        uv=[v for v in Q.get_triangle_u_vs(dm,0,ti) if isinstance(v,u.Vector2D)]
        data['arms'].append({'p':[[v.x,v.y,v.z] for v in (a,b,c)],'uv':[[v.x,v.y] for v in uv]})
data['normal_dots']={k:{'min':min(v),'negative':sum(x<0 for x in v),'mean':sum(v)/len(v),'count':len(v)} for k,v in data['normal_dots'].items()}
(O/'arm_surface.json').write_text(json.dumps(data))
print('SVCH_ARM_SURFACE',json.dumps({k:v for k,v in data.items() if k!='arms'}),flush=True)
