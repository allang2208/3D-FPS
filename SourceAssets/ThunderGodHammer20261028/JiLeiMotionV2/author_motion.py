"""Visible, forward single-hand lift with a continuous native elbow plane."""
import ast,copy,json,math
from pathlib import Path
import bpy
from mathutils import Matrix,Quaternion,Vector
P=Path(__file__).resolve().parent;R=P.parents[2];OUT=P/'Export';OUT.mkdir(exist_ok=True)
FPS=240
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'JiLeiSeatV1/JiLeiMotionV1_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
rig=bpy.data.objects['SK_RusticPickaxe_Rig'];scene=bpy.context.scene
action=bpy.data.actions['A_ThunderHammer_CallCharge'];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
scene.frame_set(0);idle={b.name:b.matrix.copy() for b in rig.pose.bones}
scene.frame_set(480);old_top={b.name:b.matrix.copy() for b in rig.pose.bones}
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
local_rest={b.name:rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name] for b in rig.data.bones}
def smooth(t):
 t=max(0.,min(1.,t));return t*t*t*(10+t*(-15+6*t))
def blend(a,b,t):return Matrix.LocRotScale(a.translation.lerp(b.translation,t),a.to_quaternion().slerp(b.to_quaternion(),t),Vector((1,1,1)))
def framed(a,b):return Matrix((a,b,a.cross(b))).transposed().to_quaternion()
def project(v,axis):return (v-axis*v.dot(axis)).normalized()
def loc(p):return {b.name:p[b.parent.name].inverted()@p[b.name] if b.parent else p[b.name] for b in rig.data.bones}
idle_loc=loc(idle);hang_loc=loc(old_top)
grip=idle['WPN_root'].inverted()@idle['hand_r']
finger_names=[n for n in rest if n.startswith(('thumb','index','middle','ring','pinky'))]
spec={}
for s in ['r','l']:
 U,F,H=[n+'_'+s for n in ['upperarm','lowerarm','hand']]
 a=(rest[F].translation-rest[U].translation).normalized();b=(rest[H].translation-rest[F].translation).normalized()
 initial_axis=(idle[H].translation-idle[U].translation).normalized()
 spec[s]=dict(U=U,F=F,H=H,a=a,b=b,rn=a.cross(b).normalized(),
  l1=(rest[F].translation-rest[U].translation).length,l2=(rest[H].translation-rest[F].translation).length,
  initial_axis=initial_axis,initial_pole=project(idle[F].translation-idle[U].translation,initial_axis))

def elbow_frame(s,shoulder,hand,swivel):
 d=spec[s];v=hand.translation-shoulder;distance=v.length
 if not abs(d['l1']-d['l2'])+.001<distance<(d['l1']+d['l2'])*.97:raise RuntimeError('Unreachable authored hand '+s+' '+str(distance))
 axis=v.normalized();pole=d['initial_axis'].rotation_difference(axis)@d['initial_pole']
 pole=Quaternion(axis,swivel)@project(pole,axis)
 along=(d['l1']**2-d['l2']**2+distance**2)/(2*distance)
 elbow=shoulder+axis*along+pole*math.sqrt(max(0,d['l1']**2-along**2))
 ua=(elbow-shoulder).normalized();fa=(hand.translation-elbow).normalized();normal=ua.cross(fa).normalized()
 du=framed(ua,normal)@framed(d['a'],d['rn']).inverted();df=framed(fa,normal)@framed(d['b'],d['rn']).inverted()
 hand_delta=hand.to_quaternion()@rest[d['H']].to_quaternion().inverted();neutral=hand_delta@d['b']
 full=neutral.rotation_difference(fa)@hand_delta;dq=full@df.inverted()
 twist=(2*math.atan2(Vector((dq.x,dq.y,dq.z)).dot(fa),dq.w)+math.pi)%(2*math.pi)-math.pi
 return elbow,ua,fa,du,df,twist,neutral.angle(fa)

# A forward, slightly outboard shaft keeps the complete head below the top
# frame. Keep the accepted right grip; rotate the complete held weapon.
right_top=Vector((.32,.43,-.20))
shoulder_top={'r':Vector((.215,-.035,-.225)),'l':old_top['upperarm_l'].translation.copy()}
shaft=Vector((.10,.35,.932)).normalized()
q0=idle['WPN_root'].to_quaternion()
base=(q0@Vector((0,0,1))).rotation_difference(shaft)@q0
best=None
for roll_degree in range(-180,181,2):
 q=Quaternion(shaft,math.radians(roll_degree))@base
 w=Matrix.LocRotScale(right_top-q@grip.translation,q,Vector((1,1,1)));h=w@grip
 for swivel_degree in range(-180,181,2):
  e,ua,fa,du,df,twist,bend=elbow_frame('r',shoulder_top['r'],h,math.radians(swivel_degree))
  cost=10*bend*bend+1.2*twist*twist+.025*math.radians(swivel_degree)**2+.025*math.radians(roll_degree)**2
  cost+=100*max(0,.16-e.x)**2+40*max(0,e.z+.08)**2+120*max(0,.08-e.y)**2
  if best is None or cost<best[0]:best=(cost,w,math.radians(swivel_degree),roll_degree,math.degrees(bend),math.degrees(twist))
_,top,right_swivel,roll,bend,twist=best
left_hand_top=old_top['hand_l'].copy()
# The relaxed left pose is also solved on a continuous transported elbow
# plane; choose one final swivel, never a new minimum on each animation frame.
left_best=None
for angle in range(-160,161,2):
 e,ua,fa,du,df,tw,bn=elbow_frame('l',shoulder_top['l'],left_hand_top,math.radians(angle))
 cost=3*bn*bn+tw*tw+.03*math.radians(angle)**2+200*max(0,e.x+.16)**2
 if left_best is None or cost<left_best[0]:left_best=(cost,math.radians(angle))
