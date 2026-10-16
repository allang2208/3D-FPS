"""Confirm the two UV defects directly from UE SOURCE_MODEL, not FBX export."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;D=json.loads((O/'capture.json').read_text());R={}
G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries
for key,mids in [('HK416',{0,1,2}),('LMG201',{1,2,3})]:
 mesh=u.load_asset(D['assets'][key]['path']);lod=u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL)
 dm,status=G.copy_mesh_from_static_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False,request_tangents=True),lod)
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError(key)
 _,p,_=Q.get_all_vertex_positions(dm,False);p=u.GeometryScript_List.convert_vector_list_to_array(p)
 _,t,_=Q.get_all_triangle_indices(dm,False);t=u.GeometryScript_List.convert_triangle_list_to_array(t)
 row={'body_triangles':0,'collapsed_uv0_nondegenerate_body_triangles':0,'first_collapsed_triangles':[]}
 for tid,tri in enumerate(t):
  if u.GeometryScript_Materials.get_triangle_material_id(dm,tid)[0] not in mids:continue
  row['body_triangles']+=1;pa,pb,pc=p[tri.x],p[tri.y],p[tri.z]
  ax,ay,az=pb.x-pa.x,pb.y-pa.y,pb.z-pa.z;bx,by,bz=pc.x-pa.x,pc.y-pa.y,pc.z-pa.z
  if (ay*bz-az*by)**2+(az*bx-ax*bz)**2+(ax*by-ay*bx)**2<=4e-16:continue
  a,b,c,_=Q.get_triangle_u_vs(dm,0,tid)
  area2=abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))
  if area2<2e-14:
   row['collapsed_uv0_nondegenerate_body_triangles']+=1
   if len(row['first_collapsed_triangles'])<5:row['first_collapsed_triangles'].append({'id':tid,'uv':[[x.x,x.y] for x in (a,b,c)]})
 R[key]=row;(O/'ue_uv_confirmation.json').write_text(json.dumps(R,indent=2),encoding='utf-8');print('UV_SOURCE_CONFIRMED',key,row['collapsed_uv0_nondegenerate_body_triangles'],flush=True)
