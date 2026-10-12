"""Read only: exact saved Super90 surfaces, bindings and compressed poses."""
import gzip, hashlib, json
from pathlib import Path
import unreal as u
O=Path(__file__).parent; P=O.parents[1]
O.mkdir(exist_ok=True)
Q=u.GeometryScript_MeshQueries; G=u.GeometryScript_AssetUtils; B=u.GeometryScript_BoneWeights
def xyz(v): return [v.x,v.y,v.z]
def transform(t):
    p=t.translation
    return dict(position=xyz(p),axes=[xyz(t.transform_location(v)-p) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))])
targets={'full':'/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7',
 'arms':'/Game/Characters/ModularOutfit20260924/Super90Source20261006/Super90/SK_Super90_BareArmsV7'}
for key,path in targets.items():
    mesh=u.load_asset(path); assert mesh,path
    dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    assert status==u.GeometryScriptOutcomePins.SUCCESS
    _,pv,_=Q.get_all_vertex_positions(dm,False); ps=u.GeometryScript_List.convert_vector_list_to_array(pv)
    _,tv,_=Q.get_all_triangle_indices(dm,False); ts=u.GeometryScript_List.convert_triangle_list_to_array(tv)
    _,bones=B.get_all_bones_info(dm); names={b.index:str(b.name) for b in bones}
    d=dict(path=path,positions=[xyz(p) for p in ps],triangles=[xyz(t) for t in ts],normals=[],uv=[[],[],[],[]],materials=[],weights=[],
        bones={str(b.name):dict(index=b.index,parent=b.parent_index,**transform(b.world_transform)) for b in bones},
        skeleton=mesh.skeleton.get_path_name(),lod_count=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).get_lod_count(mesh),
        slots=[dict(name=str(s.material_slot_name),material=s.material_interface.get_path_name() if s.material_interface else None) for s in mesh.materials])
    for ti in range(len(ts)):
        d['materials'].append(u.GeometryScript_Materials.get_triangle_material_id(dm,ti)[0])
        _,a,b,c,ok=Q.get_triangle_normals(dm,ti); assert ok
        d['normals'].append([xyz(n) for n in (a,b,c)])
        for channel in range(4):
            values=Q.get_triangle_u_vs(dm,channel,ti)
            d['uv'][channel].append([[v.x,v.y] for v in values[:3]] if values[-1] else None)
    for vi in range(len(ps)):
        _,ws,ok=B.get_vertex_bone_weights(dm,vi); assert ok
        d['weights'].append({names[w.bone_index]:w.weight for w in ws if w.weight>0})
    package=P/'Content'/(path.removeprefix('/Game/')+'.uasset');d['sha256']=hashlib.sha256(package.read_bytes()).hexdigest()
    with gzip.open(O/(key+'_before.json.gz'),'wt',encoding='utf-8') as f: json.dump(d,f,separators=(',',':'))
    print('SUPER90_READ',key,len(ps),len(ts),d['sha256'],flush=True)
    if key=='full': full=mesh; bone_names=list(d['bones'])
opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=full;opt.evaluation_type=u.AnimDataEvalType.COMPRESSED
poses={}
for label in ('idle','reload_one','reload_empty','reload_full','inspect','equip','fire'):
    path='/Game/Weapons/Super90/Cransh20261006/Animations/A_Super90_'+label
    a=u.load_asset(path); assert a,path
    length=a.get_play_length(); count=max(2,int(length*30)+1)
    rows=[]
    for f in range(count):
        time=length*f/(count-1); pose=u.AnimPoseExtensions.get_anim_pose_at_time(a,time,opt)
        rows.append(dict(time=time,bones={n:transform(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in bone_names}))
    package=P/'Content'/(path.removeprefix('/Game/')+'.uasset')
    poses[label]=dict(path=path,length=length,sha256=hashlib.sha256(package.read_bytes()).hexdigest(),rows=rows)
    print('SUPER90_POSES',label,count,flush=True)
with gzip.open(O/'poses.json.gz','wt',encoding='utf-8') as f: json.dump(poses,f,separators=(',',':'))
api={}
for cls,names in [(u.GeometryScript_Normals,['update_vertex_normal','set_mesh_triangle_normals']), (G,['copy_mesh_to_skeletal_mesh'])]:
    for n in names:api[cls.__name__+'.'+n]=getattr(getattr(cls,n,None),'__doc__',None)
(O/'api.json').write_text(json.dumps(api,indent=2))
print('SUPER90_READ_COMPLETE',flush=True)
