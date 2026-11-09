"""Current saved source, native skin and both side-magazine shells for requested review."""
from pathlib import Path
import pickle,json,hashlib,unreal as u
r=Path(__file__).resolve().parent
exec(compile((r.parent/'Repair18/read_inputs.py').read_text(),str(r/'read_inputs.py'),'exec'))
for role in ('reload','reload_empty'):
    a=u.load_asset('/Game/Weapons/M249/SideMagazine20261108/Animations/A_M249_side_'+role);record(a)
    fps=120;duration=a.get_play_length()
    d['clips'][a.get_path_name()]={'fps':fps,'duration':duration,'frames':[[tr(t) for t in u.AnimationLibrary.get_bone_poses_for_time(a,d['names'],min(i/fps,duration),False,mesh)] for i in range(round(duration*fps)+1)]}
Q,B,L=u.GeometryScript_MeshQueries,u.GeometryScript_BoneWeights,u.GeometryScript_List
def geometry(dm):
    _,p,_=Q.get_all_vertex_positions(dm,False);_,f,_=Q.get_all_triangle_indices(dm,False)
    return dict(vertices=[v.to_tuple() for v in L.convert_vector_list_to_array(p)],faces=[(v.x,v.y,v.z) for v in L.convert_triangle_list_to_array(f)])
dm,result=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
g=geometry(dm);g.update(names=d['names'],parents=d['parents'],bind=d['bind'],slots=[str(s.material_slot_name) for s in mesh.materials])
g['sections']=[u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0] for i in range(len(g['faces']))]
g['weights']=[]
for i in range(len(g['vertices'])):
    _,raw,valid=B.get_vertex_bone_weights(dm,i)
    if not valid:raise RuntimeError('Missing vertex weights')
    g['weights'].append([(w.bone_index,w.weight) for w in raw if w.weight>0])
g['parts']={}
for name in ('SM_m249_side_mag_30','SM_m249_side_mag_45','SM_M249_SidePort'):
    a=u.load_asset('/Game/Weapons/M249/SideMagazine20261108/Meshes/'+name);record(a)
    part,result=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    g['parts'][name]=geometry(part)
with (r/'geometry.pkl').open('wb') as f:pickle.dump(g,f)
with (r/'native.pkl').open('wb') as f:pickle.dump(d,f)
(r/'inputs.json').write_text(json.dumps(receipt,indent=2))
print('M249_CURRENT_SIDE_RELOAD_GEOMETRY_SAVED',len(g['vertices']),flush=True)
