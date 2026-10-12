"""Read current production mounts, skin, poses and shared grip profiles."""
import gzip,json,hashlib
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=O.parents[1];O.mkdir(exist_ok=True)
Q=u.GeometryScript_MeshQueries;G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
def xyz(v):return [v.x,v.y,v.z]
def pack(t):return [*xyz(t.translation),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*xyz(t.scale3d)]
def dump(name,data):
    with gzip.open(O/(name+'.json.gz'),'wt',encoding='utf-8') as f:json.dump(data,f,separators=(',',':'))
def geometry(path,skinned=False):
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError(path)
    fn=G.copy_mesh_from_skeletal_mesh if skinned else G.copy_mesh_from_static_mesh
    dm,status=fn(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Geometry read failed '+path)
    _,vl,_=Q.get_all_vertex_positions(dm,False);vs=u.GeometryScript_List.convert_vector_list_to_array(vl)
    _,tl,_=Q.get_all_triangle_indices(dm,False);ts=u.GeometryScript_List.convert_triangle_list_to_array(tl)
    slots=mesh.materials if skinned else mesh.static_materials
    d={'path':path,'vertices':[xyz(v) for v in vs],'faces':[xyz(t) for t in ts],
       'materials':[u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0] for i in range(len(ts))],
       'slots':[{'name':str(s.material_slot_name),'path':s.material_interface.get_path_name() if s.material_interface else None} for s in slots]}
    if skinned:
        _,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
        d['rest']={str(b.name):pack(b.world_transform) for b in bones}
        d['parents']={str(b.name):names.get(b.parent_index) for b in bones};d['weights']=[]
        for i in range(len(vs)):
            _,weights,ok=B.get_vertex_bone_weights(dm,i)
            if not ok:raise RuntimeError('Skin read failed')
            d['weights'].append({names[w.bone_index]:w.weight for w in weights if w.weight>0})
    dump(mesh.get_name(),d);return mesh,d
mesh,data=geometry('/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7',True)
for family in ('vertical','tactical_vertical','canted','prism','angled'):
    geometry('/Game/Weapons/Super90/Foregrips20261007/Meshes/SM_Super90_'+family)
profiles={};clips={}
for family in ('vertical','canted','prism','angled'):
    path='/Game/Weapons/Super90/Foregrips20261007/Profiles/DA_Super90_'+family
    profile=u.load_asset(path);rows=[]
    for clip in profile.get_editor_property('clips'):
        base=clip.get_editor_property('base');retained=clip.get_editor_property('retained')
        row={'base':base.get_path_name(),'duration':clip.get_editor_property('duration'),'tracks':[]}
        if retained:row['retained']=retained.get_path_name()
        clips[base.get_path_name()]=base
        for tr in clip.get_editor_property('tracks'):
            row['tracks'].append({'bone':str(tr.get_editor_property('bone')),'times':list(tr.get_editor_property('times')),'values':list(tr.get_editor_property('values'))})
        rows.append(row)
    profiles[family]={'family':family,'path':path,'clips':rows}
dump('profiles_before',profiles)
opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.evaluation_type=u.AnimDataEvalType.COMPRESSED;opt.should_retarget=False
poses={}
for path,clip in clips.items():
    length=clip.get_play_length();steps=max(1,round(length*60));samples=[]
    for i in range(steps+1):
        time=length*i/steps;pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,time,opt)
        samples.append({'time':time,'local':{n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in data['rest']}})
    poses[path]={'duration':length,'samples':samples}
    print('GRIP_INPUT_CLIP '+clip.get_name(),flush=True)
dump('poses',poses)
# Read the active shared M4 profiles, not historical filenames assumed by the old author.
donors={}
for family in profiles:
    path='/Game/Weapons/AnimationProfiles20261001/ue_m4a1/DA_'+family
    profile=u.load_asset(path)
    if not profile:raise RuntimeError('Missing accepted donor '+path)
    rows=[]
    for clip in profile.get_editor_property('clips'):
        base=clip.get_editor_property('base');retained=clip.get_editor_property('retained')
        if 'idle' not in base.get_name().lower():continue
        source=retained or base;pose=u.AnimPoseExtensions.get_anim_pose_at_time(source,0,u.AnimPoseEvaluationOptions())
        local={n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in data['rest']}
        tracks=[{'bone':str(t.get_editor_property('bone')),'times':list(t.get_editor_property('times')),'values':list(t.get_editor_property('values'))} for t in clip.get_editor_property('tracks')]
        rows.append({'base':base.get_path_name(),'source':source.get_path_name(),'local':local,'tracks':tracks})
    donors[family]={'profile':path,'idle':rows}
dump('donor_profiles',donors)
(O/'exported.json').write_text(json.dumps({'grips':5,'profiles':4,'clips':len(poses),'runtime_tested':False},indent=2))
print('SUPER90_GRIP_INPUTS_READY',flush=True)
