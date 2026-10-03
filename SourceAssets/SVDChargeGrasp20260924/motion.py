import json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent
def ease(x):
 x=max(0.,min(1.,x));return x*x*x*(10+x*(-15+6*x))
def mix(a,b,w):
 p,q,s=a.decompose();p2,q2,s2=b.decompose();return Matrix.LocRotScale(p.lerp(p2,w),q.slerp(q2,w),s.lerp(s2,w))
def shifted(m,v):
 m=m.copy();m.translation+=Vector(v);return m
def frame(axis,normal):
 axis=axis.normalized();normal=normal-axis*normal.dot(axis)
 if normal.length<1e-6:normal=axis.orthogonal()
 normal.normalize();return Matrix((axis,normal.cross(axis).normalized(),normal)).transposed().to_quaternion()
class Motion:
 def __init__(self,poses,rest,parents):
  self.poses=poses;self.rest=rest;self.parents=parents
  self.lr={n:rest[parents[n]].inverted()@m if parents[n] else m.copy() for n,m in rest.items()}
  fit=json.loads((O/'grasp_fit.json').read_text());self.hook=Matrix(fit['hand_in_root']);self.grip={n:Quaternion(q) for n,q in fit['finger_basis'].items()}
  self.opened={n:q.slerp(Quaternion(),.23) if 'metacarpal' not in n else q.copy() for n,q in self.grip.items()}
  self.fingers=list(self.grip)
  self.edited=['clavicle_r','upperarm_r','lowerarm_r','hand_r','upperarm_twist_01_r','upperarm_twist_02_r','lowerarm_twist_01_r','lowerarm_twist_02_r']+self.fingers
  if 'ik_hand_r' in rest:self.edited.append('ik_hand_r')
  rear=json.loads((O.parent/'RifleQuickMelee20260924/ArmRepairV2/rear_grip.json').read_text())
  self.rear=Matrix(rear['hand_in_root']);self.rear_fingers={n:Quaternion(q) for n,q in rear['finger_basis'].items()}
  self.entry=self.rear.copy();self.finish=self.rear.copy()
  self.closed=poses[0]['WPN_root'].inverted()@poses[0]['WPN_bolt']
  backtravel=(poses[344]['WPN_root'].inverted()@poses[344]['WPN_bolt']).translation-self.closed.translation
  self.pre=shifted(self.hook,(-.036,.022,.009));self.back=shifted(self.hook,backtravel);self.away=shifted(self.back,(-.05,.015,-.004))
  self.return_pre=shifted(self.rear,(-.055,.012,-.018))
  self.bound={f:{n:self.rear_fingers[n].copy() for n in self.fingers} for f in [268,432]}
 def pose(self,f,profile):
  old=self.poses[f];p={n:m.copy() for n,m in old.items()};W=old['WPN_root'];rest=self.rest;parents=self.parents
  rear_weight=ease((f-220)/24)*(1-ease((f-460)/55))
  if rear_weight>0 and not 268<f<432:
   p['hand_r']=mix(old['hand_r'],W@self.rear,rear_weight)
   for n in self.fingers:
    basis=self.lr[n].inverted()@old[parents[n]].inverted()@old[n];loc,q,scale=basis.decompose()
    p[n]=p[parents[n]]@self.lr[n]@Matrix.LocRotScale(loc,q.slerp(self.rear_fingers[n],rear_weight),scale)
  if 268<f<432:
   if f<294:local=mix(self.entry,self.pre,ease((f-268)/26))
   elif f<310:local=mix(self.pre,self.hook,ease((f-294)/16))
   elif f<=344:local=shifted(self.hook,(W.inverted()@old['WPN_bolt']).translation-self.closed.translation)
   elif f<364:local=mix(self.back,self.away,ease((f-344)/20))
   elif f<408:local=mix(self.away,self.return_pre,ease((f-364)/44))
   else:local=mix(self.return_pre,self.finish,ease((f-408)/24))
   H=W@local;p['hand_r']=H
   for n in self.fingers:
    if f<294:q=self.bound[268][n].slerp(self.opened[n],ease((f-268)/26))
    elif f<310:q=self.opened[n].slerp(self.grip[n],ease((f-294)/16))
    elif f<=344:q=self.grip[n].copy()
    elif f<358:q=self.grip[n].slerp(self.opened[n],ease((f-344)/14))
    else:q=self.opened[n].slerp(self.bound[432][n],ease((f-358)/74))
    basis=self.lr[n].inverted()@old[parents[n]].inverted()@old[n];loc,_,scale=basis.decompose()
    p[n]=p[parents[n]]@self.lr[n]@Matrix.LocRotScale(loc,q,scale)
  H=p['hand_r'];support=ease((f-220)/44)*(1-ease((f-460)/55))
  if support<=0:return p
  back,down,out=profile;un,fn,hn,cn='upperarm_r','lowerarm_r','hand_r','clavicle_r'
  A=old[un].translation+Vector((out,-back,-down))*support;T=H.translation
  a=(old[fn].translation-old[un].translation).length;b=(old[hn].translation-old[fn].translation).length
  direction=T-A;distance=direction.length;axis=direction.normalized()
  if distance>(a+b)*.985:A+=axis*(distance-(a+b)*.985);direction=T-A;distance=direction.length;axis=direction.normalized()
  # Anatomical support in camera/component space: elbow stays right and below
  # the wrist, independent of the receiver's animated bank and local axes.
  hand_local=(W.inverted()@H).translation
  outside=W@Vector((min(-.20,hand_local.x-.13),hand_local.y+.18,hand_local.z-.01))
  lower=Vector((max(.28,A.x+.18),A.y*.55+T.y*.45,min(A.z-.19,T.z-.14)))
  hint=outside.lerp(lower,.15)
  E0=old[fn].translation.lerp(hint,support);pole=E0-A;pole-=axis*pole.dot(axis)
  if pole.length<1e-7:pole=Vector((1,0,-1));pole-=axis*pole.dot(axis)
  along=(a*a-b*b+distance*distance)/(2*max(distance,1e-7));E=A+axis*along+pole.normalized()*math.sqrt(max(0,a*a-along*along))
  ru=(rest[fn].translation-rest[un].translation).normalized();rf=(rest[hn].translation-rest[fn].translation).normalized()
  width=rest['index_metacarpal_r'].translation-rest['pinky_metacarpal_r'].translation
  fd=frame(T-E,(H.to_quaternion()@rest[hn].to_quaternion().inverted())@width)@frame(rf,width).inverted()
  fq=fd@rest[fn].to_quaternion();uq=(frame(E-A,fd@width)@frame(ru,width).inverted())@rest[un].to_quaternion()
  for main,origin,q,oldaxis,newaxis in [(un,A,uq,old[fn].translation-old[un].translation,E-A),(fn,E,fq,old[hn].translation-old[fn].translation,T-E)]:
   transported=oldaxis.normalized().rotation_difference(newaxis.normalized())@old[main].to_quaternion()
   p[main]=Matrix.LocRotScale(origin,transported.slerp(q,support),old[main].to_scale())
   for suffix in ['01','02']:
    n=main[:-2]+'_twist_'+suffix+'_r';oldlocal=old[main].inverted()@old[n];rigid=rest[main].inverted()@rest[n]
    p[n]=p[main]@mix(oldlocal,rigid,support)
  p[cn].translation+=A-old[un].translation
  if 'ik_hand_r' in rest:p['ik_hand_r']=H.copy()
  return p
