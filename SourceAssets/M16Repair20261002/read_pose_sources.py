"""Read only the M16 left-hand poses and currently registered outfit surfaces."""
import hashlib, json
from pathlib import Path
import unreal as u

P = Path(u.Paths.project_dir()).resolve()
O = Path(__file__).parent
C = json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
SOURCE = '/Game/Weapons/M16A2/Gameplay20260919/SK_M16_Manny.SK_M16_Manny'
mesh = u.load_asset(SOURCE)
profile = C['profiles'][SOURCE]
NAMES = list(json.loads((O/'Input/CurrentM16.json').read_text())['bones'])

def xyz(v):
    return [v.x,v.y,v.z]

def tr(t):
    return dict(position=xyz(t.translation),axes=[xyz(t.transform_location(v)-t.translation)
        for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))],
        q=[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],scale=xyz(t.scale3d))

clips = []
for folder in [P/'Content/Weapons/M16A2/Gameplay20260919/Animations',
               P/'Content/Weapons/M16A2/UniversalAttachments20260920/Animations']:
    for f in sorted(folder.rglob('*.uasset')):
        if any(f.stem.endswith('_'+state) for state in ('idle','aim','fire','aim_fire','reload','reload_empty','inspect')):
            path='/Game/'+f.relative_to(P/'Content').with_suffix('').as_posix()
            a=u.load_asset(path)
            opts=u.AnimPoseEvaluationOptions(optional_skeletal_mesh=mesh,evaluation_type=u.AnimDataEvalType.COMPRESSED)
            duration=a.get_play_length()
            rows=[]
            for time in (0.,duration*.5,duration):
                pose=u.AnimPoseExtensions.get_anim_pose_at_time(a,time,opts)
                rows.append(dict(time=time,bones={n:tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in NAMES}))
            clips.append(dict(path=path,duration=duration,poses=rows))
            u.log('CLOVEN_M16_POSE_READ '+f.stem)
(O/'pose_sources.json').write_text(json.dumps(clips,separators=(',',':')),encoding='utf-8')

paths={profile['original_gloved_arms']}
for item in C['items'].values():
    for field in ('rig_meshes','skin_meshes','sleeve_meshes'):
        if item.get(field,{}).get('M16'):
            paths.add(item[field]['M16'])
Q,B,G=u.GeometryScript_MeshQueries,u.GeometryScript_BoneWeights,u.GeometryScript_AssetUtils
outfit=[]
for path in sorted(paths):
    a=u.load_asset(path)
    dm,status=G.copy_mesh_from_skeletal_mesh(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot read '+path)
    _,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
    _,pos,_=Q.get_all_vertex_positions(dm,False);ps=u.GeometryScript_List.convert_vector_list_to_array(pos)
    weapon=[];all_names=set();lo=[float('inf')]*3;hi=[-float('inf')]*3
    for i,p in enumerate(ps):
        for j,v in enumerate(xyz(p)):
            lo[j]=min(lo[j],v);hi[j]=max(hi[j],v)
        _,ws,_=B.get_vertex_bone_weights(dm,i)
        used={names[w.bone_index] for w in ws if w.weight>.0001};all_names.update(used)
        if any(n.startswith('WPN_') for n in used):
            weapon.append(i)
    outfit.append(dict(path=path,vertices=len(ps),weapon_bound_vertices=len(weapon),bounds=[lo,hi],
        weighted_bones=sorted(all_names),slots=[str(s.material_slot_name) for s in a.materials]))
    u.log('CLOVEN_M16_OUTFIT_READ '+path+' weapon_bound_vertices='+str(len(weapon)))
(O/'outfit_sources.json').write_text(json.dumps(outfit,indent=2),encoding='utf-8')
u.log('CLOVEN_M16_POSE_SOURCES_COMPLETE '+str(len(clips)))
