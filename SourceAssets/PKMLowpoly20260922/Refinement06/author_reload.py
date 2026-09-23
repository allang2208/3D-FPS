"""Author two editable, reference-informed FPS reload candidates. No tests or preview renders."""
import bpy,json,math,pathlib
from mathutils import Matrix,Vector,Quaternion
OUT=pathlib.Path(__file__).parent;ROOT=OUT.parent
import sys
sys.path.insert(0,str(OUT))
from belt_dynamics import BeltDynamics
fingertips=json.loads((OUT/'fingertips.json').read_text())
SRC=pathlib.Path('D:/FPS3D/FPSGAME/SourceAssets/M4TacticalToss20260910/M4_Hand_MAT_Editable.blend')
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(SRC))
# The donor's library-relative Manny paths must be made absolute before saving elsewhere.
handTex=pathlib.Path('D:/FPS3D/FPSGAME/SourceAssets/M4Infima/Original/Blender_Source_Files_FreeFpsTemplate/Textures/Manny')
for image in bpy.data.images:
 filename=pathlib.Path(image.filepath).name
 if filename.startswith('T_Manny_') and (handTex/filename).is_file():image.filepath=str(handTex/filename)
scene=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];hands=bpy.data.objects['SK_Manny_Arms_Export']
source=bpy.data.actions['M4_idle'];r.animation_data.action=source;r.animation_data.action_slot=source.slots[0]
scene.frame_set(0);bpy.context.view_layer.update()
base={b.name:b.matrix.copy() for b in r.pose.bones};rest={b.name:b.bone.matrix_local.copy() for b in r.pose.bones}
parents={b.name:b.parent.name if b.parent else None for b in r.pose.bones}
baseW=base['WPN_root'];restW=rest['WPN_root']
# Remove the donor rifle's roll around the gun axis without moving the grip.
up=baseW.to_3x3()@Vector((0,0,1))
donor_roll=math.atan2(up.x,up.z)
levelW=baseW@Matrix.Rotation(donor_roll,4,'Y')
data=json.loads((ROOT/'hands_source.json').read_text());lo,hi=data['donor_grip_bounds']
grip=(Vector(lo)+Vector(hi))*.5
fit=Matrix.Translation(grip-Vector((0,.25855,-.0648)))
for o in list(bpy.data.objects):
 if o not in [r,hands]:bpy.data.objects.remove(o,do_unlink=True)
r.animation_data_clear()
for b in r.pose.bones:
 for c in list(b.constraints):b.constraints.remove(c)
for a in bpy.data.actions:a.use_fake_user=False

with bpy.data.libraries.load(str(ROOT/'Mechanics02/PKM_Mechanics_Editable.blend'),link=False) as (src,dst):
 dst.objects=[n for n in src.objects if n=='PKM_MechanicalRig' or n.startswith('PKM_') and n!='PKM_Lowpoly_Assembly']
imported=[o for o in dst.objects if o]
for o in imported:scene.collection.objects.link(o)
mechanical=next(o for o in imported if o.type=='ARMATURE');weapons=[o for o in imported if o.type=='MESH']
mechanicRest={b.name:b.matrix_local.copy() for b in mechanical.data.bones}
mechanicParent={b.name:b.parent.name if b.parent else 'WPN_root' for b in mechanical.data.bones}

