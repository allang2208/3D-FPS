"""Keep M870 cartridge contact; repair wrist support using native S90 stations."""
import bpy,ast,json,math,sys,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;S=O.parent;BASE=S/'M870Tactical20261015';X=O/'Exports';(X/'Animations').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(S/'M870Super90Sprint20261016/M870_Super90Sprint_Editable.blend'),use_scripts=False)
r=bpy.data.objects['SK_Super90'];s=bpy.context.scene;I=Matrix.Identity(4)
rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
local_rest={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
rf=rest['hand_r'].translation-rest['lowerarm_r'].translation
ru=rest['lowerarm_r'].translation-rest['upperarm_r'].translation
L1,L2=ru.length,rf.length
def under(n,root):
 while n:
  if n==root:return True
  n=parents.get(n)
 return False
handbones=[n for n in rest if under(n,'hand_r')]
def ease(x):
 x=max(0,min(1,x));return x*x*x*(10+x*(-15+6*x))
def basis(axis,normal):
 x=axis.normalized();z=(normal-x*normal.dot(x)).normalized()
 return Matrix((x,z.cross(x),z)).transposed()
def qslerp(a,b,w):
 if a.dot(b)<0:b=-b
 return a.slerp(b,w)
# Reuse the established native Super90 R9 anatomical hinge frame. This is
# binding calibration, not the rejected per-finger or mesh-warp approach.
V=json.loads((S/'Super90QuickMelee20261008/LeftArmR5/v7_skin_basis.json').read_text())
vr={n:Matrix(m) for n,m in V['rest'].items()}
warp=json.loads((S/'BenelliM4Super9020261006/authoring.json').read_text())['v7_to_native_warp']
vh=(vr['lowerarm_r'].translation-vr['upperarm_r'].translation).cross(vr['hand_r'].translation-vr['lowerarm_r'].translation).normalized()
FF=basis(rf,Matrix(warp['lowerarm_r']).to_3x3()@vh)
FU=basis(ru,Matrix(warp['upperarm_r']).to_3x3()@vh)
stations=('lowerarm_r','lowerarm_aux_r','lowerarm_twist_02_r','lowerarm_twist_01_r')
UC=S/'M870UrbanAnimations20261015';sys.path.insert(0,str(UC))
from read_inputs import smd
uc=smd(UC/'Original/870/anims/reloadinsert.smd')['rows'];prefix='ValveBiped.Bip01_R_'
def palm_frame(p,source=False):
 hand=prefix+'Hand' if source else 'hand_r';middle=prefix+'Finger2' if source else 'middle_01_r'
 index=prefix+'Finger1' if source else 'index_01_r';pinky=prefix+'Finger4' if source else 'pinky_01_r'
 forward=(p[middle].translation-p[hand].translation).normalized();across=(p[index].translation-p[pinky].translation).normalized()
 normal=across.cross(forward).normalized()
 return Matrix((forward.cross(normal).normalized(),forward,normal)).transposed().to_quaternion()
native_palm=palm_frame(rest)
def donor_arm(f):
 if f<18:phase=0.
 elif f>=360:phase=26.
 else:
  index=0 if f<60 else min(6,1+(f-60)//50);start=18 if index==0 else 60+(index-1)*50;contact=44+index*50;end=60+index*50
  phase=12*(f-start)/(contact-start) if f<=contact else 12+14*(f-contact)/(end-contact)
 phase=max(0,min(26,phase));a=int(phase);t=phase-a
 def values(p):
  palm=palm_frame(p,True)
  return palm.inverted()@(p[prefix+'Hand'].translation-p[prefix+'Forearm'].translation).normalized(),palm.inverted()@(p[prefix+'Forearm'].translation-p[prefix+'UpperArm'].translation).normalized()
 va=values(uc[a]);vb=values(uc[min(a+1,26)])
 return tuple(a.lerp(b,t).normalized() for a,b in zip(va,vb))
def native_digits(row,w):
 """Anatomical hinge planes remove imported axial finger roll, not curl."""
 carry=row['hand_r'].to_quaternion()@rest['hand_r'].to_quaternion().inverted()
 for digit in ('thumb','index','middle','ring','pinky'):
  ns=[f'{digit}_{i:02d}_r' for i in (1,2,3)]
  b0=rest[ns[1]].translation-rest[ns[0]].translation;b1=rest[ns[2]].translation-rest[ns[1]].translation
  a0=row[ns[1]].translation-row[ns[0]].translation;a1=row[ns[2]].translation-row[ns[1]].translation
  normal=b0.cross(b1)
  if normal.length<1.e-6:normal=rest['index_01_r'].translation-rest['pinky_01_r'].translation
  normal.normalize();posed=a0.cross(a1)
  if posed.length<1.e-6:posed=carry@normal
  posed.normalize()
  if posed.dot(carry@normal)<0:posed=-posed
  for j,n in enumerate(ns):
   native=b0 if j==0 else b1
   axis=a0 if j==0 else a1 if j==1 else (row[n]@rest[n].inverted()).to_quaternion()@native
   target=(basis(axis,posed)@basis(native,normal).inverted()@rest[n].to_3x3()).to_quaternion()
   old=row[n];row[n]=Matrix.LocRotScale(old.translation,qslerp(old.to_quaternion(),target,w),Vector((1,1,1)))
def smooth_release(rows):
 """The inherited return jumps 126 mm at frame 58. After the insertion event,
 return over the complete sixteen-frame release interval with a compact arc."""
 out=[{n:m.copy() for n,m in row.items()} for row in rows]
 for contact in range(44,345,50):
  a,b,c=contact,contact+8,contact+16
  if c>=len(rows):continue
  hp=[rows[k]['hand_r'].translation for k in (a,b,c)]
  direction=(hp[2]-hp[0]).normalized();arc=hp[1]-(hp[0]+hp[2])*.5
  arc-=direction*arc.dot(direction)
  if arc.length>.025:arc*=.025/arc.length
  for f in range(a+1,c):
   segment=0 if f<=b else 1;lo,hi=(a,b) if segment==0 else (b,c);t=(f-lo)/(hi-lo);dt=hi-lo
   progress=(f-a)/(c-a);pos=hp[0].lerp(hp[2],ease(progress))+arc*(math.sin(math.pi*progress)**2)
   qa=rows[a]['hand_r'].to_quaternion();qb=rows[c]['hand_r'].to_quaternion()
   out[f]['hand_r']=Matrix.LocRotScale(pos,qslerp(qa,qb,ease(progress)),Vector((1,1,1)))
   for n in handbones:
    if n=='hand_r':continue
    parent=parents[n];la=rows[a][parent].inverted()@rows[a][n];lb=rows[c][parent].inverted()@rows[c][n]
    held_rotation=qslerp(la.to_quaternion(),lb.to_quaternion(),ease(progress))
    released=qslerp(held_rotation,local_rest[n].to_quaternion(),.35*math.sin(math.pi*progress)**2)
    out[f][n]=out[f][parent]@Matrix.LocRotScale(local_rest[n].translation,released,Vector((1,1,1)))
 return out
def geometry(p,w,f):
 shoulder=p['upperarm_r'].translation;elbow=p['lowerarm_r'].translation;hand=p['hand_r'].translation
 hd=p['hand_r'].to_quaternion()@rest['hand_r'].to_quaternion().inverted()
 original=(hand-elbow).normalized();palm_axis=(hd@rf).normalized();angle=palm_axis.angle(original)
 # Reuse the source loading arm in the complete anatomical palm frame.
 # The old idle-grip correction changed palm orientation without carrying
 # the source elbow, causing 127-degree wrist bends. No hand IK is added.
 source_fore,source_upper=donor_arm(f);carry=hd@native_palm
 target=(carry@source_fore).normalized()
 forward=qslerp(Quaternion(),original.rotation_difference(target),w)@original
 e=hand-forward*L2
 original_upper=(elbow-shoulder).normalized();desired_upper=(carry@source_upper).normalized()
 upper=qslerp(Quaternion(),original_upper.rotation_difference(desired_upper),w)@original_upper
 a=e-upper*L1
 hinge=(e-a).cross(hand-e)
 if hinge.length<1.e-7:hinge=hd@(FF@Vector((0,0,1)))
 neutral=basis(hand-e,hinge)@FF.inverted()
 distal=palm_axis.rotation_difference(forward).to_matrix()@hd.to_matrix()
 delta=(distal@neutral.inverted()).to_quaternion()
 if delta.w<0:delta=-delta
 axis=forward.normalized()
 roll=2*math.atan2(Vector((delta.x,delta.y,delta.z)).dot(axis),delta.w)
 return a,e,hand,neutral,roll
tree=ast.parse((BASE/'author_m870.py').read_text());authored={}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('select','bake')],type_ignores=[]),str(BASE/'author_m870.py'),'exec'))
inputs=json.loads((S/'M870ReloadContact20261016/authoring.json').read_text())['clips'];recipes={}
for role,entry in inputs.items():
 action=bpy.data.actions[entry['action']];r.animation_data.action=action;r.animation_data.action_slot=action.slots[0]
 count=round(entry['duration']*60)+1;old=[]
 for f in range(count):s.frame_set(f);old.append({b.name:b.matrix.copy() for b in r.pose.bones})
 old=smooth_release(old)
 # Match the existing contact layer's twelve-frame handoff to the stock.
 # Empty-reload pumping after frame 372 retains its original grip support.
 weights=[ease(f/15)*(1-ease((f-360)/12)) for f in range(count)]
 frames=[geometry(p,w,f) for f,(p,w) in enumerate(zip(old,weights))];rolls=np.unwrap([v[-1] for v in frames]);rows=[]
 for f,(p,w,data,roll) in enumerate(zip(old,weights,frames,rolls)):
  q={n:m.copy() for n,m in p.items()}
  if w<1.e-8:rows.append(q);continue
  a,e,h,neutral,_=data;fore=h-e;axis=fore.normalized()
  hinge=(e-a).cross(h-e)
  anatomical_upper=basis(e-a,hinge)@FU.inverted()@rest['upperarm_r'].to_3x3()
  original_upper=(p['lowerarm_r'].translation-p['upperarm_r'].translation).rotation_difference(e-a)@p['upperarm_r'].to_quaternion()
  uq=qslerp(original_upper,anatomical_upper.to_quaternion(),w)
  um=Matrix.LocRotScale(a,uq,Vector((1,1,1)));ud=um@p['upperarm_r'].inverted()
  for n in q:
   if under(n,'upperarm_r') and not under(n,'lowerarm_r'):q[n]=ud@p[n]
  q['clavicle_r'].translation+=a-p['upperarm_r'].translation
  proximal=Quaternion(axis,float(roll)*.35).to_matrix()@neutral
  upper=(um@rest['upperarm_r'].inverted()).to_3x3()
  for n in stations:
   offset=rest[n].translation-rest['lowerarm_r'].translation;t=offset.dot(rf)/rf.length_squared
   driver=Quaternion(axis,float(roll)*(.35+.65*ease(t/(2/3)))).to_matrix()@neutral
   if n=='lowerarm_aux_r':driver=qslerp(upper.to_quaternion(),proximal.to_quaternion(),.5).to_matrix()
   target=(driver@rest[n].to_3x3()).to_quaternion()
   rotation=qslerp(p[n].to_quaternion(),target,w)
   # Keep each station's actual pivot; only axial roll is distributed.
   final_driver=rotation@rest[n].to_quaternion().inverted()
   position=e+t*fore+final_driver@(offset-t*rf)
   q[n]=Matrix.LocRotScale(position,rotation,Vector((1,1,1)))
  # Whole-hand contact stays in author/world space. Re-encode its new parent
  # through the exporter; preserve held fingers and remove the old thumb-base
  # translation during release, instead of stretching the palm to follow it.
  for n in handbones:
   if n=='hand_r':continue
   parent=parents[n];local=p[parent].inverted()@p[n]
   local.translation=local.translation.lerp(local_rest[n].translation,w)
   q[n]=q[parent]@local
  native_digits(q,w)
  rows.append(q)
 bake(role,rows);recipes[role]={'input_action':entry['action'],'frames':count,'support_blend_in_frames':15,'stock_handoff_frames':[360,372],'arm_motion_source':'UC 870 reloadinsert, complete arm directions in anatomical palm frame'}
action=bpy.data.actions[authored['reload_continuous']['action']];r.animation_data.action=action;r.animation_data.action_slot=action.slots[0];s.frame_set(30)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M870_ReloadWrist_Editable.blend'))
(O/'authoring.json').write_text(json.dumps({'clips':authored,'recipe':recipes,'support_reference':'Super90QuickMelee20261008/RightArmR9 anatomical frame and native skin stations','scope':'Right support, anatomical digit hinge roll and native base translations; smooth released-hand retreat; held hand/prop contact, left arm, weapon, event clock and other actions preserved','runtime_tested':False},indent=2))
print('M870_RELOAD_WRIST_AUTHORED',len(authored),flush=True)
