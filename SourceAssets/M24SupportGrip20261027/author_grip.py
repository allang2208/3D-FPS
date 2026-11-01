"""Native-axis support grasp; sparse animation inputs, with no mesh/rest changes."""
import bpy,json,math,ast,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).resolve().parent;X=O/'Exports';X.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24MotionMagazine20261027/M24_MotionMagazine_Editable.blend'),use_scripts=False)
s=bpy.context.scene;r=bpy.data.objects['M24_V9_Rig'];skin=bpy.data.objects['M24_V9_BareArms']
rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
local_rest={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
for file,names in [('M24CustomScope20261026/author_gameplay.py',('under','twists')),('M24Hold20261027/author_hold.py',('bake',))]:
 tree=ast.parse((O.parent/file).read_text())
 for name in names:exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)),name,'exec'))
report={'clips':{},'fps':30,'source':'M24MotionMagazine20261027/M24_MotionMagazine_Editable.blend','runtime_tested':False,
 'method':'native axial swing, anatomical PIP/DIP hinges, bounded skin-to-forend fitting; no finger translation or scaling',
 'unchanged':['weapon tracks','right arm','left wrist and arm tracks','mesh','rest pose','weights','morphs','mechanical clocks']}
def clone(p):return {n:m.copy() for n,m in p.items()}
def ease(t):
 t=max(0.,min(1.,t));return t*t*t*(t*(t*6-15)+10)
def sample(role):
 a=bpy.data.actions['A_M24_'+role];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];rows=[]
 for f in range(round(a.frame_range[1])+1):
  s.frame_set(f);bpy.context.view_layer.update();rows.append({b.name:b.matrix.copy() for b in r.pose.bones})
 return rows
roles=('idle','aim','equip','fire','cycle','reload','reload_empty','inspect','quick_melee','sprint_enter','sprint_loop','sprint_exit','reload_mag10','reload_empty_mag10')
clips={role:sample(role) for role in roles};idle=clips['aim'][0]
digits=[b.name for b in r.data.bones if under(b.name,'hand_l') and b.name!='hand_l']
native={n:idle[parents[n]].inverted()@idle[n] for n in digits}
# UE/Manny's physical finger axis is +X. The former terminal-bone retarget
# used +Y; this injected up to 173 degrees of rotation into the last joint.
target={n:m.copy() for n,m in native.items()}
palm_normal=-(rest['index_01_l'].translation-rest['pinky_01_l'].translation).cross(rest['middle_01_l'].translation-rest['hand_l'].translation).normalized()
hinges={}
for finger in ('index','middle','ring','pinky'):
 first=finger+'_01_l';second=finger+'_02_l'
 axis=(rest[second].translation-rest[first].translation).cross(palm_normal).normalized()
 for j in (1,2,3):
  name=f'{finger}_{j:02d}_l';v=rest[name].to_quaternion().inverted()@axis;v.x=0;v.normalize();hinges[name]=v
 # Remove only axial roll; retain the original MCP direction and wrist anchor.
 delta=(local_rest[first].inverted()@native[first]).to_quaternion();swing,_=delta.to_swing_twist('X')
 target[first]=local_rest[first]@swing.to_matrix().to_4x4()
for j in (1,2):
 n=f'thumb_{j:02d}_l';delta=(local_rest[n].inverted()@native[n]).to_quaternion();swing,_=delta.to_swing_twist('X')
 target[n]=local_rest[n]@swing.to_matrix().to_4x4()
# The thumb retains its opposition and proximal pose. Only its twisted terminal
# segment gets a modest native hinge flexion, aligned with the proximal curl.
target['thumb_03_l']=local_rest['thumb_03_l']@Matrix.Rotation(math.radians(-18),4,'Z')

gun=bpy.data.objects['M24_base'];gun.data.calc_loop_triangles()
bvh=BVHTree.FromPolygons([v.co for v in gun.data.vertices],[t.vertices for t in gun.data.loop_triangles],all_triangles=True)
names=list(rest);ids={n:i for i,n in enumerate(names)};inv=np.array([np.array(rest[n].inverted()) for n in names])
vertices=np.array([list(v.co)+[1.] for v in skin.data.vertices]);weights=np.zeros((len(vertices),len(names)),dtype=np.float64)
for v in skin.data.vertices:
 for g in v.groups:
  n=skin.vertex_groups[g.group].name
  if n in ids:weights[v.index,ids[n]]=g.weight