def select(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for o in obs:o.hide_set(False);o.select_set(True)
 bpy.context.view_layer.objects.active=obs[-1]

select([r]);bpy.ops.object.mode_set(mode='EDIT')
for name,m in mechanicRest.items():
 if name=='WPN_root':continue
 # A new edit bone has zero length. Give it a direction/length BEFORE setting
 # its full matrix; otherwise Blender reconstructs a different rest axis.
 b=r.data.edit_bones.new(name);b.head=(0,0,0);b.tail=(0,.025,0);b.matrix=restW@fit@m
 b.parent=r.data.edit_bones[mechanicParent[name]]
# Separate old/new box and belt sets avoid visible mid-animation mesh resets or scale hiding.
dupeNames=[n for n in mechanicRest if n.startswith('PKM_Belt') or n in ['PKM_Box','PKM_BoxLid']]
for name in dupeNames:
 b=r.data.edit_bones.new('New_'+name);b.head=(0,0,0);b.tail=(0,.025,0);b.matrix=restW@fit@mechanicRest[name]
 parent=mechanicParent[name];b.parent=r.data.edit_bones['New_'+parent if parent in dupeNames else parent]
bpy.ops.object.mode_set(mode='OBJECT')

# Reject this specific bind-basis failure before producing a visually inverted gun.
for name,m in mechanicRest.items():
 if name=='WPN_root':continue
 for target in [name]+(['New_'+name] if name in dupeNames else []):
  expected=restW@fit@m;actual=r.data.bones[target].matrix_local
  error=max(abs(a-b) for ra,rb in zip(actual,expected) for a,b in zip(ra,rb))
  if error>1e-4:raise RuntimeError('Mechanical bind basis mismatch: '+target+' '+str(error))

for ob in weapons:
 bone=ob['mechanical_bone'];world=ob.matrix_world.copy();ob.parent=None
 ob.data=ob.data.copy();ob.data.transform(restW@fit@world);ob.matrix_world=Matrix.Identity(4)
 ob.parent=r;ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4)
 for mod in ob.modifiers:
  if mod.type=='ARMATURE':mod.object=r
 if bone in dupeNames:
  twin=ob.copy();twin.data=ob.data.copy();twin.name='New_'+ob.name;scene.collection.objects.link(twin)
  for vg in twin.vertex_groups:vg.name='New_'+vg.name
  twin['mechanical_bone']='New_'+bone
for ob in list(scene.objects):
 if ob.type=='MESH' and ob.name.startswith('New_PKM_') and ob not in weapons:weapons.append(ob)
bpy.data.objects.remove(mechanical,do_unlink=True)
r.name='PKM_Manny_Rig'
for b in r.data.bones:
 rest[b.name]=b.matrix_local.copy();parents[b.name]=b.parent.name if b.parent else None
for b in r.pose.bones:b.rotation_mode='QUATERNION'
scene.render.fps=60;scene.render.fps_base=1

inp=json.loads((ROOT/'mechanics_inputs.json').read_text());centers=[Vector(v['center']) for v in inp['cartridges']]
dynamics={}
hinge=Vector((0,-.021,.07));boxPivot=Vector((0,.04,-.065))
off=Vector((-.43,.36,-.65))
def smooth(a):a=max(0,min(1,a));return a*a*(3-2*a)
def mix(a,b,t):return a*(1-t)+b*t
def ramp(t,a,b):return smooth((t-a)/(b-a))
def seq(t,keys):
 if t<=keys[0][0]:return keys[0][1]
 for (a,v),(b,w) in zip(keys,keys[1:]):
  if t<=b:return mix(v,w,ramp(t,a,b))
 return keys[-1][1]
def trx(v):return Matrix.Translation(Vector(v))
def rot(axis,degrees):return Matrix.Rotation(math.radians(degrees),4,axis)
def around(p,q):return trx(p)@q@trx(-Vector(p))
def matrix_mix(a,b,t):
 la,qa,sa=a.decompose();lb,qb,sb=b.decompose()
 return Matrix.LocRotScale(la.lerp(lb,t),qa.slerp(qb,t),sa.lerp(sb,t))
def matrix_seq(t,keys):
 if t<=keys[0][0]:return keys[0][1]
 for (a,v),(b,w) in zip(keys,keys[1:]):
  if t<=b:return matrix_mix(v,w,ramp(t,a,b))
 return keys[-1][1]

