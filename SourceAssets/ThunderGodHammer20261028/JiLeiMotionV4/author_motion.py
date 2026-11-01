"""Elbow-down single-hand lift: the supporting arm determines the held hammer."""
import ast,copy,json,math
from pathlib import Path
import bpy
from mathutils import Matrix,Quaternion,Vector
P=Path(__file__).resolve().parent;R=P.parents[2];OUT=P/'Export';OUT.mkdir(exist_ok=True)
FPS=240
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'JiLeiMotionV3/JiLeiMotionV3_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
rig=bpy.data.objects['SK_RusticPickaxe_Rig'];scene=bpy.context.scene
old={}
for kind in ['Charge','Release']:
 action=bpy.data.actions['A_ThunderHammer_Call'+kind];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
 rows=[]
 for i in range(round(action.frame_range[1])+1):
  scene.frame_set(i);rows.append({b.name:b.matrix.copy() for b in rig.pose.bones})
 old[kind]=rows
idle=old['Charge'][0];rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
local_rest={b.name:rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name] for b in rig.data.bones}
U,F,H='upperarm_r','lowerarm_r','hand_r'
def smooth(t):
 t=max(0.,min(1.,t));return t*t*t*(10+t*(-15+6*t))
def project(v,a):return (v-a*v.dot(a)).normalized()
def frame(a,b):return Matrix((a,b,a.cross(b))).transposed().to_quaternion()
def blend(a,b,t):return Matrix.LocRotScale(a.translation.lerp(b.translation,t),a.to_quaternion().slerp(b.to_quaternion(),t),Vector((1,1,1)))
def axial(q,axis):return (2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w)+math.pi)%(2*math.pi)-math.pi
a=(rest[F].translation-rest[U].translation).normalized();b=(rest[H].translation-rest[F].translation).normalized();rn=a.cross(b).normalized()
l1=(rest[F].translation-rest[U].translation).length;l2=(rest[H].translation-rest[F].translation).length
s0=idle[U].translation;h0=idle[H].translation;axis0=(h0-s0).normalized();pole0=project(idle[F].translation-s0,axis0)
grip=idle['WPN_root'].inverted()@idle[H]
finger_names=[n for n in rest if n.startswith(('thumb','index','middle','ring','pinky')) and n.endswith('_r')]
idle_local={n:idle[rig.data.bones[n].parent.name].inverted()@idle[n] for n in rest if rig.data.bones[n].parent}

def support(s,h,pole):
 axis=(h-s).normalized();d=(h-s).length
 if not abs(l1-l2)+.001<d<(l1+l2)*.97:raise RuntimeError('Unreachable support arm')
 along=(l1*l1-l2*l2+d*d)/(2*d)
 e=s+axis*along+project(pole,axis)*math.sqrt(l1*l1-along*along)
 ua=(e-s).normalized();fa=(h-e).normalized();normal=ua.cross(fa).normalized()
 du=frame(ua,normal)@frame(a,rn).inverted();df=frame(fa,normal)@frame(b,rn).inverted()
 return e,ua,fa,normal,du@rest[U].to_quaternion(),df@rest[F].to_quaternion()

# Do not trade anatomical elbow placement for a lower wrist-only objective.
# The elbow stays below the wrist, outside the torso and in front of the shoulder.
best=None;design_options=[]
for depth in [.46,.50,.54]:
 for height in [-.14,-.12,-.10,-.075]:
  for outer,pole_z,shoulder_z in [(x,z,s) for x in [.65,1.] for z in [-.1,.25,.6] for s in [-.30,-.34]]:
   shoulder=Vector((.26,.055,shoulder_z));hand=Vector((.32,depth,height));pole=Vector((outer,0,pole_z)).normalized()
   try:e,ua,fa,n,qu,qf=support(shoulder,hand,pole)
   except RuntimeError:continue
   if e.x<hand.x-.01 or e.x>.48 or e.z>hand.z-.03 or e.z<hand.z-.12:continue
   for roll_deg in range(-120,121,5):
    for bend_deg in [0,10,20,25,30]:
     for bend_axis_deg in range(0,360,30):
      ba=n*math.cos(math.radians(bend_axis_deg))+fa.cross(n)*math.sin(math.radians(bend_axis_deg))
      qh=Quaternion(ba,math.radians(bend_deg))@Quaternion(fa,math.radians(roll_deg))@qf@rest[F].to_quaternion().inverted()@rest[H].to_quaternion()
      qw=qh@grip.to_quaternion().inverted();w=Matrix.LocRotScale(hand-qw@grip.translation,qw,Vector((1,1,1)))
      shaft=qw@Vector((0,0,1));head=w@Vector((0,0,.916))
      cost=18*(shaft-Vector((.18,.38,.907)).normalized()).length_squared+2*math.radians(bend_deg)**2+.15*math.radians(roll_deg)**2
      design_options.append({'cost':cost,'shaft':list(shaft),'head':list(head),'elbow':list(e),'hand':list(hand),'roll':roll_deg,'bend':bend_deg})
      if shaft.z<.72 or shaft.y<.05 or shaft.x<-.18:continue
      if head.z+.07>head.y*.767*.92 or head.x+.14>head.y*.90:continue
      cost+=10*(hand-Vector((.32,.46,-.075))).length_squared
      if best is None or cost<best[0]:best=(cost,shoulder,hand,pole,qh,shaft,roll_deg,bend_deg,e)