dominant=weights.argmax(1);group={}
for finger in ('index','middle','ring','pinky'):
 # Use the actual skin, not the bone endpoints, for fit. Keep a bounded set
 # from each segment plus palm-facing distal pads so the optimizer cannot
 # trade a twisted finger for a closer abstract fingertip.
 groups=[];pads=[]
 for j in (1,2,3):
  n=f'{finger}_{j:02d}_l';allids=np.flatnonzero(dominant==ids[n]);groups.extend(allids[::max(1,len(allids)//45)])
  if j>=2:
   eligible=[i for i in allids if skin.data.vertices[int(i)].normal.dot(palm_normal)>.25]
   pads.extend(eligible[::max(1,len(eligible)//24)])
 group[finger]=(np.array(groups,dtype=int),np.array(pads,dtype=int))
def pose_from(local):
 pose=clone(idle)
 for n in digits:pose[n]=pose[parents[n]]@local[n]
 return pose
def deform(pose,selected):
 mats=np.array([np.array(pose[n]) for n in names])@inv
 return np.einsum('vk,kij,vj->vi',weights[selected],mats,vertices[selected],optimize=True)[:,:3]
def distances(points):
 signed=[];unsigned=[]
 for p in points:
  q,n,_,d=bvh.find_nearest(Vector(p))
  signed.append(d if (Vector(p)-q).dot(n)>=0 else -d);unsigned.append(d)
 return np.array(signed),np.array(unsigned)
def evaluate(finger,a,b):
 local={n:m.copy() for n,m in target.items()}
 for j,angle in ((2,a),(3,b)):
  name=f'{finger}_{j:02d}_l';local[name]=local_rest[name]@Quaternion(hinges[name],math.radians(angle)).to_matrix().to_4x4()
 pose=pose_from(local);whole,pads=group[finger]
 signed,_=distances(deform(pose,whole));_,contact=distances(deform(pose,pads))
 # Use a small skin clearance and an anatomical prior. Penetration is penalized
 # across the whole finger, while only the closest palm pads seek the shell.
 penetration=np.mean(np.minimum(signed-.0005,0)**2)*30
 contact_cost=np.mean(np.sort(contact)[:max(3,len(contact)//4)]**2)*2 if len(contact) else 0
 natural=((a-32)/18)**2+((b-16)/14)**2
 return float(penetration+contact_cost+natural*.000002),local
fit={}
for finger in ('index','middle','ring','pinky'):
 best=None
 for a in range(10,51,5):
  for b in range(0,31,5):
   score,local=evaluate(finger,a,b)
   if best is None or score<best[0]:best=(score,a,b,local)
 score,a,b,local=best
 for j in (2,3):n=f'{finger}_{j:02d}_l';target[n]=local[n]
 fit[finger]={'pip_extra_deg':a,'dip_extra_deg':b,'objective':score}
report['fit']=fit;report['target_local']={n:[list(v) for v in m] for n,m in target.items()}

def support_weight(role,frame,count):
 if role.startswith('reload'):
  return 1-ease((frame-6)/7) if frame<13 else ease((frame-44)/10)
 return 1.
def relax_weight(role,frame,count):
 if role=='sprint_enter':return .35*ease((frame/15)/.7)
 if role=='sprint_exit':return .35*ease((1-frame/12)/.7)
 if role=='sprint_loop':return .35
 return 0.
for role,rows in clips.items():
 for f,row in enumerate(rows):
  w=support_weight(role,f,len(rows));relax=relax_weight(role,f,len(rows));old=clone(row)
  for n in digits:
   original=old[parents[n]].inverted()@old[n]
   desired=target[n].lerp(local_rest[n],relax)
   # Preserve each source's local bone translation and scale exactly; edit
   # rotation only, then reconstruct all descendants once in parent order.
   p,q,sc=original.decompose();q=q.slerp(desired.to_quaternion(),w)
   row[n]=row[parents[n]]@Matrix.LocRotScale(p,q,sc)
 old=bpy.data.actions.get('A_M24_'+role);r.animation_data.action=None;bpy.data.actions.remove(old)
 bake(role,rows)
 bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
 path=X/('A_M24_'+role+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
 report['clips'][role]['file']=str(path)
r.animation_data.action=bpy.data.actions['A_M24_aim'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(0)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_SupportGrip_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M24_SUPPORT_GRIP_AUTHORED',json.dumps(fit),flush=True)
