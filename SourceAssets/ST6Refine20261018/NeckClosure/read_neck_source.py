"""Read the saved native head and existing component identities; no scene mutation."""
import json
from pathlib import Path
import unreal as u
O=Path(__file__).parent
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights;Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List
mesh=u.load_asset('/Game/AsianMale_Jason/Mesh/Head/SKM_Jason_head')
dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read saved head')
_,ps,_=Q.get_all_vertex_positions(dm,False);ps=L.convert_vector_list_to_array(ps)
_,fs,_=Q.get_all_triangle_indices(dm,False);fs=L.convert_triangle_list_to_array(fs)
_,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
def xyz(v):return [v.x,v.y,v.z]
selected=[]
for i,face in enumerate(fs):
    ids=[face.x,face.y,face.z]
    if min(ps[v].z for v in ids)<153.0:selected.append((i,ids))
used=sorted({v for _,f in selected for v in f});remap={v:i for i,v in enumerate(used)}
d=dict(source=mesh.get_path_name(),positions=[xyz(ps[v]) for v in used],triangles=[[remap[v] for v in f] for _,f in selected],weights=[],
       bones={str(b.name):dict(index=b.index,parent=b.parent_index,position=xyz(b.world_transform.translation),axes=[xyz(b.world_transform.transform_location(v)-b.world_transform.translation) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))]) for b in bones})
for vi in used:
    _,weights,_=B.get_vertex_bone_weights(dm,vi);d['weights'].append({names[v.bone_index]:v.weight for v in weights if v.weight>0})
(O/'native_head_neck.json').write_text(json.dumps(d,separators=(',',':')))
level=u.get_editor_subsystem(u.LevelEditorSubsystem)
report={'in_play':bool(level and level.is_in_play_in_editor()),'neck_vertices':len(used),'neck_triangles':len(selected)}
(O/'editor_state.json').write_text(json.dumps(report,indent=2))
print('ST6_NATIVE_NECK_READ',json.dumps(report),flush=True)
