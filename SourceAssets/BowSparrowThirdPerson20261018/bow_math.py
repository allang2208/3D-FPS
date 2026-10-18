import gzip,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

O=Path(__file__).parent
def read(name):
 with gzip.open(O/name,'rt',encoding='utf-8') as f:return json.load(f)
def unit(v):return np.asarray(v)/max(float(np.linalg.norm(v)),1e-12)
def mul(a,b):
 a,b=np.asarray(a),np.asarray(b)
 return np.r_[a[3]*b[:3]+b[3]*a[:3]+np.cross(a[:3],b[:3]),a[3]*b[3]-np.dot(a[:3],b[:3])]
def inv(q):return np.r_[-q[:3],q[3]]
def rot(q,v):
 v=np.asarray(v);return v+2*np.cross(q[:3],np.cross(q[:3],v)+q[3]*v)
def compose(a,b):return np.r_[a[:3]+rot(a[3:7],b[:3]),mul(a[3:7],b[3:7])]
def inverse(t):return np.r_[rot(inv(t[3:7]),-t[:3]),inv(t[3:7])]
def frame_xy(x,y):
 x=unit(x);y=unit(y-x*np.dot(x,y))
 return R.from_matrix(np.column_stack((x,y,np.cross(x,y)))).as_quat()
def between(a,b):
 a,b=unit(a),unit(b);dot=np.clip(np.dot(a,b),-1,1)
 if dot<-.99999:
  axis=np.cross(a,[1,0,0])
  if np.linalg.norm(axis)<.01:axis=np.cross(a,[0,1,0])
  return np.r_[unit(axis),0.]
 return unit(np.r_[np.cross(a,b),1+dot])
def fk(f,parents):
 w=np.asarray(f).copy()
 for i,p in enumerate(parents):
  if p>=0:
   w[i,:3]=w[p,:3]+rot(w[p,3:7],f[i,:3]*w[p,7:])
   w[i,3:7]=mul(w[p,3:7],f[i,3:7]);w[i,7:]=w[p,7:]*f[i,7:]
 return w
def local(w,parents):
 f=w.copy()
 for i,p in enumerate(parents):
  if p>=0:
   f[i,:3]=rot(inv(w[p,3:7]),w[i,:3]-w[p,:3])/w[p,7:]
   f[i,3:7]=unit(mul(inv(w[p,3:7]),w[i,3:7]));f[i,7:]=w[i,7:]/w[p,7:]
 return f
def slerp(a,b,t):
 b=np.where(np.sum(a*b,axis=-1,keepdims=True)<0,-b,b)
 dot=np.clip(np.sum(a*b,axis=-1,keepdims=True),-1,1);theta=np.arccos(dot)
 den=np.where(theta<1e-7,1,np.sin(theta))
 q=np.where(theta<1e-6,a*(1-t)+b*t,(a*np.sin((1-t)*theta)+b*np.sin(t*theta))/den)
 return q/np.linalg.norm(q,axis=-1,keepdims=True)
def blend(a,b,t):
 f=a*(1-t)+b*t;f[:,3:7]=slerp(a[:,3:7],b[:,3:7],t);return f
def smooth(t):
 t=np.clip(t,0,1);return t*t*(3-2*t)
def sample(c,t):
 if not isinstance(c['frames'],np.ndarray):c['frames']=np.asarray(c['frames'])
 a=c['frames'];p=np.clip(t/c['duration']*(len(a)-1),0,len(a)-1)
 i=int(p);return blend(a[i],a[min(i+1,len(a)-1)],p-i)

