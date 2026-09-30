"""Read back the saved repair for the user's specifically requested ADS check."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;record=json.loads((O/'delivery.json').read_text());mesh=u.load_asset(record['asset'])
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights;Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List;M=u.GeometryScript_Materials
dm,res=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if res!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read saved sleeve')
_,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
_,p,_=Q.get_all_vertex_positions(dm,False);p=L.convert_vector_list_to_array(p);_,t,_=Q.get_all_triangle_indices(dm,False);t=L.convert_triangle_list_to_array(t)
weights=[]
for i in range(len(p)):
 _,ws,valid=B.get_vertex_bone_weights(dm,i)
 if not valid:raise RuntimeError('Invalid saved weight')
 weights.append({names[w.bone_index]:w.weight for w in ws if w.weight>0})
out={'mesh':mesh.get_path_name(),'positions':[[v.x,v.y,v.z] for v in p],'weights':weights,'triangles':[[f.x,f.y,f.z] for f in t],'triangle_materials':[M.get_triangle_material_id(dm,i)[0] for i in range(len(t))]}
(O/'installed_weights.json').write_text(json.dumps(out,separators=(',',':')))
print('ADS34_SAVED_READBACK',len(bones),len(p),len(t),flush=True)
