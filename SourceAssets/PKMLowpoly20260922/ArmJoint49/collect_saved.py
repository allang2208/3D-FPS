"""Read saved wrist seams and elbow tracks for the user's requested joint inspection."""
import hashlib,json
from pathlib import Path
import unreal as u
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2];OUT=HERE/'SavedReadback';OUT.mkdir(exist_ok=True)
receipt=json.loads((HERE/'install_receipt.json').read_text())
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights;Q=u.GeometryScript_MeshQueries
def xyz(v):return [v.x,v.y,v.z]
def pack(t):return {'p':xyz(t.translation),'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':xyz(t.scale3d)}
for path,info in receipt['meshes'].items():
    asset=u.load_asset(path)
    dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot inspect '+path)
    _,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
    _,vs,_=Q.get_all_vertex_positions(dm,False);vs=u.GeometryScript_List.convert_vector_list_to_array(vs)
    _,ts,_=Q.get_all_triangle_indices(dm,False);ts=u.GeometryScript_List.convert_triangle_list_to_array(ts)
    ids=sorted({v for t in ts for v in (t.x,t.y,t.z)});mapping={v:i for i,v in enumerate(ids)};weights=[]
    for vi in ids:
        _,ws,valid=B.get_vertex_bone_weights(dm,vi)
        weights.append({names[w.bone_index]:w.weight for w in ws if w.weight>0})
    data={'asset':path,'positions':[xyz(vs[i]) for i in ids],'weights':weights,
        'triangles':[[mapping[v] for v in (t.x,t.y,t.z)] for t in ts],
        'bones':{str(b.name):dict(pack(b.world_transform),index=b.index,parent=b.parent_index) for b in bones}}
    (OUT/(info['family']+'.json')).write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    print('SAVED_JOINT_MESH_READ',info['family'],flush=True)
old=json.loads((HERE/'Inputs/poses.json').read_text())
paths=list(receipt['animations'])+[v['asset'] for n,v in old.items() if n.endswith('_idle')]
mesh=u.load_asset('/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular.SK_PKM_Manny_Modular')
names=list(next(iter(old.values()))['frames'][0]);poses={}
opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.evaluation_type=u.AnimDataEvalType.RAW
for path in paths:
    anim=u.load_asset(path);count=anim.get_editor_property('data_model_interface').get_number_of_keys();duration=anim.get_play_length();rows=[]
    for i in range(count):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(anim,duration*i/max(1,count-1),opt)
        rows.append({n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names})
    poses[anim.get_name()]={'asset':path,'duration':duration,'frames':rows}
(OUT/'poses.json').write_text(json.dumps(poses,separators=(',',':')),encoding='utf-8')
print('SAVED_JOINT_POSES_READ',len(poses),flush=True)
