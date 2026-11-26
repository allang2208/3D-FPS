"""Capture active waist geometry for the reported crouch overlap (read only)."""
import gc,json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/RangerCrouchFit20261021'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def xyz(v):return [v.x,v.y,v.z]
data=read(R/'inputs.json');G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;B=u.GeometryScript_BoneWeights;L=u.GeometryScript_List
paths=dict(Jason=data['recipe']['ue_field_sweater']['rig_meshes']['Jason'],Owner_Jason=data['recipe']['ue_field_sweater']['owner_body_meshes']['Jason'])
paths['Pants']=data['recipe']['ue_leather_pants']['rig_meshes']['Jason']
paths['PantsHigh']=data['recipe']['ue_leather_pants']['shoe_fit_meshes']['ue_leather_boots']['Jason']
for key,path in paths.items():
    asset=u.load_asset(path);dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+path)
    _,vs,_=Q.get_all_vertex_positions(dm,False);_,fs,_=Q.get_all_triangle_indices(dm,False);_,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
    ps=[xyz(v) for v in L.convert_vector_list_to_array(vs)];tri=[xyz(f) for f in L.convert_triangle_list_to_array(fs)];weights={}
    for i,p in enumerate(ps):
        if p[2]<77 or p[2]>108 or abs(p[0])>25:continue
        _,ww,valid=B.get_vertex_bone_weights(dm,i)
        if valid:weights[str(i)]={names[w.bone_index]:w.weight for w in ww if w.weight>0}
    out=dict(asset=path,positions=ps,triangles=tri,waist_weights=weights)
    (R/(key+'_live_mesh.json')).write_text(json.dumps(out,separators=(',',':')),encoding='utf-8')
    print('LIVE_WAIST_MESH',key,len(ps),len(tri),len(weights),flush=True)
    del dm,out;gc.collect()
# All skeleton bones are needed because trousers use calf and thigh base bones
# that the shirt's waist weights may never reference directly.
shirt=read(Path(data['sources']['Jason']['file']));names=list(shirt['bones']);mesh=u.load_asset(data['body_mesh']);options=u.AnimPoseEvaluationOptions();options.optional_skeletal_mesh=mesh
def pack(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return dict(p=xyz(p),q=[q.x,q.y,q.z,q.w],s=xyz(s))
for key,row in data['clips'].items():
    clip=u.load_asset(row['asset'])
    for sample in row['samples']:
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,sample['time'],options)
        sample['bones']={n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names}
(R/'inputs.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print('FULL_CROUCH_BONES_READ',len(names),flush=True)
