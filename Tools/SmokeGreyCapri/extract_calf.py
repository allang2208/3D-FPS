"""Export the native calf section with its original UVs and skinning for capris."""
import json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/SmokeGreyCapri20261004'
c=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
body=json.loads((P/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
base=c['profiles'][body['body_mesh']]['base'];asset=u.load_asset(base)
Q=u.GeometryScript_MeshQueries;B=u.GeometryScript_BoneWeights
dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot extract native calf')
_,vectors,_=Q.get_all_vertex_positions(dm,False);ps=u.GeometryScript_List.convert_vector_list_to_array(vectors)
_,indices,_=Q.get_all_triangle_indices(dm,False);ts=u.GeometryScript_List.convert_triangle_list_to_array(indices)
faces=[];normals=[];uv=[]
for ti,t in enumerate(ts):
    slot=u.GeometryScript_Materials.get_triangle_material_id(dm,ti)[0]
    if slot not in [12,16] or min(ps[i].z for i in [t.x,t.y,t.z])>33:continue
    a,b,cc,ok=Q.get_triangle_u_vs(dm,0,ti)
    if not ok:raise RuntimeError('Native calf UV unavailable')
    _,n0,n1,n2,ok=Q.get_triangle_normals(dm,ti)
    if not ok:raise RuntimeError('Native calf normals unavailable')
    faces.append([t.x,t.y,t.z]);uv.append([[v.x,v.y] for v in [a,b,cc]])
    normals.append([[v.x,v.y,v.z] for v in [n0,n1,n2]])
used=sorted({i for f in faces for i in f});remap={v:i for i,v in enumerate(used)};weights=[]
for vi in used:
    _,ws,ok=B.get_vertex_bone_weights(dm,vi)
    if not ok:raise RuntimeError('Native calf binding unavailable')
    weights.append([[w.bone_index,w.weight] for w in ws if w.weight>0])
data=dict(source=base,positions=[[ps[i].x,ps[i].y,ps[i].z] for i in used],triangles=[[remap[i] for i in f] for f in faces],weights=weights,uv=uv,normals=normals,material=asset.materials[16].material_interface.get_path_name())
(R/'native_calf.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
(R/'source_context.json').write_text(json.dumps(dict(profile_key=body['body_mesh'],base=base,pants_covers=[8,10,12,14,16],native_calf_sections=[12,16],skin_cut_z_cm=33,hem_z_cm=30),indent=2),encoding='utf-8')
print('CAPRI_NATIVE_CALF_EXPORTED',len(faces),flush=True)
