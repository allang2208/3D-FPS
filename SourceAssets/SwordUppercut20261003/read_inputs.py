"""Read the installed idle/native rig needed to author an original uppercut."""
import json
from pathlib import Path
import unreal as u

P = Path(__file__).parent
mesh = u.load_asset('/Game/Characters/ModularOutfit20260924/BarePalmV7/RuneSword/SK_RuneSword_BareArmsV7')
if not mesh:
    raise RuntimeError('Current sword bare arms unavailable')
ref = u.AnimPoseExtensions.get_reference_pose(mesh.skeleton)
names = [str(n) for n in u.AnimPoseExtensions.get_bone_names(ref)]
component = u.SkeletalMeshComponent()
component.set_skeletal_mesh_asset(mesh)
parents = {n: str(component.get_parent_bone(n)) for n in names}
options = u.AnimPoseEvaluationOptions()
options.evaluation_type = u.AnimDataEvalType.SOURCE
options.optional_skeletal_mesh = mesh

def pack(t):
    p, q, s = t.translation, t.rotation, t.scale3d
    return dict(p=[p.x,p.y,p.z], q=[q.w,q.x,q.y,q.z], s=[s.x,s.y,s.z])

def world(pose):
    return {n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names}

out = dict(mesh=mesh.get_path_name(), skeleton=mesh.skeleton.get_path_name(),
           parents=parents, reference=world(ref), variants={})
for variant, folder in [('Standard','/Game/Weapons/AzureRunesword20260913'),
                        ('LongGrip','/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations')]:
    idle = u.load_asset(folder+'/A_RuneSword_Idle')
    if not idle:
        raise RuntimeError('Missing current idle '+folder)
    pose = u.AnimPoseExtensions.get_anim_pose_at_time(idle,0.0,options)
    out['variants'][variant] = dict(idle=idle.get_path_name(),world=world(pose))
(P/'inputs.json').write_text(json.dumps(out,separators=(',',':')),encoding='utf-8')
print('UPPERCUT_INPUTS_SAVED bones='+str(len(names)))