if best is None:
 (P/'design-options.json').write_text(json.dumps(sorted(design_options,key=lambda x:x['cost'])[:10],indent=2))
 raise RuntimeError('No elbow-down supported lift candidate; see design-options.json')
_,s1,h1,pole1,qh1,shaft,roll,bend,e1=best
# Give the long head a little more depth without changing the solved arm bend.
for point in (s1,h1,e1):point.y+=.05
e,ua0,fa0,n,qu0,qf0=support(s0,h0,pole0)
u_roll0=axial(idle[U].to_quaternion()@qu0.inverted(),ua0)
f_roll0=axial(idle[F].to_quaternion()@qf0.inverted(),fa0)
hand_rel0=qf0.inverted()@idle[H].to_quaternion()
*_,qf1=support(s1,h1,pole1)
hand_rel1=qf1.inverted()@qh1
right_bones=[n for n in rest if n.endswith('_r') and n.startswith(('clavicle','upperarm','lowerarm','hand','thumb','index','middle','ring','pinky'))]

def author(t,recoil=0.):
 lift=smooth((t-.14)/1.20)
 out=copy.deepcopy(old['Charge'][min(480,round(t*FPS))])
 shoulder=s0.lerp(s1,lift);hand=h0.lerp(h1,lift)
 hand+=Vector((.018,.012,.025))*math.sin(math.pi*lift)+Vector((0,-.014,-.012))*recoil
 axis=(hand-shoulder).normalized()
 incoming=axis0.rotation_difference(axis)@pole0
 ending=project(pole1,axis)
 pole=project(incoming.lerp(ending,lift),axis)
 e,ua,fa,n,qu,qf=support(shoulder,hand,pole)
 qu=Quaternion(ua,u_roll0*(1-lift))@qu
 raw_qf=qf.copy();qf=Quaternion(fa,f_roll0*(1-lift))@qf
 qh=raw_qf@hand_rel0.slerp(hand_rel1,lift)
 out['clavicle_r']=idle['clavicle_r'].copy();out['clavicle_r'].translation+=shoulder-s0
 out[U]=Matrix.LocRotScale(shoulder,qu,Vector((1,1,1)))
 out[F]=Matrix.LocRotScale(e,qf,Vector((1,1,1)))
 out[H]=Matrix.LocRotScale(hand,qh,Vector((1,1,1)))
 for name in ['upperarm_twist_01_r','upperarm_twist_02_r']:
  moved=out[U]@idle[U].inverted()@idle[name];native=out[U]@rest[U].inverted()@rest[name]
  out[name]=blend(moved,native,lift)
 hand_delta=qh@rest[H].to_quaternion().inverted();neutral=hand_delta@b
 full=neutral.rotation_difference(fa)@hand_delta;df=qf@rest[F].to_quaternion().inverted()
 tw=axial(full@df.inverted(),fa)
 for name,share in [('lowerarm_twist_01_r',1.),('lowerarm_twist_02_r',.5)]:
  moved=out[F]@idle[F].inverted()@idle[name];position=(out[F]@rest[F].inverted()@rest[name]).translation
  native=Matrix.LocRotScale(position,Quaternion(fa,tw*share)@df@rest[name].to_quaternion(),Vector((1,1,1)))
  out[name]=blend(moved,native,lift)
 for name in finger_names:out[name]=out[rig.data.bones[name].parent.name]@idle_local[name]
 out['WPN_root']=out[H]@grip.inverted()
 return out
charge=[author(i/FPS) for i in range(481)]
release=[]
for i in range(round(.72*FPS)+1):
 t=i/FPS;reverse=1-smooth((t-.12)/.60)
 p=author(1.60*reverse,math.sin(math.pi*min(t/.12,1))**2 if t<.12 else 0.)
 for n in rest:
  if n.endswith('_l'):p[n]=old['Release'][i][n].copy()
 release.append(p)
charge[0]=copy.deepcopy(idle);release[0]=copy.deepcopy(charge[-1]);release[-1]=copy.deepcopy(idle)
module=ast.parse((R/'SourceAssets/SteelWarhammer20261014/SprintDragV1/author_sprint.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'apply_pose','new_action','bake'}],type_ignores=[]),'<native_baker>','exec'))
names=['A_ThunderHammer_CallCharge','A_ThunderHammer_CallRelease']
for name,rows in zip(names,[charge,release]):bake(name,rows,FPS)
rig.animation_data.action=bpy.data.actions[names[0]];rig.animation_data.action_slot=rig.animation_data.action.slots[0];scene.frame_set(480)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'JiLeiMotionV4_Editable.blend'))
record={'fps':FPS,'clips':names,'charge_seconds':2,'release_seconds':.72,'shoulder':list(s1),'elbow':list(e1),'wrist':list(h1),'shaft':list(shaft),'roll_degrees':roll,'bend_degrees':bend,'gameplay_run':False}
(P/'motion.json').write_text(json.dumps(record,indent=2))
print('JI_LEI_V4_AUTHORED',json.dumps(record),flush=True)
