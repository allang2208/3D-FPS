"""User-requested inspection of the active hand rig and the two saved clips."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
names=['WPN_root','hand_l','hand_r','lowerarm_l','lowerarm_r','upperarm_l','upperarm_r','index_01_l','index_03_l','middle_01_l','middle_03_l']
def pack(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return dict(p=[p.x,p.y,p.z],q=[q.w,q.x,q.y,q.z],s=[s.x,s.y,s.z])
out={'runtime':[],'clips':{}}
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
out['pie_active']=bool(world)
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Character):
        for mesh in actor.get_components_by_class(u.SkeletalMeshComponent):
            if 'RuneSwordViewmodel' not in mesh.get_name():continue
            out['runtime'].append({'actor':actor.get_name(),'mesh':mesh.get_skeletal_mesh_asset().get_path_name(),
                'component':pack(mesh.get_world_transform()),
                'bones':{n:pack(mesh.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT)) for n in names},
                'modules':[{'name':c.get_name(),'transform':pack(c.get_relative_transform()),'mesh':c.static_mesh.get_path_name() if c.static_mesh else None}
                    for c in actor.get_components_by_class(u.StaticMeshComponent) if c.get_name().startswith('ModularSword')]})
for variant in ('Standard','LongGrip'):
    path='/Game/Weapons/Zhanmadao20261018/ChixiaoDoubleHeavyV1/A_Chixiao_DoubleHeavy_'+variant
    asset=u.load_asset(path);data={}
    for kind in ('SOURCE','COMPRESSED'):
        opts=u.AnimPoseEvaluationOptions();opts.evaluation_type=getattr(u.AnimDataEvalType,kind)
        rows=[]
        for t in (0.,.12,.15,.18,.21,.24,.27,.30,.38,.5,.75,.9,1.):
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(asset,t,opts)
            rows.append({'t':t,'bones':{n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names}})
        data[kind]=rows
    out['clips'][variant]=data
(P/'runtime-input.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('CHIXIAO_GRIP_INPUT_SAVED',{'pie':out['pie_active'],'rigs':len(out['runtime']),'clips':list(out['clips'])})
