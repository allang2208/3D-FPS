"""Read current PKM geometry and the 30 requested grip/fire/reload sequences."""
import hashlib,json,os
from pathlib import Path
import unreal as u
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2]
OUT=HERE/'Input';OUT.mkdir(exist_ok=True,parents=True)
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights;Q=u.GeometryScript_MeshQueries;E=u.EditorAssetLibrary
config=json.loads((PROJECT/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
source,profile=next((p,v) for p,v in config['profiles'].items() if v['rig_profile']=='PKM')
paths={'Weapon':source,'Bare':profile['native_bare_skin']}
paths.update({family:config['items'][item]['rig_meshes']['PKM'] for family,item in
    [('Brown','ue_field_gloves'),('Black','ue_field_gloves_black'),('Sleeve','ue_field_sweater')]})
def xyz(v):return [v.x,v.y,v.z]
def pack(t):return {'p':xyz(t.translation),'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':xyz(t.scale3d)}
def sha(asset):
    file=PROJECT/'Content'/(asset.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset')
    return hashlib.sha256(file.read_bytes()).hexdigest()
def surface(dm):
    _,vs,_=Q.get_all_vertex_positions(dm,False);vs=u.GeometryScript_List.convert_vector_list_to_array(vs)
    _,ts,_=Q.get_all_triangle_indices(dm,False);ts=u.GeometryScript_List.convert_triangle_list_to_array(ts)
    ids=sorted({v for t in ts for v in (t.x,t.y,t.z)});mapping={v:i for i,v in enumerate(ids)}
    mats=[u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0] for i in range(len(ts))]
    return {'positions':[xyz(vs[i]) for i in ids],'triangles':[[mapping[v] for v in (t.x,t.y,t.z)] for t in ts],
        'triangle_materials':mats},ids
for family,path in paths.items():
    asset=u.load_asset(path)
    dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError(path)
    data,ids=surface(dm);_,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones};weights=[]
    for vi in ids:
        _,ws,valid=B.get_vertex_bone_weights(dm,vi)
        if not valid:raise RuntimeError('Missing weights '+family)
        weights.append({names[w.bone_index]:w.weight for w in ws if w.weight>0})
    data.update(asset=path,sha256=sha(asset),weights=weights,materials=[str(s.material_slot_name) for s in asset.materials],
        bones={str(b.name):dict(pack(b.world_transform),index=b.index,parent=b.parent_index) for b in bones})
    (OUT/(family+'.json')).write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    if family=='Weapon':weapon_data=data
    print('PKM_STATE_READ_MESH',family,len(ids),flush=True)
for family in ['angled','canted','vertical','prism']:
    path='/Game/Weapons/PKMLowpoly20260922/Accessories14/Meshes/SM_PKM_'+family;asset=u.load_asset(path)
    dm,status=G.copy_mesh_from_static_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError(path)
    data,_=surface(dm);data.update(asset=path,sha256=sha(asset),attachment_bone='WPN_root',relative_scale=.01)
    (OUT/('Grip_'+family+'.json')).write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
mesh=u.load_asset(source);bones=weapon_data['bones'];byindex={v['index']:n for n,v in bones.items()}
names={n for n in bones if n.endswith('_l') and not any(x in n for x in ['thigh','calf','foot','ball','toe','ik_foot'])}|{'WPN_root'}
for n in list(names):
    while bones[n]['parent'] in byindex:
        n=byindex[bones[n]['parent']];names.add(n)
names=sorted(names,key=lambda n:bones[n]['index'])
probes=['upperarm_l','lowerarm_l','lowerarm_twist_01_l','lowerarm_twist_02_l','hand_l','index_03_l','thumb_03_l','WPN_root']
manifest=[]
for family in ['base','angled','canted','vertical','prism']:
    for action in ['idle','aim','fire','aim_fire','reload','reload_empty']:
        name='A_PKM_'+('' if family=='base' else family+'_')+action
        folder='Animations' if family=='base' else 'Accessories14/Animations/'+family
        path='/Game/Weapons/PKMLowpoly20260922/'+folder+'/'+name+'.'+name;anim=u.load_asset(path)
        if not anim:raise RuntimeError(path)
        count=anim.get_editor_property('data_model_interface').get_number_of_keys();duration=anim.get_play_length()
        raw=u.AnimPoseEvaluationOptions();raw.optional_skeletal_mesh=mesh;raw.evaluation_type=u.AnimDataEvalType.RAW
        compressed=u.AnimPoseEvaluationOptions();compressed.optional_skeletal_mesh=mesh;compressed.evaluation_type=u.AnimDataEvalType.COMPRESSED
        frames=[];local=[];checks=[]
        for i in range(count):
            time=duration*i/max(1,count-1);pose=u.AnimPoseExtensions.get_anim_pose_at_time(anim,time,raw)
            frames.append({n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names})
            local.append({n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names})
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(anim,time,compressed)
            checks.append({n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in probes})
        times=[0.,duration*.5,duration] if 'reload' not in action else [0.,.5,.65,1.05,1.1,1.4,2.175,2.183333,2.65,3.65,4.0,4.7,5.6,duration]
        renders=[]
        for time in sorted(set(min(t,duration) for t in times)):
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(anim,time,compressed)
            renders.append({'time':time,'pose':{n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in bones}})
        data={'name':name,'family':family,'action':action,'asset':path,'sha256':sha(anim),'duration':duration,'keys':count,
            'revision':E.get_metadata_tag(anim,'PKMLeftArmRevision'),'frames':frames,'local':local,'compressed':checks,'renders':renders}
        (OUT/(name+'.json')).write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
        manifest.append({k:v for k,v in data.items() if k not in ['frames','local','compressed','renders']})
        print('PKM_STATE_READ_CLIP',name,count,flush=True)
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
state={'pid':os.getpid(),'pie':u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor(),
    'world':world.get_path_name() if world else None,'profile':profile,'components':[]}
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Character):
        for component in actor.get_components_by_class(u.SkeletalMeshComponent):
            asset=component.get_skinned_asset()
            if asset and ('PKM' in asset.get_path_name() or 'Outfit' in component.get_name()):
                state['components'].append({'name':component.get_name(),'asset':asset.get_path_name(),
                    'visible':component.is_visible(),'transform':pack(component.get_component_transform())})
(OUT/'runtime.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
print('PKM_STATE50_COLLECTED',len(manifest),state['pie'],flush=True)
