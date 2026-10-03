"""Read current third-combo thrust and idle as animation authoring inputs."""
import json
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
mesh = u.load_asset('/Game/Characters/ModularOutfit20260924/BarePalmV7/RuneSword/SK_RuneSword_BareArmsV7')
ref = u.AnimPoseExtensions.get_reference_pose(mesh.skeleton)
names = [str(n) for n in u.AnimPoseExtensions.get_bone_names(ref)]
component = u.SkeletalMeshComponent()
component.set_skeletal_mesh_asset(mesh)
parents = {n:str(component.get_parent_bone(n)) for n in names}
options = u.AnimPoseEvaluationOptions()
options.evaluation_type = u.AnimDataEvalType.SOURCE
options.optional_skeletal_mesh = mesh

def pack(t):
    p,q,s = t.translation,t.rotation,t.scale3d
    return dict(p=[p.x,p.y,p.z],q=[q.w,q.x,q.y,q.z],s=[s.x,s.y,s.z])

def world(pose):
    return {n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names}

out = dict(mesh=mesh.get_path_name(),skeleton=mesh.skeleton.get_path_name(),
           parents=parents,reference=world(ref),variants={})
profile = u.load_asset('/Game/Weapons/AnimationProfiles20261001/Melee/DA_Sword_LongGrip')
if profile:
    out['long_grip_profile'] = dict(asset=profile.get_path_name(),clips=[])
    for clip in profile.get_editor_property('clips'):
        base,retained = clip.get_editor_property('base'),clip.get_editor_property('retained')
        if not base or not any(base.get_name().endswith('_'+r) for r in ('Idle','Thrust')):
            continue
        tracks = [dict(bone=str(tr.get_editor_property('bone')),times=list(tr.get_editor_property('times')),
                       values=list(tr.get_editor_property('values'))) for tr in clip.get_editor_property('tracks')]
        out['long_grip_profile']['clips'].append(dict(base=base.get_path_name(),
            retained=retained.get_path_name() if retained else None,tracks=tracks))

for variant,folder in [('Standard','/Game/Weapons/AzureRunesword20260913'),
                       ('LongGrip','/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations')]:
    idle = u.load_asset(folder+'/A_RuneSword_Idle')
    thrust = u.load_asset(folder+'/A_RuneSword_Thrust')
    if not idle or not thrust:
        raise RuntimeError('Current donor missing '+variant)
    samples = [dict(seconds=i/120,world=world(u.AnimPoseExtensions.get_anim_pose_at_time(thrust,i/120,options)))
               for i in range(151)]
    out['variants'][variant] = dict(idle=idle.get_path_name(),thrust=thrust.get_path_name(),
        idle_world=world(u.AnimPoseExtensions.get_anim_pose_at_time(idle,0,options)),
        thrust_seconds=thrust.get_editor_property('sequence_length'),samples=samples)
(P/'inputs.json').write_text(json.dumps(out,separators=(',',':')),encoding='utf-8')
print('UPPERCUT_V5_DONOR_INPUTS_SAVED: current third-combo thrust, 2 grip variants')
