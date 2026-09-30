"""Read native 201 arm and equipped mail weights for a local fitting repair."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;data=json.loads((O/'sources.json').read_text())['meshes']
Q=u.GeometryScript_MeshQueries;B=u.GeometryScript_BoneWeights;G=u.GeometryScript_AssetUtils;L=u.GeometryScript_List;M=u.GeometryScript_Materials
def xyz(v):return [v.x,v.y,v.z]
for key in ['201','shirt']:
 mesh=u.load_asset(data[key]['mesh']);dm,res=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD());_,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
 _,p,_=Q.get_all_vertex_positions(dm,False);p=L.convert_vector_list_to_array(p)
 _,t,_=Q.get_all_triangle_indices(dm,False);t=L.convert_triangle_list_to_array(t)
 faces=[];materials=[]
 for i,tri in enumerate(t):
  mid,valid=M.get_triangle_material_id(dm,i)
  if valid and (key=='shirt' or mid in [0,1,2]):faces.append(xyz(tri));materials.append(mid)
 ids=sorted({i for f in faces for i in f});remap={v:i for i,v in enumerate(ids)};weights=[]
 for vi in ids:
  _,ws,valid=B.get_vertex_bone_weights(dm,vi)
  if not valid:raise RuntimeError('Invalid weight '+key)
  weights.append({names[w.bone_index]:w.weight for w in ws if w.weight>0})
 out={'mesh':mesh.get_path_name(),'vertex_ids':ids,'positions':[xyz(p[i]) for i in ids],'weights':weights,'triangles':[[remap[i] for i in f] for f in faces],'triangle_materials':materials}
 (O/(key+'_weights.json')).write_text(json.dumps(out,separators=(',',':')))
 print('ADS34_WEIGHT_SOURCE',key,len(ids),len(faces),flush=True)