# Palm frames derive from each donor hand independently; no mirrored Euler-angle copy.
palm={}
for side in ['l','r']:
 h=base['hand_'+side];mid=base['middle_01_'+side].translation
 f=(mid-h.translation).normalized();width=(base['index_01_'+side].translation-base['pinky_01_'+side].translation).normalized()
 normal=f.cross(width).normalized()
 if side=='l':normal.negate()
 y=normal.cross(f).normalized();basis=Matrix((f,y,normal)).transposed()
 palm[side]={'basis':basis,'offset':h.inverted()@h.translation.lerp(mid,.63)}
def contact(side,point,forward,normal,W):
 f=Vector(forward).normalized();n=Vector(normal).normalized();y=n.cross(f).normalized();f=y.cross(n).normalized()
 target=Matrix((f,y,n)).transposed()
 R=W.to_3x3()@target@palm[side]['basis'].transposed()@base['hand_'+side].to_3x3()
 p=W@(fit@Vector(point));q=R.to_quaternion();return Matrix.LocRotScale(p-q@palm[side]['offset'],q,Vector((1,1,1)))

def belt_pose(boxM,delta):
 pts=[boxM@c for c in centers];anchor=pts[5].copy();target=pts[0]+Vector(delta)
 chain=[pts[i].copy() for i in range(5,-1,-1)];lengths=[(chain[i+1]-chain[i]).length for i in range(5)]
 if (target-anchor).length>sum(lengths)*.999:target=anchor+(target-anchor).normalized()*sum(lengths)*.999
 for _ in range(10):
  chain[-1]=target.copy()
  for i in range(4,-1,-1):chain[i]=chain[i+1]+(chain[i]-chain[i+1]).normalized()*lengths[i]
  chain[0]=anchor.copy()
  for i in range(5):chain[i+1]=chain[i]+(chain[i+1]-chain[i]).normalized()*lengths[i]
 for k,p in enumerate(chain):pts[5-k]=p
 matrices=[]
 for i,p in enumerate(pts):
  j=i+1 if i<13 else i-1
  old=centers[j]-centers[i];new=pts[j]-p
  q=old.rotation_difference(new)
  matrices.append(trx(p)@q.to_matrix().to_4x4()@trx(-centers[i]))
 return pts,matrices

