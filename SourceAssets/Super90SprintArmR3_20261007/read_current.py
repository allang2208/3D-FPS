"""Read the existing editor's loaded Super90 rig; do not start or change PIE."""
import unreal as u, json
from pathlib import Path
O=Path(__file__).parent
def pack(t):
    return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
def path(o):return o.get_path_name() if o else None
mesh=u.load_asset('/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7')
sc=u.SkeletalMeshComponent();sc.set_skeletal_mesh_asset(mesh)
names=[str(sc.get_bone_name(i)) for i in range(sc.get_num_bones())]
data={'clips':{},'actors':[],'profiles':{},'framing':{}}
opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.should_retarget=False
for key,asset in [('M4','/Game/Weapons/M4ContactImpactFinal/A_AKM_idle'),('Super90','/Game/Weapons/Super90/Cransh20261006/Animations/A_Super90_idle')]:
    clip=u.load_asset(asset)
    ref_opt=u.AnimPoseEvaluationOptions();ref_opt.evaluation_type=u.AnimDataEvalType.COMPRESSED;ref_opt.should_retarget=False
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,0.,ref_opt)
    data['framing'][key]={n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in ('hand_r','WPN_root','WPN_RearSight','WPN_FrontSight','upperarm_l','lowerarm_l','hand_l')}
for kind in ('enter','loop'):
    clip=u.load_asset('/Game/Weapons/Super90/TacticalSprint20261007/Animations/A_Super90_sprint_'+kind)
    rows=[]
    for mode in ('SOURCE','COMPRESSED'):
        opt.evaluation_type=getattr(u.AnimDataEvalType,mode)
        for fraction in (0.,.25,.5,.75,1.):
            time=clip.get_play_length()*fraction
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,time,opt)
            rows.append({'mode':mode,'time':time,'local':{n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names}})
    data['clips'][kind]={'asset':path(clip),'revision':u.EditorAssetLibrary.get_metadata_tag(clip,'Super90SprintSource'),'rows':rows}
for family in ('vertical','canted','prism','angled'):
    asset=u.load_asset('/Game/Weapons/Super90/Foregrips20261007/Profiles/DA_Super90_'+family)
    data['profiles'][family]=[]
    for clip in asset.get_editor_property('clips'):
        base=path(clip.get_editor_property('base'))
        if 'sprint_' not in base:continue
        data['profiles'][family].append({'base':base,'tracks':[{'bone':str(t.get_editor_property('bone')),'times':list(t.get_editor_property('times')),'values':list(t.get_editor_property('values'))} for t in clip.get_editor_property('tracks')]})
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
data['game_world']=path(world)
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Character):
        components=[]
        for c in actor.get_components_by_class(u.SkeletalMeshComponent):
            m=c.get_skeletal_mesh_asset()
            if not m or 'Super90' not in path(m):continue
            row={'name':c.get_name(),'mesh':path(m),'transform':pack(c.get_world_transform()),'visible':c.is_visible()}
            row['bones']={n:pack(c.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT)) for n in ('upperarm_l','lowerarm_l','lowerarm_aux_l','lowerarm_twist_02_l','lowerarm_twist_01_l','hand_l')}
            anim=c.get_anim_instance()
            row['anim']=path(anim)
            if anim:
                for prop in ('idle_clip','sprint_clip','sprint_loop_clip','grip_profile'):
                    try:row[prop]=path(anim.get_editor_property(prop))
                    except Exception:pass
            components.append(row)
        if components:data['actors'].append({'actor':path(actor),'components':components})
(O/'current.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
print('SUPER90_CURRENT_READ',data['game_world'],len(data['actors']),flush=True)
