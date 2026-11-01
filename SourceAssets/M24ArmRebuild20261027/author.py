"""Rebuild both native arm chains for every M24 role, retaining weapon/event tracks."""
import bpy,json,math,ast,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).resolve().parent;X=O/'Exports';X.mkdir(exist_ok=True)
input=json.loads((O/'source_before.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24MotionPolish20261027/M24_MotionPolish_Editable.blend'),use_scripts=False)
s=bpy.context.scene;r=bpy.data.objects['M24_V9_Rig'];skin=bpy.data.objects['M24_V9_BareArms']
rest={n:Matrix(m) for n,m in input['rest'].items()};parents=input['parents']
local_rest={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
clips={role:[{n:Matrix(m) for n,m in row.items()} for row in data['poses']] for role,data in input['clips'].items()}
idle=clips['aim'][0];C=Matrix(json.loads((O.parent/'M24Hold20261027/hip-calibration.json').read_text())['hip_transform'])@Matrix.Diagonal((100,-100,100,1))
# The donor's left shoulder was displaced toward the camera center. Place the
# support shoulder laterally, keeping the source weapon and wrist contacts fixed.
shoulder_offsets={'l':C.inverted().to_3x3()@Vector((-3,-10,-1)),'r':Vector((0,0,0))}
def clone(row):return {n:m.copy() for n,m in row.items()}
def under(n,p):
 while n:
  if n==p:return True
  n=parents.get(n)
 return False
def ease(x):
 x=max(0,min(1,x));return x*x*x*(x*(6*x-15)+10)
def frame(x,z):
 x=x.normalized();z=(z-x*z.dot(x)).normalized();return Matrix((x,z.cross(x).normalized(),z)).transposed()
def twist(q,axis):
 if q.w<0:q=-q
 return 2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w)
def solve_frames(row,side,phi=0.,hand=None):
 u,l,h=[n+'_'+side for n in ('upperarm','lowerarm','hand')]
 hand=row[h] if hand is None else hand
 S=row[u].translation+shoulder_offsets[side];T=hand.translation;RU=rest[l].translation-rest[u].translation;RL=rest[h].translation-rest[l].translation
 a,b=RU.length,RL.length;axis=T-S
 if axis.length>.955*(a+b):S+=axis.normalized()*(axis.length-.955*(a+b))
 axis=T-S;d=max(axis.length,abs(a-b)+1.e-6);axis.normalize()
 pole=row[l].translation-S;pole=(pole-axis*pole.dot(axis)).normalized();pole=Quaternion(axis,math.radians(phi))@pole
 along=(a*a-b*b+d*d)/(2*d);E=S+axis*along+pole*math.sqrt(max(0,a*a-along*along))
 U=E-S;L=T-E;N=U.cross(L).normalized();RN=RU.cross(RL).normalized()
 uq=(frame(U,N)@frame(RU,RN).transposed()).to_quaternion()@rest[u].to_quaternion()
 lq=(frame(L,N)@frame(RL,RN).transposed()).to_quaternion()@rest[l].to_quaternion()
 ax=rest[l].to_quaternion().inverted()@RL.normalized()
 rel=(lq.inverted()@hand.to_quaternion())@(rest[l].to_quaternion().inverted()@rest[h].to_quaternion()).inverted()
 roll=twist(rel,ax);swing=(rel@Quaternion(ax,-roll)).angle
 if swing>math.pi:swing=2*math.pi-swing
 return S,E,uq,lq,roll,math.degrees(swing),math.degrees(U.angle(L))
def cost(row,side,phi,hand=None):
 S,E,uq,lq,roll,wrist,bend=solve_frames(row,side,phi,hand)
 # Bone-frame limits, not medical angles. Retain the source elbow neighborhood.
 value=(max(0,abs(math.degrees(roll))-95)/12)**2+(max(0,wrist-32)/9)**2+(phi/50)**2*.4
 p=C@E;side_sign=-1 if side=='l' else 1
 value+=max(0,-side_sign*p.y/10)**2*.3
 # Keep the elbow below the view axis and out of the near-camera region.
 value+=max(0,(p.z+5)/10)**2+max(0,(16-p.length)/4)**2
 return value
