"""Requested diagnosis: saved UV/tangent data and actual material-region mapping."""
import unreal as u,json,math
from pathlib import Path
O=Path(__file__).parent;C=json.loads((O/'inputs.json').read_text());R={}
G,Q,N=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_Normals
for key in ('M16_stock','M16_balanced'):
 mesh=u.load_asset(C['meshes'][key]['path'])
 dm,status=G.copy_mesh_from_static_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL))
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read saved '+key)
 mats,indices,names,_=G.get_section_material_list_from_static_mesh(mesh,u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL))
 _,tl,_=Q.get_all_triangle_indices(dm,False);tri=u.GeometryScript_List.convert_triangle_list_to_array(tl)
 _,pl,_=Q.get_all_vertex_positions(dm,False);pos=u.GeometryScript_List.convert_vector_list_to_array(pl)
 collapsed=0;zero_normals=0;count={};regionwrong=0
 for i,t in enumerate(tri):
  a,b,c,valid=Q.get_triangle_u_vs(dm,0,i)
  area=(b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x)
  if not valid or abs(area)<1e-12:collapsed+=1
  _,n0,n1,n2,valid=Q.get_triangle_normals(dm,i)
  zero_normals+=sum(n.x*n.x+n.y*n.y+n.z*n.z<.5 for n in (n0,n1,n2))
  section=u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0];slot=indices[section];name=str(names[section]);count[name]=count.get(name,0)+1
  if key=='M16_balanced':
   z=[pos[v].z for v in (t.x,t.y,t.z)]
   expected=1 if max(z)<=-.9999 else 0 if min(z)>=-.2001 else 2
   if slot!=expected:regionwrong+=1
 _,tx,ty,valid,gaps=N.get_mesh_per_vertex_tangents(dm,False)
 xs=u.GeometryScript_List.convert_vector_list_to_array(tx);ys=u.GeometryScript_List.convert_vector_list_to_array(ty)
 badx=sum(v.x*v.x+v.y*v.y+v.z*v.z<.5 for v in xs);bady=sum(v.x*v.x+v.y*v.y+v.z*v.z<.5 for v in ys)
 settings=(u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)).get_lod_build_settings(mesh,0)
 R[key]={'triangles':len(tri),'collapsed_uv0_triangles':collapsed,'zero_corner_normals':zero_normals,'tangents_present':valid,'sampled_zero_tangents':badx,'sampled_zero_bitangents':bady,'material_region_mismatches':regionwrong,'material_face_counts':count,'full_precision_uvs':settings.use_full_precision_u_vs,'high_precision_tangents':settings.use_high_precision_tangent_basis}
(O/'diagnosis_after.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
print(json.dumps(R))
if any(r['collapsed_uv0_triangles'] or r['zero_corner_normals'] or r['material_region_mismatches'] or not r['tangents_present'] or r['sampled_zero_tangents'] or r['sampled_zero_bitangents'] for r in R.values()):raise RuntimeError('Scoped source diagnosis still has a surface-data issue; see diagnosis_after.json')