left_swivel=left_best[1]

def solve(out,s,hand,shoulder,progress):
 d=spec[s];U,F,H=d['U'],d['F'],d['H']
 elbow,ua,fa,du,df,tw,bend=elbow_frame(s,shoulder,hand,(right_swivel if s=='r' else left_swivel)*progress)
 # Transport the incoming native roll, then gradually resolve the hinge.
 # This starts exactly at the accepted idle, rather than popping to a newly
 # solved elbow in the first .12 s or forcing the old idle in the last key.
 idle_ua=(idle[F].translation-idle[U].translation).normalized();idle_fa=(idle[H].translation-idle[F].translation).normalized()
 upper_from=idle_ua.rotation_difference(ua)@idle[U].to_quaternion()
 lower_from=idle_fa.rotation_difference(fa)@idle[F].to_quaternion()
 qU=upper_from.slerp(du@rest[U].to_quaternion(),progress)
 qF=lower_from.slerp(df@rest[F].to_quaternion(),progress)
 out['clavicle_'+s].translation+=shoulder-idle[U].translation
 out[U]=Matrix.LocRotScale(shoulder,qU,Vector((1,1,1)))
 out[F]=Matrix.LocRotScale(elbow,qF,Vector((1,1,1)))
 for n in ['upperarm_twist_01_'+s,'upperarm_twist_02_'+s]:
  moved=out[U]@idle[U].inverted()@idle[n];native=out[U]@rest[U].inverted()@rest[n]
  out[n]=blend(moved,native,progress)
 for n,share in [('lowerarm_twist_01_'+s,1.),('lowerarm_twist_02_'+s,.5)]:
  moved=out[F]@idle[F].inverted()@idle[n]
  position=(out[F]@rest[F].inverted()@rest[n]).translation
  native=Matrix.LocRotScale(position,Quaternion(fa,tw*share)@df@rest[n].to_quaternion(),Vector((1,1,1)))
  out[n]=blend(moved,native,progress)
 out[H]=hand
 for n in finger_names:
  if n.endswith('_'+s):out[n]=out[rig.data.bones[n].parent.name]@idle_loc[n]

def pose(charge_t,recoil=0.):
 lift=smooth((charge_t-.10)/1.50);drop=smooth((charge_t-.03)/.72)
 # Separate shaft elevation from axial roll. A direct quaternion slerp
 # between both changes sends the long head outside the upper/right frame.
 swing=Quaternion().slerp((q0@Vector((0,0,1))).rotation_difference(shaft),lift)
 axis=swing@(q0@Vector((0,0,1)))
 q=Quaternion(axis,math.radians(roll)*lift)@swing@q0
 right=idle['hand_r'].translation.lerp(right_top,lift)
 right+=Vector((-.015,.035,-.030))*math.sin(math.pi*lift)
 w=Matrix.LocRotScale(right-q@grip.translation,q,Vector((1,1,1)))
 w.translation+=Vector((0,-.018,-.015))*recoil
 left=blend(idle['hand_l'],left_hand_top,drop);left.translation.x-=.025*math.sin(math.pi*drop)
 out=copy.deepcopy(idle)
 for s,hand,progress in [('r',w@grip,lift),('l',left,drop)]:
  shoulder=idle['upperarm_'+s].translation.lerp(shoulder_top[s],progress)
  solve(out,s,hand,shoulder,progress)
 local=loc(out)
 opening=smooth((charge_t-.03)/.28)
 for n in finger_names:
  if n.endswith('_l'):local[n]=blend(idle_loc[n],hang_loc[n],opening)
 for b in rig.data.bones:out[b.name]=out[b.parent.name]@local[b.name] if b.parent else local[b.name]
 out['WPN_root']=w
 return out
charge=[pose(i/FPS) for i in range(481)]
release=[]
for i in range(round(.72*FPS)+1):
 t=i/FPS;reverse=1-smooth((t-.12)/.60)
 release.append(pose(1.60*reverse,math.sin(math.pi*min(t/.12,1))**2 if t<.12 else 0.))
charge[0]=copy.deepcopy(idle);release[0]=copy.deepcopy(charge[-1]);release[-1]=copy.deepcopy(idle)
module=ast.parse((R/'SourceAssets/SteelWarhammer20261014/SprintDragV1/author_sprint.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'apply_pose','new_action','bake'}],type_ignores=[]),'<native_baker>','exec'))
names=['A_ThunderHammer_CallCharge','A_ThunderHammer_CallRelease']
for name,rows in zip(names,[charge,release]):bake(name,rows,FPS)
rig.animation_data.action=bpy.data.actions[names[0]];rig.animation_data.action_slot=rig.animation_data.action.slots[0];scene.frame_set(480)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'JiLeiMotionV2_Editable.blend'))
(P/'motion.json').write_text(json.dumps(dict(fps=FPS,clips=names,charge_seconds=2,release_seconds=.72,right_top_cm=list(right_top*100),
 shaft=list(shaft),right_swivel_deg=math.degrees(right_swivel),weapon_roll_deg=roll,target_wrist_bend_deg=bend,target_forearm_twist_deg=twist,
 left_swivel_deg=math.degrees(left_swivel),right_grip='unchanged relative to hammer',runtime_tested=False),indent=2))
print('JI_LEI_V2_AUTHORED '+json.dumps(dict(bend=bend,twist=twist,swivel=math.degrees(right_swivel),roll=roll)),flush=True)
