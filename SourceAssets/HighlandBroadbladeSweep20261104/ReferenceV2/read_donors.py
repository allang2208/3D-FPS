from pathlib import Path
import json,unreal as u
P=Path(__file__).resolve().parent
out={}
for role,folder in [('Slash1','/Game/Weapons/AzureRunesword20260913'),('LongGripSlash1','/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations')]:
 clip=u.load_asset(folder+'/A_RuneSword_Slash1')
 options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.SOURCE
 duration=clip.get_play_length();frames=[]
 for i in range(round(duration*60)+1):
  t=min(i/60,duration);pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,options);bones={}
  for name in u.AnimPoseExtensions.get_bone_names(pose):
   tf=u.AnimPoseExtensions.get_bone_pose(pose,name,u.AnimPoseSpaces.LOCAL);p,q,s=tf.translation,tf.rotation,tf.scale3d
   bones[str(name)]=dict(p=[p.x,p.y,p.z],q=[q.w,q.x,q.y,q.z],s=[s.x,s.y,s.z])
  frames.append(bones)
 out[role]=dict(path=clip.get_path_name(),duration=duration,fps=60,frames=frames)
 print('SWEEP_DONOR',role,duration)
(P/'donors.json').write_text(json.dumps(out))