def solve_arm(side,target,open_amount,desired,bodyMove):
 names=['upperarm_'+side,'lowerarm_'+side,'hand_'+side]
 shoulder=base[names[0]].translation+bodyMove;elbow=base[names[1]].translation+bodyMove;wrist=base[names[2]].translation+bodyMove
 l1=(elbow-shoulder).length;l2=(wrist-elbow).length
 delta=target.translation-shoulder;distance=delta.length
 # Reach is limited by anatomy. Never stretch/translate the shoulder to chase a prop.
 shift=Vector()
 direction=(target.translation-shoulder).normalized();distance=(target.translation-shoulder).length
 distance=max(abs(l1-l2)+.001,min(distance,l1+l2-.001))
 # Keep the reload elbow outside/below the receiver instead of crossing it.
 pole=Vector((.38 if side=='r' else -.38,-.08,-.38))
 pole=pole-direction*pole.dot(direction)
 if pole.length<.001:pole=Vector((-1 if side=='l' else 1,0,-1)).cross(direction)
 pole.normalize();a=(l1*l1-l2*l2+distance*distance)/(2*distance)
 newElbow=shoulder+direction*a+pole*math.sqrt(max(0,l1*l1-a*a))
 newWrist=shoulder+direction*distance
 for name,p0,p1,orig0,orig1 in [(names[0],shoulder,newElbow,base[names[0]].translation,base[names[1]].translation),(names[1],newElbow,newWrist,base[names[1]].translation,base[names[2]].translation)]:
  q=(orig1-orig0).rotation_difference(p1-p0);m=q.to_matrix().to_4x4()@base[name];m.translation=p0;desired[name]=m
 target=target.copy();target.translation=newWrist;desired[names[2]]=target
 for seg in ['upperarm','lowerarm']:
  xf=desired[seg+'_'+side]@base[seg+'_'+side].inverted()
  for name in base:
   if name.startswith(seg+'_twist_') and name.endswith('_'+side):desired[name]=xf@base[name]
 # Distribute wrist twist along the two forearm roll bones. Wrist deformation
 # no longer carries the full axial rotation in one narrow ring of vertices.
 fore=desired[names[1]];dq=fore.to_quaternion().inverted()@target.to_quaternion()
 axis=(newWrist-newElbow).normalized();axisLocal=fore.to_quaternion().inverted()@axis
 v=Vector((dq.x,dq.y,dq.z));proj=axisLocal*v.dot(axisLocal)
 twist=Quaternion((dq.w,proj.x,proj.y,proj.z));twist.normalize()
 donorDq=base[names[1]].to_quaternion().inverted()@base[names[2]].to_quaternion()
 v=Vector((donorDq.x,donorDq.y,donorDq.z));proj=axisLocal*v.dot(axisLocal)
 donorTwist=Quaternion((donorDq.w,proj.x,proj.y,proj.z));donorTwist.normalize()
 twist=twist@donorTwist.inverted()
 for suffix,weight in [('02',.33),('01',.67)]:
  n='lowerarm_twist_'+suffix+'_'+side
  q=fore.to_quaternion()@Quaternion().slerp(twist,weight)@fore.to_quaternion().inverted()
  m=desired[n];p=m.translation.copy();m=q.to_matrix().to_4x4()@m;m.translation=p;desired[n]=m
 clav='clavicle_'+side;desired[clav]=trx(bodyMove+shift)@base[clav]
 for name in base:
  if name==names[2] or not name.endswith('_'+side):continue
  if not any(name.startswith(f) for f in ['thumb_','index_','middle_','ring_','pinky_']):continue
  parent=parents[name]
  localRest=rest[parent].inverted()@rest[name]
  basis=localRest.inverted()@base[parent].inverted()@base[name]
  loc,q,scl=basis.decompose();amount=open_amount*(.32 if 'metacarpal' in name else .5 if 'thumb' in name else 1)
  local=localRest@Matrix.LocRotScale(loc,q.slerp(Quaternion(),amount),scl)
  desired[name]=desired[parent]@local

def support_fingers(desired,W,amount):
 # Individual three-joint contact targets, outside the front receiver/box.
 # Start from the donor's anatomical curl and preserve every phalanx length.
 targets={'thumb':(.010,-.015,.104),'index':(.012,-.103,.014),
          'middle':(-.020,-.080,-.005),'ring':(-.020,-.057,-.026),
          'pinky':(-.010,-.039,-.035)}
 for digit,point in targets.items():
  names=[f'{digit}_{i:02}_l' for i in range(1,4)]
  originals={n:desired[n].copy() for n in names}
  if digit=='thumb':
   # Bend around the OUTSIDE of the wall, then lay the distal phalanx over
   # the top. A tip-only CCD solution can cut through the receiver wall.
   p0=originals[names[0]].translation;p1=originals[names[1]].translation;p2=originals[names[2]].translation
   l1=(p1-p0).length;l2=(p2-p1).length
   target=p2.lerp(W@fit@Vector((.034,-.018,.101)),amount)
   direction=(target-p0).normalized();dist=min((target-p0).length,l1+l2-.0001)
   target=p0+direction*dist
   outward=W.to_3x3()@Vector((1,0,0));outward=(outward-direction*outward.dot(direction)).normalized()
   initialPole=p1-p0;initialPole=(initialPole-direction*initialPole.dot(direction)).normalized()
   pole=initialPole.lerp(outward,amount).normalized()
   along=(l1*l1-l2*l2+dist*dist)/(2*dist)
   elbow=p0+direction*along+pole*math.sqrt(max(0,l1*l1-along*along))
   for n,oldA,oldB,newA,newB in [(names[0],p0,p1,p0,elbow),(names[1],p1,p2,elbow,target)]:
    q=(oldB-oldA).rotation_difference(newB-newA);m=q.to_matrix().to_4x4()@originals[n];m.translation=newA;desired[n]=m
   oldTip=originals[names[2]]@Vector(fingertips[names[2]]['local_tip'])
   tipGoal=oldTip.lerp(W@fit@Vector((.006,-.019,.104)),amount)
   q=(oldTip-p2).rotation_difference(tipGoal-target);m=q.to_matrix().to_4x4()@originals[names[2]];m.translation=target;desired[names[2]]=m
   continue
  tip=Vector(fingertips[names[-1]]['local_tip']);goal=W@fit@Vector(point)
  initial=desired[names[-1]]@tip;goal=initial.lerp(goal,amount)
  for _ in range(14):
   for i in [2,1,0]:
    pivot=desired[names[i]].translation;end=desired[names[-1]]@tip
    a=end-pivot;b=goal-pivot
    if min(a.length,b.length)<1e-7:continue
    q=a.rotation_difference(b)
    if q.angle>.25:q=Quaternion().slerp(q,.25/q.angle)
    xf=trx(pivot)@q.to_matrix().to_4x4()@trx(-pivot)
    for n in names[i:]:desired[n]=xf@desired[n]

