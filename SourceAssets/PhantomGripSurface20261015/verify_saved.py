import unreal as u,json,math,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];D=json.loads((O/'capture.json').read_text());C=json.loads((O/'production.json').read_text());receipt=json.loads((O/'install_receipt.json').read_text());R={'assets':{},'complete':False,'gameplay_tested':False}
G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;sms=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
if not receipt['complete']:raise RuntimeError('Install incomplete')
for key,row in D['assets'].items():
 mesh=u.load_asset(row['path']);actual={str(s.material_slot_name):s.material_interface.get_path_name() for s in mesh.static_materials};expected={s['name']:s['material'] for s in row['slots']}
 if actual!=expected:raise RuntimeError('Binding mismatch '+key)
 settings=sms.get_lod_build_settings(mesh,0)
 if settings.recompute_normals or not settings.use_full_precision_u_vs:raise RuntimeError('Build settings mismatch '+key)
 dm,status=G.copy_mesh_from_static_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False,request_tangents=True),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL))
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+key)
 _,verts,_=Q.get_all_vertex_positions(dm,False);verts=u.GeometryScript_List.convert_vector_list_to_array(verts);_,tris,_=Q.get_all_triangle_indices(dm,False);tris=u.GeometryScript_List.convert_triangle_list_to_array(tris)
 r={'triangles':len(tris),'material_triangles':{},'collapsed_uv0':{'body':0,'interface':0},'invalid_normals':0,'authored_normals_preserved':True,'full_precision_uv':True,'material_bindings_preserved':True,'mask4_nonzero_corners':0}
 for tid,t in enumerate(tris):
  mid=int(u.GeometryScript_Materials.get_triangle_material_id(dm,tid)[0]);r['material_triangles'][mid]=r['material_triangles'].get(mid,0)+1
  _,a,b,c,valid=Q.get_triangle_normals(dm,tid)
  r['invalid_normals']+=sum(1 for n in [a,b,c] if not valid or not all(math.isfinite(x) for x in [n.x,n.y,n.z]) or n.x*n.x+n.y*n.y+n.z*n.z<.5)
  pa,pb,pc=verts[t.x],verts[t.y],verts[t.z];ax,ay,az=pb.x-pa.x,pb.y-pa.y,pb.z-pa.z;bx,by,bz=pc.x-pa.x,pc.y-pa.y,pc.z-pa.z
  if (ay*bz-az*by)**2+(az*bx-ax*bz)**2+(ax*by-ay*bx)**2>4e-16:
   a,b,c,_=Q.get_triangle_u_vs(dm,0,tid);area=abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))
   if area<2e-14:r['collapsed_uv0']['body' if mid==C['assets'][key]['body_slot'] else 'interface']+=1
  if key=='LMG201':
   a,b,c,_=Q.get_triangle_u_vs(dm,4,tid);r['mask4_nonzero_corners']+=sum(1 for x in [a,b,c] if x.x>.00001)
 if r['collapsed_uv0']['body'] or r['invalid_normals']:raise RuntimeError('Invalid saved surface '+key+' '+str(r))
 if key=='LMG201' and r['mask4_nonzero_corners']==0:raise RuntimeError('LMG mask lost')
 R['assets'][key]=r;(O/'saved_asset_review.json').write_text(json.dumps(R,indent=2),encoding='utf-8');print('PHANTOM_SAVED_REVIEW',key,r,flush=True)
R['complete']=True;(O/'saved_asset_review.json').write_text(json.dumps(R,indent=2),encoding='utf-8');print('PHANTOM_SAVED_REVIEW_COMPLETE',flush=True)