def apply_arm(row,side,phi):
 old=clone(row);u,l,h=[n+'_'+side for n in ('upperarm','lowerarm','hand')]
 S,E,uq,lq,roll,wrist,bend=solve_frames(row,side,phi)
 U=Matrix.LocRotScale(S,uq,Vector((1,1,1)));L=Matrix.LocRotScale(E,lq,Vector((1,1,1)))
 for n in row:
  if under(n,h):continue
  if under(n,l):row[n]=L@rest[l].inverted()@rest[n]
  elif under(n,u):row[n]=U@rest[u].inverted()@rest[n]
 # Keep shoulder skin and upper-arm helpers on the same deformation frame.
 cn='clavicle_'+side;row[cn]=U@rest[u].inverted()@rest[cn]
 ax=rest[l].to_quaternion().inverted()@(rest[h].translation-rest[l].translation).normalized()
 for i,share in ((1,1.),(2,.5)):
  n=f'lowerarm_twist_{i:02d}_{side}';lr=local_rest[n]
  row[n]=L@Matrix.LocRotScale(lr.translation,Quaternion(ax,roll*share)@lr.to_quaternion(),Vector((1,1,1)))
 return {'pole':phi,'roll':math.degrees(roll),'wrist':wrist,'bend':bend}

# A single bolt-local contact pose, rotated around the actual cylindrical knob
# to keep the forearm away from its 180-degree branch throughout manipulation.
old_report=json.loads((O.parent/'M24MotionPolish20261027/authoring.json').read_text())
anchor=Matrix(old_report['bolt_contact']['hand_anchor']);knob=Vector(old_report['bolt_contact']['knob_local'])
fit=json.loads((O/'bolt_grip_fit.json').read_text())
anchor.translation=knob-anchor.to_quaternion()@Vector(fit['parameters'][:3])
axis=rest['WPN_BoltHandle'].to_quaternion().inverted()@Vector((1,0,0))
contact_rows=[clips[role][f+shift] for role,shift in [('fire',0),('cycle',4),('reload_empty',52)] for f in range(17,40,2)]
best=None
for angle in range(-180,181,10):
 a=Matrix.Translation(knob)@Quaternion(axis,math.radians(angle)).to_matrix().to_4x4()@Matrix.Translation(-knob)@anchor
 scores=[]
 for row in contact_rows:
  hand=row['WPN_BoltHandle']@a;scores.append(min(cost(row,'r',p,hand) for p in range(-105,106,5)))
 v=max(scores)+float(np.mean(scores))+(angle/180)**2*.08
 if best is None or v<best[0]:best=(v,angle,a)
anchor=best[2];print('BOLT_ORIENTATION',best[:2],flush=True)
grip={n:Matrix(m) for n,m in fit['local_grip'].items()}
anchor.translation=knob-anchor.to_quaternion()@Vector(fit['parameters'][:3])
right_digits=[n for n in rest if under(n,'hand_r') and n!='hand_r']
hold_local={n:idle[parents[n]].inverted()@idle[n] for n in right_digits}
for n in right_digits:
 if 'metacarpal' in n:continue
 d=(local_rest[n].inverted()@hold_local[n]).to_quaternion();swing,_=d.to_swing_twist('X')
 if n.endswith('_03_r'):
  # Donor terminal axes differ from V9; do not carry the old half-turn into a fingertip.
  finger=n.split('_')[0]
  if finger=='thumb':swing=Quaternion((0,0,1),math.radians(18))
  else:
   pn=-(rest['index_01_r'].translation-rest['pinky_01_r'].translation).cross(rest['middle_01_r'].translation-rest['hand_r'].translation).normalized()
   hinge=(rest[finger+'_02_r'].translation-rest[finger+'_01_r'].translation).cross(pn).normalized()
   v=rest[n].to_quaternion().inverted()@hinge;v.x=0;v.normalize();swing=Quaternion(v,math.radians(23))
 hold_local[n]=local_rest[n]@swing.to_matrix().to_4x4()
right_hold=idle['WPN_root'].inverted()@idle['hand_r']
contact_states={}
def anatomical_blend(row,base,target,w,desired,phi):
 if w<=0 or w>=1:return base if w<=0 else target
 qmid=solve_frames(row,'r',phi,desired)[3]
 ax=rest['lowerarm_r'].to_quaternion().inverted()@(rest['hand_r'].translation-rest['lowerarm_r'].translation).normalized()
 ref=rest['lowerarm_r'].to_quaternion().inverted()@rest['hand_r'].to_quaternion()
 relative=[(qmid.inverted()@h.to_quaternion())@ref.inverted() for h in (base,target)]
 original_angles=[twist(q,ax) for q in relative]
 swings=[q@Quaternion(ax,-a) for q,a in zip(relative,original_angles)]
 angles=original_angles
 # Both endpoints live in this exact evaluated forearm frame. Using two
 # different endpoint pole frames introduced a half-turn immediately before contact.
 a=angles[0]*(1-w)+angles[1]*w
 a=max(math.radians(-115),min(math.radians(115),a))
 q=qmid@(swings[0].slerp(swings[1],w)@Quaternion(ax,a))@ref
 return Matrix.LocRotScale(desired.translation,q,Vector((1,1,1)))