def frame_pose(t,kind):
 idle=kind=='Idle';empty=kind=='Reload_Empty'
 # Empty uses the same contact sequence, with a separate charging-handle tail.
 length=7.5 if empty else 6.5
 tilt=0 if idle else seq(t,[(0,0),(.5,1),(5.65,1),(6.4,0)])
 W=levelW@trx((0,.06,-.02))@trx((0,.015*tilt,.012*tilt))@rot('Y',-13*tilt)@rot('X',-9*tilt)
 coverAngle=0 if idle else seq(t,[(0,0),(.65,0),(1.12,108),(5.25,108),(5.72,0),(length,0)])
 coverM=around(hinge,rot('X',coverAngle))
 oldOut=0 if idle else ramp(t,2.3,3.15)
 newIn=0 if idle else ramp(t,3.65,4.35)
 oldBox=trx(off*oldOut)@around(boxPivot,rot('Y',-20*oldOut))
 newBox=trx(off*(1-newIn))@around(boxPivot,rot('Y',-20*(1-newIn)))
 oldLift=0 if idle else seq(t,[(0,0),(1.35,0),(1.65,1),(2.12,1),(2.4,0)])
 newLift=0 if idle else seq(t,[(0,0),(3.8,0),(4.18,1),(4.75,1),(5.1,0)])
 oldPts,oldBelt=belt_pose(oldBox,(-.025*oldLift,0,.052*oldLift))
 if empty:oldPts,oldBelt=belt_pose(oldBox@trx(off),(0,0,0))
 newPts,newBelt=belt_pose(newBox,(-.022*newLift,0,.048*newLift))
 if not idle:
  for key,pts,matrices,box in [('old',oldPts,oldBelt,oldBox),('new',newPts,newBelt,newBox)]:
   if key not in dynamics:dynamics[key]=BeltDynamics(centers)
   solved=dynamics[key].step(t,pts,W@fit,box)
   for i in range(6):
    pts[i]=solved[i]
   for i in range(14):
    j=i+1 if i<13 else i-1
    q=(centers[j]-centers[i]).rotation_difference(pts[j]-pts[i])
    matrices[i]=trx(pts[i])@q.to_matrix().to_4x4()@trx(-centers[i])
 charge=0 if not empty else seq(t,[(0,0),(6.03,0),(6.27,.055),(6.45,0),(7.5,0)])
 desired={n:m.copy() for n,m in base.items()};desired['WPN_root']=W
 deltas={'PKM_Cover':coverM,'PKM_Tray':Matrix.Identity(4),'PKM_Box':oldBox,'PKM_BoxLid':oldBox,'PKM_Charge':trx((0,charge,0)),'PKM_Trigger':Matrix.Identity(4),'PKM_Latch':trx((0,0,-.0018*(1 if .57<t<.78 and not idle else 0))),'PKM_InnerCarrier':trx((0,charge*.75,0)),'PKM_BeltRoot':oldBox,'PKM_EmptyLink':Matrix.Identity(4)}
 for i,m in enumerate(oldBelt):deltas[f'PKM_Belt_{i:02}']=m
 for name in mechanicRest:
  if name!='WPN_root':desired[name]=W@fit@deltas[name]@mechanicRest[name]
 for name in dupeNames:
  m=newBelt[int(name.rsplit('_',1)[1])] if name.startswith('PKM_Belt_') else newBox
  desired['New_'+name]=W@fit@m@mechanicRest[name]

 # Reachable support on the receiver's left/front flank above the box.
 # Dorsal normal points outward; fingertips curl inward around the front edge.
 LH=contact('l',(.055,-.018,.012),(0,-1,-.05),(1,0,0),W)
 RH=W@trx((0,-.004,.025))@baseW.inverted()@base['hand_r']
 if idle:
  left,right=LH,RH;lopen=.03;ropen=0
 else:
  LC=contact('l',(0,.285,.111),(0,-1,0),(0,0,1),W)
  LCmove=W@fit@coverM@fit.inverted()@W.inverted()@LC
  Lclear=contact('l',Vector((0,.038,.092)) if empty else oldPts[0]+Vector((0,0,.019)),(-1,0,0),(0,0,1),W)
  Loutside=contact('l',(.14,.10,.125),(0,-1,0),(0,0,-1),W)
  left=matrix_seq(t,[(0,LH),(.35,LH),(.65,LCmove),(1.12,LCmove),(1.25,LCmove),(1.38,Lclear),(1.65,Lclear),(1.9,Lclear),(2.12,Loutside),(2.3,LH),(length,LH)])
  lopen=seq(t,[(0,.03),(.5,.8),(.65,.5),(1.12,.5),(1.32,.7),(1.55,.25),(1.9,.25),(2.1,.85),(2.3,.03),(length,.03)])
  Rbox=contact('r',oldBox@Vector((-.120,.04,-.088)),(0,-.1,-1),(-1,0,0),W)
  RnewBox=contact('r',newBox@Vector((-.120,.04,-.088)),(0,-.1,-1),(-1,0,0),W)
  Rout=contact('r',(-.20,.16,-.07),(0,-.4,-1),(1,0,0),W)
  Runder=contact('r',(-.22,.25,-.22),(0,-.4,-1),(-1,0,0),W)
  Rbelt=contact('r',newPts[0]+Vector((0,0,.019)),(1,0,0),(0,0,1),W)
  Rcover=contact('r',(0,.275,.116),(0,-1,0),(0,0,1),W)
  RcoverMove=W@fit@coverM@fit.inverted()@W.inverted()@Rcover
  Rcharge=contact('r',(-.072,.115+charge,.023),(0,-.25,-1),(-1,0,0),W)
  keys=[(0,RH),(2.2,RH),(2.38,Rout),(2.6,Rbox),(3.15,Rbox),(3.4,Runder),(3.65,RnewBox),(4.35,RnewBox),(4.48,Rout),(4.66,Rbelt),(5.1,Rbelt),(5.25,RcoverMove),(5.72,RcoverMove),(5.9,Rout)]
  if empty:keys += [(6.02,Rcharge),(6.27,Rcharge),(6.45,Rcharge),(6.68,Rout),(7.15,RH),(7.5,RH)]
  else:keys += [(6.3,RH),(6.5,RH)]
  right=matrix_seq(t,keys)
  ropen=seq(t,[(0,0),(2.2,0),(2.38,.6),(2.6,.16),(4.35,.16),(4.5,.8),(4.68,.3),(5.1,.3),(5.25,.82),(5.72,.82),(5.9,.6),(6.03,.1 if empty else .3),(6.45,.1 if empty else 0),(6.8,.7 if empty else 0),(7.15,0)])
 bodyMove=Vector((0,-.055,-.02))
 solve_arm('l',left,lopen,desired,bodyMove+Vector((0,.035,0)));solve_arm('r',right,ropen,desired,bodyMove)
 support=1 if idle else seq(t,[(0,1),(.35,1),(.65,0),(2.12,0),(2.3,1),(length,1)])
 if support>0:support_fingers(desired,W,support)
 # Existing marker bones follow the new weapon, with explicit source-model endpoints.
 for name,p in {'WPN_SOCKET_Muzzle':(0,-.609,.044),'WPN_FrontSight':(0,-.535,.109),'WPN_RearSight':(0,.22,.106),'WPN_SOCKET_Eject':(.028,.11,.024)}.items():
  m=W.copy();m.translation=W@(fit@Vector(p));desired[name]=m
 return desired

