import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
out={}
for key,path in (('M4','/Game/Weapons/M4ContactImpactFinal/A_AKM_idle'),('Super90','/Game/Weapons/Super90/Cransh20261006/Animations/A_Super90_idle')):
 opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=u.AnimDataEvalType.COMPRESSED;opt.should_retarget=False
 pose=u.AnimPoseExtensions.get_anim_pose_at_time(u.load_asset(path),0.,opt)
 row={}
 for n in ('hand_r','WPN_root','WPN_RearSight','WPN_FrontSight'):
  t=u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)
  row[n]=[*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
 out[key]=row
(O/'framing.json').write_text(json.dumps(out,indent=2))
print('SUPER90_FRAMING_READ',flush=True)
