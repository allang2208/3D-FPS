"""Native hinge sprint arm and bolt-local right-hand contact, preserving gun clocks."""
import bpy,json,math,ast,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).resolve().parent;X=O/'Exports';X.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24SupportGrip20261027/M24_SupportGrip_Editable.blend'),use_scripts=False)
s=bpy.context.scene;r=bpy.data.objects['M24_V9_Rig'];skin=bpy.data.objects['M24_V9_BareArms']
rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
local_rest={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
C=Matrix(json.loads((O.parent/'M24Hold20261027/hip-calibration.json').read_text())['hip_transform'])@Matrix.Diagonal((100,-100,100,1));Ci=C.inverted()
report={'clips':{},'fps':30,'source':'M24SupportGrip20261027/M24_SupportGrip_Editable.blend','runtime_tested':False}
def under(n,p):
 while n:
  if n==p:return True
  n=parents.get(n)
 return False
def clone(row):return {n:m.copy() for n,m in row.items()}
def ease(t):
 t=max(0.,min(1.,t));return t*t*t*(t*(t*6-15)+10)
def sample(role):
 a=bpy.data.actions['A_M24_'+role];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
 rows=[]
 for f in range(round(a.frame_range[1])+1):
  s.frame_set(f);bpy.context.view_layer.update();rows.append({b.name:b.matrix.copy() for b in r.pose.bones})
 return rows
idle=sample('aim')[0]
roles=('sprint_enter','sprint_loop','sprint_exit','fire','cycle','reload_empty')
clips={role:sample(role) for role in roles}
def frame(x,z):
 x=x.normalized();z=(z-x*z.dot(x)).normalized();y=z.cross(x).normalized()
 return Matrix((x,y,z)).transposed()
def solve(row,side,goal,pole,blend,hand_q=None):
 old=clone(row);u,l,h=['upperarm_'+side,'lowerarm_'+side,'hand_'+side]
 shoulder=old[u].translation.copy();a=(rest[l].translation-rest[u].translation).length;b=(rest[h].translation-rest[l].translation).length
 axis=goal-shoulder;maxreach=.965*(a+b)
 if axis.length>maxreach:shoulder+=axis.normalized()*(axis.length-maxreach)
 axis=goal-shoulder;d=max(axis.length,abs(a-b)+.00001);axis.normalize()
 pole=pole-axis*pole.dot(axis);pole.normalize();along=(a*a-b*b+d*d)/(2*d)
 elbow=shoulder+axis*along+pole*math.sqrt(max(0,a*a-along*along))
 U=elbow-shoulder;L=goal-elbow;normal=U.cross(L).normalized()
 RU=rest[l].translation-rest[u].translation;RL=rest[h].translation-rest[l].translation;RN=RU.cross(RL).normalized()
 uq=(frame(U,normal)@frame(RU,RN).transposed()).to_quaternion()@rest[u].to_quaternion()
 lq=(frame(L,normal)@frame(RL,RN).transposed()).to_quaternion()@rest[l].to_quaternion()
 transport_u=(old[l].translation-old[u].translation).rotation_difference(U)@old[u].to_quaternion()
 transport_l=(old[h].translation-old[l].translation).rotation_difference(L)@old[l].to_quaternion()
 uq=transport_u.slerp(uq,blend);lq=transport_l.slerp(lq,blend)
 if hand_q is None:
  q0=idle[l].to_quaternion().inverted()@idle[h].to_quaternion()
  q1=rest[l].to_quaternion().inverted()@rest[h].to_quaternion()
  hand_q=lq@q0.slerp(q1,blend)
 transforms={u:Matrix.LocRotScale(shoulder,uq,Vector((1,1,1))),l:Matrix.LocRotScale(elbow,lq,Vector((1,1,1))),h:Matrix.LocRotScale(goal,hand_q,Vector((1,1,1)))}
 for n in row:
  if under(n,h):row[n]=transforms[h]@old[h].inverted()@old[n]
  elif under(n,l):row[n]=transforms[l]@rest[l].inverted()@rest[n]
  elif under(n,u):row[n]=transforms[u]@rest[u].inverted()@rest[n]
 row['clavicle_'+side].translation+=shoulder-old[u].translation
 # V9 forearm skin contract: distal station 100%, middle station 50%.
 axis_local=rest[l].to_quaternion().inverted()@RL.normalized()
 relative=(lq.inverted()@hand_q)@(rest[l].to_quaternion().inverted()@rest[h].to_quaternion()).inverted()
 if relative.w<0:relative.negate()
 angle=2*math.atan2(Vector((relative.x,relative.y,relative.z)).dot(axis_local),relative.w)
 for index,share in ((1,1.),(2,.5)):
  n=f'lowerarm_twist_{index:02d}_{side}';lr=local_rest[n]
  row[n]=row[l]@Matrix.LocRotScale(lr.translation,Quaternion(axis_local,angle*share)@lr.to_quaternion(),Vector((1,1,1)))
 return math.degrees(angle)

left=[n for n in rest if under(n,'upperarm_l') or n=='clavicle_l']
ldigits=[n for n in rest if under(n,'hand_l') and n!='hand_l']
for role in roles[:3]:
 for f,row in enumerate(clips[role]):
  progress=f/15 if role=='sprint_enter' else 1-f/12 if role=='sprint_exit' else 1
  w=ease(min(1,progress/.75));phase=2*math.pi*f/30 if role=='sprint_loop' else 0
  for n in left:row[n]=idle[n].copy()
  # Move the shoulder skin clear of the lower camera edge with the released arm.
  for n in left:row[n].translation+=Ci.to_3x3()@Vector((0,0,-4.*w))
  goal=C@idle['hand_l'].translation
  parked=Vector((23.,-27.,-57.))+Vector((1.0*math.sin(phase),.8*math.sin(phase),1.2*math.sin(phase*2)))
  goal=Ci@goal.lerp(parked,w)
  oldpole=C.to_3x3()@(idle['lowerarm_l'].translation-idle['upperarm_l'].translation)
  pole_camera=oldpole.lerp(Vector((-9.,-19.,-29.)),w)
  if w>0:solve(row,'l',goal,Ci.to_3x3()@pole_camera,w)
  for n in ldigits:
   initial=idle[parents[n]].inverted()@idle[n];p,q,sc=initial.decompose()
   row[n]=row[parents[n]]@Matrix.LocRotScale(p,q.slerp(local_rest[n].to_quaternion(),.40*w),sc)

# Rebuild native flexion. Terminal joints no longer inherit donor +Y axis roll.
ref=clips['fire'][28];right_digits=[n for n in rest if under(n,'hand_r') and n!='hand_r']
grip={n:(ref[parents[n]].inverted()@ref[n]) for n in right_digits}
pn=-(rest['index_01_r'].translation-rest['pinky_01_r'].translation).cross(rest['middle_01_r'].translation-rest['hand_r'].translation).normalized()
for finger in ('index','middle','ring','pinky'):
 first=finger+'_01_r';axis=(rest[finger+'_02_r'].translation-rest[first].translation).cross(pn).normalized()
 for j,deg in ((1,68),(2,92),(3,38)):
  n=f'{finger}_{j:02d}_r';v=rest[n].to_quaternion().inverted()@axis;v.x=0;v.normalize()
  grip[n]=local_rest[n]@Quaternion(v,math.radians(deg)).to_matrix().to_4x4()
thumb_axis=(rest['thumb_02_r'].translation-rest['thumb_01_r'].translation).cross(pn).normalized()
for j,deg in ((1,35),(2,25),(3,25)):
 n=f'thumb_{j:02d}_r';v=rest[n].to_quaternion().inverted()@thumb_axis
 q=Quaternion(v,math.radians(deg))
 if j==1:q=Quaternion(rest[n].to_quaternion().inverted()@pn,math.radians(-25))@q
 grip[n]=local_rest[n]@q.to_matrix().to_4x4()

# The knob's convex terminal shell, expressed in its actual moving bone frame.
fit=json.loads((O/'bolt_grip_fit.json').read_text())
grip={n:Matrix(m) for n,m in fit['local_grip'].items()}
bolt=bpy.data.objects['M24_bolt']
knob=[v.co for v in bolt.data.vertices if v.co.x>.046]
center=Vector(tuple((min(p[i] for p in knob)+max(p[i] for p in knob))*.5 for i in range(3)))
knob_local=rest['WPN_BoltHandle'].inverted()@center
# Keep the existing approach orientation, but anchor the curled palm in knob space.
H=ref['hand_r'].copy();template=clone(ref)
for n in right_digits:template[n]=template[parents[n]]@grip[n]
names=list(rest);ids={n:i for i,n in enumerate(names)}
verts=np.array([list(v.co)+[1] for v in skin.data.vertices]);weights=np.zeros((len(verts),len(names)))
for v in skin.data.vertices:
 for g in v.groups:
  name=skin.vertex_groups[g.group].name
  if name in ids:weights[v.index,ids[name]]=g.weight
dominant=weights.argmax(1)
mats=np.array([np.array(H.inverted()@template[n]@rest[n].inverted()) for n in names])
local_skin=np.einsum('vk,kij,vj->vi',weights,mats,verts,optimize=True)[:,:3]
# Contact patch on the palm side of proximal middle/index fingers, rather than the wrist.
patch=np.flatnonzero(np.isin(dominant,[ids['index_01_r'],ids['middle_01_r']]))
contact=Vector(fit['parameters'][:3])
normal_local=rest['hand_r'].to_quaternion().inverted()@pn
center_pose=ref['WPN_BoltHandle']@knob_local
H.translation=center_pose-H.to_quaternion()@contact
anchor=ref['WPN_BoltHandle'].inverted()@H
report['bolt_contact']={'knob_local':[float(x) for x in knob_local],'hand_anchor':[list(x) for x in anchor],'contact_hand_local':list(contact)}
for role in roles[3:]:
 shift={'fire':0,'cycle':4,'reload_empty':52}[role]
 for f,row in enumerate(clips[role]):
  t=f-shift;w=ease((t-9)/8)*(1-ease((t-39)/8))
  if w<=0:continue
  original=clone(row);target=row['WPN_BoltHandle']@anchor
  desired=original['hand_r'].lerp(target,w)
  pole=original['lowerarm_r'].translation-original['upperarm_r'].translation
  solve(row,'r',desired.translation,pole,w,desired.to_quaternion())
  for n in right_digits:
   local=original[parents[n]].inverted()@original[n];p,q,sc=local.decompose()
   row[n]=row[parents[n]]@Matrix.LocRotScale(p,q.slerp(grip[n].to_quaternion(),w),sc)

# Dense export uses exact native local transforms, without re-solving untouched arms.
tree=ast.parse((O.parent/'M24Hold20261027/author_hold.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='bake')
node.body=[n for n in node.body if not(isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='twists')]
exec(compile(ast.unparse(node),'bake','exec'))
for role,rows in clips.items():
 old=bpy.data.actions['A_M24_'+role];r.animation_data.action=None;bpy.data.actions.remove(old);bake(role,rows)
 bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
 path=X/('A_M24_'+role+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
 report['clips'][role].update(file=str(path),owned_bones=left if role.startswith('sprint') else [n for n in rest if under(n,'upperarm_r') or n=='clavicle_r']+ldigits)
r.animation_data.action=bpy.data.actions['A_M24_aim'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(0)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_MotionPolish_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M24_MOTION_POLISH_EXPORTED',len(clips),flush=True)