actions=[]
for kind,duration in [('Idle',1.0),('Reload_Normal',6.5),('Reload_Empty',7.5)]:
 dynamics.clear()
 a=bpy.data.actions.new('PKM_'+kind);a.use_fake_user=True;r.animation_data_create();r.animation_data.action=a
 previous={};frames=round(duration*60)
 for frame in range(frames+1):
  desired=frame_pose(frame/60,kind)
  for name,p in desired.items():
   parent=parents[name]
   localRest=rest[parent].inverted()@rest[name] if parent else rest[name]
   localPose=desired[parent].inverted()@p if parent else p
   m=localRest.inverted()@localPose;loc,q,scl=m.decompose()
   if name in previous and previous[name].dot(q)<0:q.negate()
   previous[name]=q.copy();b=r.pose.bones[name];b.location=loc;b.rotation_quaternion=q;b.scale=scl
   for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=frame,group=name)
 for layer in a.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in bag.fcurves:
     for k in curve.keyframe_points:k.interpolation='LINEAR'
 scene.frame_start=0;scene.frame_end=frames;scene.frame_set(0)
 select([r]);bpy.ops.export_scene.fbx(filepath=str(OUT/('A_PKM_'+kind+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,bake_anim_step=1)
 actions.append({'action':a.name,'fps':60,'frames':frames+1,'seconds':duration,'loop':kind=='Idle'})
 print('PKM_ANIMATION_AUTHORED',kind,flush=True)

r.animation_data.action=bpy.data.actions['PKM_Reload_Normal'];r.animation_data.action_slot=r.animation_data.action.slots[0]
scene.frame_start=0;scene.frame_end=390;scene.frame_set(0)
scene.timeline_markers.clear()
for label,t in [('Left_Cover_Contact',.65),('Cover_Open',1.12),('Left_Belt_Clear',1.65),('Left_Support_Handoff',2.3),('Old_Box_Away',3.15),('New_Box_Seated',4.35),('Right_Belt_Seated',5.1),('Cover_Closed',5.72),('Grip_Return',6.3)]:scene.timeline_markers.new(label,frame=round(t*60))
select(weapons+[hands,r]);bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'PKM_Manny_Reload_Editable.blend'))
bpy.ops.export_scene.fbx(filepath=str(OUT/'SK_PKM_Manny.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,use_mesh_modifiers=True,mesh_smooth_type='FACE',path_mode='COPY',embed_textures=True)
# Export only these three candidate actions, without donor clips.
for act in list(bpy.data.actions):
 if act.name not in [x['action'] for x in actions] and act.users==0:bpy.data.actions.remove(act)
report={'hand_source':str(SRC),'hand_mesh':hands.name,'donor_pose':'M4_idle frame 0','reference':'https://www.bilibili.com/video/BV1jHeA6sEmj/','fit_matrix':[list(v) for v in fit],'animations':actions,'old_new_box_and_belt':True,'arm_bone_lengths_scaled':False,'donor_roll_correction_degrees':math.degrees(donor_roll),'visual_tested':False,'game_integrated':False,'limitations':['Reference-informed adaptation, not a captured animation','Belt secondary dynamics baked at 240 Hz; no live physics','Runtime sound and replenishment timings retained from Integration04','Authoring receipt only; see mesh_reimport.json and motion_import.json for import completion']}
(OUT/'animation_manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('PKM_ANIMATION_COMPLETE',flush=True)
