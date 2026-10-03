"""Read current PKM outfit bindings and arm pose samples for wrist/elbow diagnosis."""
import hashlib,json
from pathlib import Path
import unreal as u
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2]
OUT=HERE/'Inputs';OUT.mkdir(exist_ok=True)
config=json.loads((PROJECT/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
source,profile=next((p,v) for p,v in config['profiles'].items() if v['rig_profile']=='PKM')
paths={'BarePalmV7':profile['native_bare_skin']}
paths.update({family:config['items'][item]['rig_meshes']['PKM'] for family,item in
    [('HuntFieldGlovesV1','ue_field_gloves'),('FittedFieldGlovesV1','ue_field_gloves_black'),('FittedSleevesV1','ue_field_sweater')]})
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights;Q=u.GeometryScript_MeshQueries
def xyz(v):return [v.x,v.y,v.z]
def pack(t):
    return {'p':xyz(t.translation),'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':xyz(t.scale3d)}
for family,path in paths.items():
    asset=u.load_asset(path)
    dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError(path)
    _,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
    _,vs,_=Q.get_all_vertex_positions(dm,False);vs=u.GeometryScript_List.convert_vector_list_to_array(vs)
    _,ts,_=Q.get_all_triangle_indices(dm,False);ts=u.GeometryScript_List.convert_triangle_list_to_array(ts)
    ids=sorted({v for t in ts for v in (t.x,t.y,t.z)});mapping={v:i for i,v in enumerate(ids)}
    weights=[]
    for vi in ids:
        _,ws,valid=B.get_vertex_bone_weights(dm,vi)
        weights.append({names[w.bone_index]:w.weight for w in ws if w.weight>0})
    file=PROJECT/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
    data={'asset':path,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
        'positions':[xyz(vs[i]) for i in ids],'weights':weights,
        'triangles':[[mapping[v] for v in (t.x,t.y,t.z)] for t in ts],
        'bones':{str(b.name):dict(pack(b.world_transform),index=b.index,parent=b.parent_index) for b in bones}}
    (OUT/(family+'.json')).write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    print('ARM_JOINT_INPUT',family,len(ids),len(ts))
mesh=u.load_asset(source)
names=[str(b.name) for b in bones if str(b.name).endswith('_l')]
poses={}
base='/Game/Weapons/PKMLowpoly20260922'
folders=[base+'/Animations']+[base+'/Accessories14/Animations/'+f for f in ['angled','canted','prism','vertical']]
for folder in folders:
    for path in sorted(u.EditorAssetLibrary.list_assets(folder,False,False)):
        anim=u.load_asset(path)
        if not isinstance(anim,u.AnimSequence):continue
        count=anim.get_editor_property('data_model_interface').get_number_of_keys()
        opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.evaluation_type=u.AnimDataEvalType.RAW
        rows=[]
        # Full native samples for the requested joints, not a gameplay launch.
        for i in range(count):
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(anim,anim.get_play_length()*i/max(1,count-1),opt)
            rows.append({n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names})
        poses[anim.get_name()]={'asset':path,'duration':anim.get_play_length(),'frames':rows}
(OUT/'poses.json').write_text(json.dumps(poses,separators=(',',':')),encoding='utf-8')
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
runtime={'game_world':world.get_name() if world else None,'components':[]}
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Character):
        for component in actor.get_components_by_class(u.SkeletalMeshComponent):
            asset=component.get_skinned_asset()
            if asset and ('PKM' in asset.get_path_name() or 'Outfit' in component.get_name()):
                runtime['components'].append({'name':component.get_name(),'mesh':asset.get_path_name(),'visible':component.is_visible()})
(OUT/'runtime.json').write_text(json.dumps(runtime,indent=2),encoding='utf-8')
print('ARM_JOINT_READ_COMPLETE',len(poses),runtime)