class Contacts:
 def __init__(self,target,equipment):
  self.d=target;self.e=equipment
  self.ix={n:i for i,n in enumerate(target['names'])};self.ei={n:i for i,n in enumerate(equipment['names'])}
  self.ref=np.asarray(target['reference']);self.bind=fk(self.ref,target['parents'])
  self.ebind=fk(np.asarray(equipment['reference']),equipment['parents']);self.mounts={};self.finger_cache={};self.descendants={}
  for side in ('l','r'):
   descendants=[];hand_index=self.ix['hand_'+side]
   for i in range(len(self.ref)):
    parent=target['parents'][i]
    while parent>=0:
     if parent==hand_index:descendants.append(i);break
     parent=target['parents'][parent]
   self.descendants[side]=descendants
   points=[]
   for bind,ix in ((self.ebind,self.ei),(self.bind,self.ix)):
    hand=bind[ix['hand_'+side]]
    points.append(np.array([rot(inv(hand[3:7]),bind[ix[n+'_01_'+side],:3]-hand[:3]) for n in ('index','middle','pinky')]))
   a,b=points;q=mul(frame_xy(b[1],b[0]-b[2]),inv(frame_xy(a[1],a[0]-a[2])))
   self.mounts[side]=np.r_[b.mean(0)-rot(q,a.mean(0)),q]
 def native_pose(self,role,phase):
  c=self.e['clips'][role]
  return fk(sample(c,phase*c['duration']),self.e['parents'])
 def frames(self,pose):
  grip=compose(self.mounts['l'],compose(inverse(pose[self.ei['hand_l'],:7]),pose[self.ei['bow_grip'],:7]))
  nock=compose(self.mounts['r'],compose(inverse(pose[self.ei['hand_r'],:7]),pose[self.ei['bow_nock'],:7]))
  return grip,nock
 def fingers(self,pose,side):
  # Same anatomical frame and bounded finger IK as FPSPlayerBodyGrip::Transfer.
  ix,ei,bind,ebind,ref=self.ix,self.ei,self.bind,self.ebind,self.ref
  hand=pose[ei['hand_'+side]];native=bind[ix['hand_'+side]];mount=self.mounts[side]
  key=(side,tuple(np.round(np.concatenate([np.r_[rot(inv(hand[3:7]),pose[ei[f'{digit}_{j:02d}_{side}'],:3]-hand[:3]),
       mul(inv(hand[3:7]),pose[ei[f'{digit}_{j:02d}_{side}'],3:7])] for digit in ('thumb','index','middle','ring','pinky') for j in (1,2,3)]),5)))
  if key in self.finger_cache:return self.finger_cache[key]
  frame=mul(mul(native[3:7],mount[3:7]),inv(hand[3:7]));desired={}
  def point(b):return native[:3]+rot(native[3:7],mount[:3]+rot(mount[3:7],rot(inv(hand[3:7]),pose[b,:3]-hand[:3])))
  for digit in ('thumb','index','middle','ring','pinky'):
   src=[ei[f'{digit}_{j:02d}_{side}'] for j in (1,2,3)];dst=[ix[f'{digit}_{j:02d}_{side}'] for j in (1,2,3)]
   for j in range(3):
    a,b=(j,j+1) if j<2 else (1,2)
    na=rot(inv(bind[dst[j],3:7]),bind[dst[b],:3]-bind[dst[a],:3])
    da=rot(inv(ebind[src[j],3:7]),ebind[src[b],:3]-ebind[src[a],:3])
    desired[dst[j]]=unit(mul(mul(frame,pose[src[j],3:7]),between(na,da)))
   root=bind[dst[0],:3];goal=point(src[2]);pole=point(src[1]);l1=np.linalg.norm(bind[dst[1],:3]-root);l2=np.linalg.norm(bind[dst[2],:3]-bind[dst[1],:3])
   axis=unit(goal-root);reach=np.clip(np.linalg.norm(goal-root),abs(l1-l2)+.001,l1+l2-.001)
   bend=unit(pole-root-axis*np.dot(pole-root,axis));along=(l1*l1-l2*l2+reach*reach)/(2*reach)
   joint=root+axis*along+bend*np.sqrt(max(0,l1*l1-along*along))
   spans=[joint-root,root+axis*reach-joint]
   for j in range(2):
    axislocal=rot(inv(bind[dst[j],3:7]),bind[dst[j+1],:3]-bind[dst[j],:3])
    desired[dst[j]]=unit(mul(between(rot(desired[dst[j]],axislocal),spans[j]),desired[dst[j]]))
  out=ref.copy();world=bind[:,3:7].copy()
  for i in self.descendants[side]:
   parent=self.d['parents'][i]
   pq=world[parent] if parent>=0 else np.array([0,0,0,1.]);q=ref[i,3:7]
   if i in desired:q=mul(inv(pq),desired[i])
   elif '_half_' in self.d['names'][i] and parent in desired:
    delta=mul(inv(ref[parent,3:7]),out[parent,3:7]);q=mul(slerp(np.array([0,0,0,1.]),inv(delta),.5),q)
   out[i,3:7]=unit(q);world[i]=unit(mul(pq,q))
  self.finger_cache[key]=out
  return out
