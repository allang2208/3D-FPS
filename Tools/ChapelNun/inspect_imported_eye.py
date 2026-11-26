import unreal as u,json
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115/HeadQualityR2')
mesh=u.load_asset('/Game/Characters/ChapelNun20261115/HeadQualityR2/Meshes/SK_Nun_Head_R2_Final')
Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List
dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.RENDER_DATA))
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError(str(status))
_,ps,_=Q.get_all_vertex_positions(dm,False);_,fs,_=Q.get_all_triangle_indices(dm,False)
ps=L.convert_vector_list_to_array(ps);fs=L.convert_triangle_list_to_array(fs)
eyes=[];counts={};normal_sums={};normal_counts={}
for i,t in enumerate(fs):
 p=[ps[j] for j in (t.x,t.y,t.z)];x=sum(v.x for v in p)/3;y=sum(v.y for v in p)/3;z=sum(v.z for v in p)/3
 if 1.8<abs(x)<4.3 and y>7. and 157.1<z<157.75:
  mi=u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0];counts[mi]=counts.get(mi,0)+1
  _,a,b,c,_=Q.get_triangle_normals(dm,i)
  normal_sums[mi]=normal_sums.get(mi,0)+sum(n.y for n in (a,b,c))/3;normal_counts[mi]=normal_counts.get(mi,0)+1
  if counts[mi]<30:eyes.append({'position':[x,y,z],'material':mi,'normal':[[n.x,n.y,n.z] for n in (a,b,c)]})
mat=u.load_asset('/Game/Characters/ChapelNun20261115/HeadQualityR2/Materials/M_Nun_EyeSurface')
props={}
for name in ['MP_BASE_COLOR','MP_METALLIC','MP_ROUGHNESS','MP_NORMAL']:
 node=u.MaterialEditingLibrary.get_material_property_input_node(mat,getattr(u.MaterialProperty,name));item={'class':node.get_class().get_name() if node else None}
 for key in ['r','constant','texture']:
  try:item[key]=str(node.get_editor_property(key))
  except Exception:pass
 props[name]=item
report={'eye_region_materials':counts,'normal_y':{k:normal_sums[k]/normal_counts[k] for k in normal_sums},'inputs':props,'sample_triangles':eyes,'material':{k:str(mat.get_editor_property(k)) for k in ['shading_model','use_material_attributes','two_sided','tangent_space_normal','blend_mode']}}
(R/'eye_readback.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('EYE_READBACK',counts,report['material'],flush=True)
