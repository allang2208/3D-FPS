import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
def tr(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
d={}
for label,path in [('reference','/Game/Weapons/M4ContactImpactFinal/A_AKM_idle'),('m870','/Game/Weapons/M870/Tactical20261015/Animations/A_M870_idle')]:
 seq=u.load_asset(path);assert seq
 opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=u.AnimDataEvalType.COMPRESSED;opt.should_retarget=False
 pose=u.AnimPoseExtensions.get_anim_pose_at_time(seq,0.,opt)
 d[label]={str(n):tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in u.AnimPoseExtensions.get_bone_names(pose)}
(O/'camera_basis.json').write_text(json.dumps(d,indent=2));print('CAMERA_BASIS_EXPORTED')
