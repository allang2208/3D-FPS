import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];D=json.loads((O/'capture.json').read_text());C=json.loads((O/'production.json').read_text());RP=O/'install_receipt.json';R=json.loads(RP.read_text());review=json.loads((O/'saved_asset_review.json').read_text());G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries
sms=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
for key,result in review['assets'].items():
 if not result['collapsed_uv0']['interface']:continue
 path=D['assets'][key]['path'];disk=P/'Content'/(path.removeprefix('/Game/')+'.uasset')
 if hashlib.sha256(disk.read_bytes()).hexdigest()!=R['installed'][key]['sha256']:raise RuntimeError('Asset changed '+key)
 mesh=u.load_asset(path);settings=sms.get_lod_build_settings(mesh,0);dm,status=G.copy_mesh_from_static_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False,request_tangents=True),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL))
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Read '+key)
 _,p,_=Q.get_all_vertex_positions(dm,False);p=u.GeometryScript_List.convert_vector_list_to_array(p);_,tri,_=Q.get_all_triangle_indices(dm,False);tri=u.GeometryScript_List.convert_triangle_list_to_array(tri);fixed=0
 for tid,t in enumerate(tri):
  if u.GeometryScript_Materials.get_triangle_material_id(dm,tid)[0]==C['assets'][key]['body_slot']:continue
  a,b,c,_=Q.get_triangle_u_vs(dm,0,tid)
  if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))>=2e-14:continue
  pts=[[p[i].x,p[i].y,p[i].z] for i in [t.x,t.y,t.z]];x=[pts[1][j]-pts[0][j] for j in range(3)];y=[pts[2][j]-pts[0][j] for j in range(3)];n=[x[1]*y[2]-x[2]*y[1],x[2]*y[0]-x[0]*y[2],x[0]*y[1]-x[1]*y[0]]
  if sum(v*v for v in n)<=4e-16:continue
  axis=max(range(3),key=lambda i:abs(n[i]));axes=[i for i in range(3) if i!=axis]
  uv=[u.Vector2D(p[axes[0]]/4.,p[axes[1]]/4.) for p in pts]
  _,ok=u.GeometryScript_UVs.set_mesh_triangle_u_vs(dm,0,tid,u.GeometryScriptUVTriangle(uv0=uv[0],uv1=uv[1],uv2=uv[2]),True)
  if not ok:raise RuntimeError('Set UV '+key)
  fixed+=1
 opts=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,use_original_vertex_order=True,replace_materials=False)
 _,status=G.copy_mesh_to_static_mesh(dm,mesh,opts,u.GeometryScriptMeshWriteLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Write '+key)
 u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh);sms.set_lod_build_settings(mesh,0,settings)
 if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Save '+key)
 R['installed'][key]['sha256']=hashlib.sha256(disk.read_bytes()).hexdigest();R['installed'][key]['interface_uv_faces_repaired']=fixed;RP.write_text(json.dumps(R,indent=2));print('PHANTOM_INTERFACE_UV_FIXED',key,fixed,flush=True)
print('PHANTOM_INTERFACE_UV_COMPLETE',flush=True)