for role,rows in clips.items():
 shift={'fire':0,'cycle':4,'reload_empty':52,'reload_empty_mag10':52}.get(role)
 for f,row in enumerate(rows):
  w=0.
  if shift is not None:
   t=f-shift;w=ease((t-8)/9)*(1-ease((t-40)/10))
   base=row['WPN_root']@right_hold;target=row['WPN_BoltHandle']@anchor
   # Work in the moving rifle frame; use a lateral clearance arc in approach/release.
   desired=base.lerp(target,w)
   arc=row['WPN_root'].to_quaternion()@Vector((.022*math.sin(math.pi*w),-.01*math.sin(math.pi*w),.012*math.sin(math.pi*w)))
   desired.translation+=arc
   contact_states[(role,f)]=(base,target,w)
   delta=desired@row['hand_r'].inverted()
   for n in row:
    if under(n,'hand_r'):row[n]=delta@row[n]
  for n in right_digits:
   a=hold_local[n];b=grip[n];p,q,sc=a.decompose()
   row[n]=row[parents[n]]@Matrix.LocRotScale(p,q.slerp(b.to_quaternion(),w),sc)

report={'clips':{},'fps':30,'source':'M24_MotionPolish_Editable.blend, source_before.json','runtime_tested':False,
        'bolt_rotation_degrees':best[1],'bolt_anchor':[list(x) for x in anchor],'metrics':{}}
# Dynamic programming picks one continuous elbow-circle path instead of per-frame
# branch switching. Identical boundary poses keep their deterministic best pole.
phis=np.arange(-105,106,3,dtype=float)
for role,rows in clips.items():
 report['metrics'][role]={}
 for side in ('l','r'):
  costs=np.array([[cost(row,side,float(p)) for p in phis] for row in rows]);back=[];total=costs[0].copy()
  start=int(total.argmin());total[:]=1.e9;total[start]=costs[0,start]
  transition=((phis[:,None]-phis[None,:])/7)**2*.6
  for k in range(1,len(rows)):
   d=total[:,None]+transition;idx=d.argmin(0);back.append(idx);total=costs[k]+d[idx,np.arange(len(phis))]
  index=int(costs[-1].argmin());path=[index]
  for b in reversed(back):index=int(b[index]);path.append(index)
  chosen=phis[np.array(path[::-1])]
  # Smooth quantized authoring samples, pin both ends so all returns match idle.
  smooth=chosen.copy()
  for k in range(1,len(rows)-1):smooth[k]=(chosen[k-1]+2*chosen[k]+chosen[k+1])/4
  metrics=[]
  for f,(row,p) in enumerate(zip(rows,smooth)):
   if side=='r' and (role,f) in contact_states:
    base,target,w=contact_states[(role,f)]
    if 0<w<1:
     desired=anatomical_blend(row,base,target,w,row['hand_r'],float(p));delta=desired@row['hand_r'].inverted()
     for n in row:
      if under(n,'hand_r'):row[n]=delta@row[n]
   metrics.append(apply_arm(row,side,float(p)))
  report['metrics'][role][side]=metrics
 print(role,{side:{k:round(max(abs(v[k]) for v in report['metrics'][role][side]),1) for k in ('roll','wrist','pole')} for side in ('l','r')},flush=True)

tree=ast.parse((O.parent/'M24Hold20261027/author_hold.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='bake')
node.body=[n for n in node.body if not(isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='twists')]
exec(compile(ast.unparse(node),'native_bake','exec'))
owned=[n for n in rest if any(under(n,'clavicle_'+side) for side in ('l','r'))]
for role,rows in clips.items():
 old=bpy.data.actions['A_M24_'+role];r.animation_data.action=None;bpy.data.actions.remove(old);bake(role,rows)
 bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
 path=X/('A_M24_'+role+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
 report['clips'][role].update(file=str(path),owned_bones=owned)
r.animation_data.action=bpy.data.actions['A_M24_aim'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(0)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_ArmRebuild_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M24_BASE_ARMS_REBUILT',len(clips),flush=True)
