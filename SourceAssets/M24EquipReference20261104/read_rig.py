"""Read the FBX armature parent in component coordinates for unit conversion."""
from pathlib import Path
import json,unreal as u
O=Path(__file__).resolve().parent;d=json.loads((O/'live_source.json').read_text())
host=u.load_asset('/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9')
comp=u.new_object(u.SkeletalMeshComponent);comp.set_skeletal_mesh_asset(host)
par=str(comp.get_parent_bone('VM_Root'))
def tr(m):
    p,q,s=m.translation,m.rotation,m.scale3d
    return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=host;opts.evaluation_type=u.AnimDataEvalType.SOURCE
def pose(a,i):
    if par=='None':return tr(u.Transform())
    return tr(u.AnimPoseExtensions.get_bone_pose(u.AnimPoseExtensions.get_anim_pose_at_time(a,i/30,opts),par,u.AnimPoseSpaces.WORLD))
eq=u.load_asset(d['equip']);idle=u.load_asset('/Game/Weapons/M24/Hold20261027/Animations/A_M24_idle')
out={'name':par,'idle':pose(idle,0),'equip':[pose(eq,i) for i in range(len(d['root']))]}
(O/'armature_parent.json').write_text(json.dumps(out,separators=(',',':')))
print('EQUIP_ARMATURE_PARENT',par,out['equip'][0],flush=True)
