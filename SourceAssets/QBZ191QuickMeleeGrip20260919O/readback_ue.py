"""Read imported QBZ grip constraints in the actual mesh's raw/compressed pose."""
import unreal as u,json,math
from pathlib import Path
P=Path(__file__).parent
def xyz(v):return (v.x,v.y,v.z)
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def length(a):return math.sqrt(dot(a,a))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def rotate(q,v,inverse=False):
 a=xyz(q);a=tuple(-x for x in a) if inverse else a;c=cross(a,v);t=cross(a,tuple(c[i]+q.w*v[i] for i in range(3)))
 return tuple(v[i]+2*t[i] for i in range(3))
def angle(a,b):return math.degrees(math.acos(max(-1,min(1,dot(a,b)/(length(a)*length(b))))))
def quat(q):return (q.x,q.y,q.z,q.w)
def qdelta(a,b):return math.degrees(2*math.acos(min(1,abs(dot(a,b))/(length(a)*length(b)))))
def mul(a,b):
 c=cross(a[:3],b[:3]);return tuple(a[3]*b[i]+b[3]*a[i]+c[i] for i in range(3))+(a[3]*b[3]-dot(a[:3],b[:3]),)
def relative_q(g,h):return mul((-g.x,-g.y,-g.z,g.w),quat(h))
mesh=u.load_asset('/Game/Weapons/QBZ191/RearGrip20260913/SK_QBZ191_Manny');report={}
for profile in ('Base','Angled','Vertical','Canted','Prism'):
 clip=u.load_asset(f'/Game/Weapons/RifleQuickMelee20260919/QBZ191/{profile}/A_QBZ191_QuickCombat_{profile}');rows={}
 idlepath='/Game/Weapons/QBZ191/Refined20260913/Animations/'+profile.lower()+'/A_QBZ191_'+('' if profile=='Base' else profile.lower()+'_')+'idle'
 idle=u.load_asset(idlepath)
 for label,typ in (('RAW',u.AnimDataEvalType.RAW),('COMPRESSED',u.AnimDataEvalType.COMPRESSED)):
  opts=u.AnimPoseEvaluationOptions();opts.evaluation_type=typ;opts.optional_skeletal_mesh=mesh
  # Raw FBX tracks are already in author space. Retargeting them again moves
  # private weapon bones; runtime compressed tracks require the normal retarget.
  opts.should_retarget=(label=='COMPRESSED')
  baseline_options=u.AnimPoseEvaluationOptions();baseline_options.evaluation_type=typ
  baseline_options.optional_skeletal_mesh=mesh;baseline_options.should_retarget=(label=='COMPRESSED')
  base=u.AnimPoseExtensions.get_anim_pose_at_time(idle,0,baseline_options)
  def bone(p,n,space=u.AnimPoseSpaces.WORLD):return u.AnimPoseExtensions.get_bone_pose(p,n,space)
  g0,h0=bone(base,'WPN_root'),bone(base,'hand_r');position0=rotate(g0.rotation,sub(xyz(h0.translation),xyz(g0.translation)),True)
  orientation0=relative_q(g0.rotation,h0.rotation)
  fingers=[n for n in u.AnimPoseExtensions.get_bone_names(base) if str(n).endswith('_r') and str(n).startswith(('thumb','index','middle','ring','pinky'))]
  fingers0={str(n):bone(base,n,u.AnimPoseSpaces.LOCAL) for n in fingers}
  samples=[]
  for frame in range(865):
   pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,frame/960,opts)
   g,h,e=bone(pose,'WPN_root'),bone(pose,'hand_r'),bone(pose,'lowerarm_r')
   pos=rotate(g.rotation,sub(xyz(h.translation),xyz(g.translation)),True)
   hr=u.AnimPoseExtensions.get_ref_bone_pose(pose,'hand_r',u.AnimPoseSpaces.WORLD)
   er=u.AnimPoseExtensions.get_ref_bone_pose(pose,'lowerarm_r',u.AnimPoseSpaces.WORLD)
   desired=rotate(h.rotation,rotate(hr.rotation,sub(xyz(hr.translation),xyz(er.translation)),True))
   fp,fr=0.,0.
   for n in fingers:
    now=bone(pose,n,u.AnimPoseSpaces.LOCAL);old=fingers0[str(n)]
    fp=max(fp,length(sub(xyz(now.translation),xyz(old.translation)))*10)
    fr=max(fr,qdelta(quat(now.rotation),quat(old.rotation)))
   samples.append({'time':frame/960,'grip_shift_mm':length(sub(pos,position0))*10,
    'grip_rotation_deg':qdelta(relative_q(g.rotation,h.rotation),orientation0),
    'finger_local_position_mm':fp,'finger_local_rotation_deg':fr,
    'wrist_bend_deg':angle(sub(xyz(h.translation),xyz(e.translation)),desired),'wrist':xyz(h.translation)})
  rows[label]={'maxima':{k:max(s[k] for s in samples) for k in samples[0] if k not in ('time','wrist')},'samples':samples}
 legacy_opts=u.AnimPoseEvaluationOptions();legacy_opts.evaluation_type=u.AnimDataEvalType.RAW;legacy_opts.optional_skeletal_mesh=mesh;legacy_opts.should_retarget=True
 legacy=u.AnimPoseExtensions.get_anim_pose_at_time(idle,0,legacy_opts)
 lg,lh=bone(legacy,'WPN_root'),bone(legacy,'hand_r')
 legacy_gap=length(sub(rotate(lg.rotation,sub(xyz(lh.translation),xyz(lg.translation)),True),position0))*10
 report[profile]={'mesh':mesh.get_path_name(),'clip':clip.get_path_name(),'length':clip.get_play_length(),'idle':idlepath,
  'baseline_evaluation':'RAW no retarget; COMPRESSED runtime retarget; same mode for target and idle',
  'legacy_idle_raw_double_retarget_vs_compressed_grip_mm':legacy_gap,'poses':rows}
 u.log('QBZ_O_UE '+profile+' '+json.dumps({k:v['maxima'] for k,v in rows.items()}))
(P/'ue_readback.json').write_text(json.dumps(report,indent=2));u.log('QBZ_O_READBACK_COMPLETE')
