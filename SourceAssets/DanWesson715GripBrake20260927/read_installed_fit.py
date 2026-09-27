"""Read-only geometry and compressed-animation snapshots for the requested fit inspection."""
import json
from pathlib import Path
import unreal as u
O=Path(__file__).parent/'FitInspection';O.mkdir(exist_ok=True)
ROOT=O.parents[2]
G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;B=u.GeometryScript_BoneWeights

def xyz(v):return [v.x,v.y,v.z]
def matrix(t):
    p=t.transform_location(u.Vector(0,0,0));cols=[]
    for a in [u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1)]:
        q=t.transform_location(a);cols.append([q.x-p.x,q.y-p.y,q.z-p.z])
    return [[cols[c][r] for c in range(3)]+[xyz(p)[r]] for r in range(3)]+[[0,0,0,1]]

def read(key,path,skinned=False):
    asset=u.load_asset(path)
    fn=G.copy_mesh_from_skeletal_mesh if skinned else G.copy_mesh_from_static_mesh
    dm,status=fn(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+path)
    _,pv,_=Q.get_all_vertex_positions(dm,False);_,tv,_=Q.get_all_triangle_indices(dm,False)
    verts=u.GeometryScript_List.convert_vector_list_to_array(pv);tris=u.GeometryScript_List.convert_triangle_list_to_array(tv)
    slots=asset.materials if skinned else asset.static_materials
    d={'asset':path,'positions':[xyz(v) for v in verts],'triangles':[xyz(t) for t in tris],
       'slots':[str(s.material_slot_name) for s in slots],'material_paths':[s.material_interface.get_path_name() if s.material_interface else '' for s in slots],
       'materials':[],'uv':[],'normals':[]}
    for i in range(len(tris)):
        d['materials'].append(u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0])
        a,b,c,valid=Q.get_triangle_u_vs(dm,0,i);d['uv'].append([[v.x,v.y] for v in (a,b,c)])
        _,a,b,c,valid=Q.get_triangle_normals(dm,i);d['normals'].append([xyz(v) for v in (a,b,c)])
    if skinned:
        _,bones=B.get_all_bones_info(dm);d['bones']={b.index:str(b.name) for b in bones}
        modifier=u.SkeletonModifier();modifier.set_skeletal_mesh(asset)
        d['reference']={str(b.name):matrix(modifier.get_bone_transform(b.name,True)) for b in bones}
        d['weights']=[]
        for i in range(len(verts)):
            _,weights,valid=B.get_vertex_bone_weights(dm,i)
            d['weights'].append([[w.bone_index,w.weight] for w in weights if w.weight>0])
    (O/(key+'.json')).write_text(json.dumps(d),encoding='utf-8')
    return asset,d

hostpath='/Game/Weapons/DanWesson715/Chrome20260914/SK_DW715_Manny.SK_DW715_Manny'
host,hostdata=read('host',hostpath,True)
config=json.loads((ROOT/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
profile=config['profiles'].get(hostpath,{})
armspath=profile.get('native_bare_skin','')
if armspath:read('bare_arms',armspath,True)
for part in ['dw715_rubber_grip','dw715_target_wood_grip','dw715_muzzle_brake']:
    read(part,'/Game/Weapons/DanWesson715/GripBrake20260927/Meshes/SM_'+part)

opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=u.AnimDataEvalType.COMPRESSED;opt.optional_skeletal_mesh=host
cases=[('idle','/Game/Weapons/DanWesson715/Upgrade20260914/Animations/A_DW715_idle',0),
       ('aim','/Game/Weapons/DanWesson715/Upgrade20260914/Animations/A_DW715_aim',0),
       ('reload_open','/Game/Weapons/DanWesson715/PalmClearance20260915/Animations/A_DW715_speed_0',.65),
       ('reload_insert','/Game/Weapons/DanWesson715/PalmClearance20260915/Animations/A_DW715_speed_0',2.25),
       ('reload_return','/Game/Weapons/DanWesson715/PalmClearance20260915/Animations/A_DW715_speed_0',3.80)]
poses={}
for key,path,t in cases:
    anim=u.load_asset(path)
    if not anim:raise RuntimeError('Missing pose asset '+path)
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(anim,t,opt)
    poses[key]={'asset':path,'time':t,'bones':{name:matrix(u.AnimPoseExtensions.get_bone_pose(pose,name,u.AnimPoseSpaces.WORLD)) for name in hostdata['bones'].values()}}
(O/'poses.json').write_text(json.dumps(poses),encoding='utf-8')
(O/'manifest.json').write_text(json.dumps({'host':hostpath,'bare_arms':armspath,'profile':profile,'parts':3,'poses':list(poses),'read_only':True},indent=2),encoding='utf-8')
u.log('DW715_INSTALLED_FIT_SNAPSHOTS_SAVED '+str(O))
