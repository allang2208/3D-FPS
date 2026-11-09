"""Small joint corrections: the wrist position and source time are immutable."""
from pathlib import Path
import numpy as np,pickle,json
from mathutils import Vector,Matrix
r=Path(__file__).resolve().parent;previous=r.parent/'Contact25'
s={'__file__':str(previous/'fit.py'),'__name__':'contact26_surface'}
exec(compile((previous/'fit.py').read_text(),str(previous/'fit.py'),'exec'),s)
# Include wrist/palm boundary vertices with mixed skinning weights as well.
ids=np.flatnonzero(s['hand_weight']>.01);g=s['g'];vertices=np.array(g['vertices'])[ids];groups={}
for j,i in enumerate(ids):
 for b,weight in g['weights'][i]:
  ii,pp=groups.setdefault(b,([],[]));ii.append(j);pp.append(np.r_[vertices[j],1.]*weight)
s.update(skin_ids=ids,bind_vertices=vertices,groups=[(b,np.array(ii),np.array(pp)) for b,(ii,pp) in groups.items()])
limits=np.array([.1,.1,.1,3.,3.,3.]+[16.]*len(s['params']),float)
import ctypes
windlib=ctypes.CDLL(str(r/'winding.dll'));windlib.winding.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p]
def native_winding(points,tri):
 p=np.ascontiguousarray(points,dtype=np.float64);t=np.ascontiguousarray(tri,dtype=np.float64);out=np.zeros(len(p));windlib.winding(p.ctypes.data,len(p),t.ctypes.data,len(t),out.ctypes.data);return out
wnscope={'winding':native_winding}

class FineFit(s['Fit']):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);self.winding_cache={};self.triangles={n:p['vertices'][p['faces']].astype(np.float64) for n,p in s['data']['parts'][self.family].items()}
 def inside_union(self,p):
  for name,tree,lo,hi in self.trees:
   if np.any(p<lo) or np.any(p>hi):continue
   votes=0
   for direction in self.directions:
    origin=Vector(p);count=0
    for _ in range(80):
     hit,n,fi,length=tree.ray_cast(origin,direction,1000.)
     if hit is None:break
     count+=1;origin=hit+direction*.0001
    votes+=count%2
   if votes>=2:return True
  return False
 def exit_delta(self,p,depth):
  hits=[tree.find_nearest(Vector(p)) for name,tree,lo,hi in self.trees]
  h=min(hits,key=lambda h:abs(h[3]-depth));return s['unit'](np.array(h[0])-p)*(depth+.035)
 def measure(self,points,indices):
  depths=np.zeros(len(points));near=np.full(len(points),100.)
  for name,tree,lo,hi in self.trees:
   query=np.flatnonzero(np.all(points>=lo-.1,axis=1)&np.all(points<=hi+.1,axis=1));candidates=[]
   for i in query:
    pt=Vector(points[i]);closest,normal,face,distance=tree.find_nearest(pt);near[i]=min(near[i],distance)
    if distance<=.015 or np.any(points[i]<lo) or np.any(points[i]>hi):continue
    votes=0
    for direction in self.directions:
     origin=pt.copy();count=0
     for _ in range(80):
      hit,n,fi,length=tree.ray_cast(origin,direction,1000.)
      if hit is None:break
      count+=1;origin=hit+direction*.0001
     votes+=count%2
    if votes>=2:candidates.append((i,distance))
   cache=self.winding_cache.setdefault(name,{})
   pending=[]
   for i,distance in candidates:
    # At less than half a millimetre, conservative parity clearance is small
    # enough to preserve the hand shape. Winding resolves deeper open-edge
    # false positives, which would otherwise pull the fingers unnecessarily.
    if distance<=.05:
     depths[i]=max(depths[i],distance);continue
    key=tuple(np.floor(points[i]/.025).astype(int))
    if distance>.05 and key in cache:
     if cache[key]:depths[i]=max(depths[i],distance)
    else:pending.append((i,distance,key))
   if pending:
    wn=wnscope['winding'](points[[i for i,d,k in pending]],self.triangles[name])
    for (i,distance,key),value in zip(pending,wn):
     inside=value>.65
     if inside:depths[i]=max(depths[i],distance)
     if distance>.05 and (value<.5 or value>.8):cache[key]=inside
  self.escape_targets={}
  for i in np.flatnonzero(depths>.015):
   delta=self.exit_delta(points[i],depths[i]);self.escape_targets[int(i)]=points[i]+delta;depths[i]=max(.015,np.linalg.norm(delta)-.035)
  return depths,near
 def pose(self,x):
  out=super().pose(x)
  if np.linalg.norm(x[:6])<1e-9:return out
  hand=s['ix']['hand_l'];a,e,h=[self.w[s['ix'][n],:3,3] for n in ['upperarm_l','lowerarm_l','hand_l']];target=out[hand,:3,3]
  axis0=s['unit'](h-a);axis=s['unit'](target-a);length=np.linalg.norm(target-a);u=np.linalg.norm(e-a);l=np.linalg.norm(h-e)
  swing=lambda v,w:np.array(Vector(v).rotation_difference(Vector(w)).to_matrix())
  pole=s['unit'](e-a-axis0*np.dot(e-a,axis0));pole=swing(axis0,axis)@pole;along=(u*u-l*l+length*length)/(2*length);elbow=a+axis*along+pole*np.sqrt(max(0,u*u-along*along));du=swing(e-a,elbow-a);df=swing(h-e,target-elbow)
  for bone in ['upperarm_l','upperarm_twist_01_l','upperarm_twist_02_l']:
   i=s['ix'][bone];out[i,:3,:3]=du@self.w[i,:3,:3];out[i,:3,3]=a+du@(self.w[i,:3,3]-a)
  axis=s['unit'](target-elbow);delta=s['rot'](out[hand])@s['rot'](self.w[hand]).T@df.T;quat=Matrix(delta).to_quaternion();angle=2*np.arctan2(np.dot(np.array([quat.x,quat.y,quat.z]),axis),quat.w)
  for bone,share in [('lowerarm_l',0.),('lowerarm_twist_02_l',.5),('lowerarm_twist_01_l',1.)]:
   i=s['ix'][bone];turn=s['spin'](axis,np.degrees(angle)*share)@df;out[i,:3,:3]=turn@self.w[i,:3,:3];out[i,:3,3]=elbow+turn@(self.w[i,:3,3]-e)
  return out
 def reset(self,w):
  self.original=w.copy();self.root=s['rigid'](w[s['ix']['WPN_root']]);self.w=np.linalg.inv(self.root)@w;self.local=self.w.copy()
  for i,p in enumerate(s['parents']):
   if p>=0:self.local[i]=np.linalg.inv(self.w[p])@self.w[i]
 def clip(self,x,rotate=True,translate=True):
  x=np.clip(x,-limits,limits)
  if not translate:x[:3]=0
  norm=np.linalg.norm(x[:3])
  if norm>.1:x[:3]*=.1/norm
  if not rotate:x[3:6]=0
  norm=np.linalg.norm(x[3:6])
  if norm>4:x[3:6]*=4/norm
  return x
 def score(self,x,details=False):
  x=self.clip(x);points=s['skin'](self.pose(x))[self.sample];depth,_=self.measure(points,self.sample)
  value=800*float(depth@depth)+8000*float(depth.max(initial=0))**2+.003*float(x[6:]@x[6:])+.04*float(x[3:6]@x[3:6])+40*float(x[:3]@x[:3])
  if details:return dict(score=value,max_depth_cm=float(depth.max(initial=0)),wrist_offset_cm=float(np.linalg.norm(x[:3])),rotation_deg=float(np.linalg.norm(x[3:6])),finger_max_deg=float(np.max(abs(x[6:]))))
  return value
 def optimize(self,start=None):
  x=np.zeros(len(limits)) if start is None else self.clip(start);before=self.score(x,True);best=before['score']
  for rotate,translate in [(False,False),(True,False),(True,True)]:
   if not rotate and np.linalg.norm(x[3:6])>0:continue
   active=list(range(6,len(x)))+(list(range(3,6)) if rotate else [])+(list(range(3)) if translate else [])
   for iteration in range(28):
    points=s['skin'](self.pose(x));dep,_=self.measure(points[self.sample],self.sample);selected=self.sample[dep>.015];depth=dep[dep>.015]
    if not len(selected):break
    targets=[]
    for i,distance in zip(selected,depth):
     targets.append(self.escape_targets[int(i)]-points[i])
    weight=np.maximum(1.,depth/max(depth.max()*.6,1e-8));J=[]
    for i in active:
     trial=x.copy();trial[i]+=.04;new=s['skin'](self.pose(trial));J.append(((new[selected]-points[selected])/.04*weight[:,None]).ravel())
    J=np.array(J).T;y=(np.array(targets)*weight[:,None]).ravel();reg=np.array([.005 if i>=6 else .04 for i in active]);step=np.linalg.solve(J.T@J+np.diag(reg*reg)+np.eye(len(active))*1e-6,J.T@y-reg*reg*x[active]);step=np.clip(step,-2.,2.)
    found=False
    for alpha in [1.,.5,.25,.125]:
     trial=x.copy();trial[active]+=step*alpha;trial=self.clip(trial,rotate,translate);cost=self.score(trial)
     if cost<best-1e-6:x,best=trial,cost;found=True;break
    if not found:break
   if self.score(x,True)['max_depth_cm']<=.025:break
  if self.score(x,True)['max_depth_cm']>.03 and not getattr(self,'rescuing',False):
   # A fingertip already inside a thin wall has a local nearest-surface
   # minimum. Try small coordinated curls across its three joints, rather
   # than moving the complete hand out and back around the magazine.
   seed=x.copy();cost=self.score(seed)
   for finger in ['thumb','index','middle','ring','pinky']:
    group=[6+i for i,p in enumerate(s['params']) if p['bone'].startswith(finger) and p['label']=='flex']
    for level in [-16.,-8.,-4.,0.,4.,8.,16.]:
     trial=seed.copy();trial[group]=level;trial=self.clip(trial);value=self.score(trial)
     if value<cost-1e-6:seed,cost=trial,value
   if self.score(seed,True)['max_depth_cm']>.03:
    for axis in range(3,6):
     for angle in [-2.,-1.,0.,1.,2.]:
      trial=seed.copy();trial[axis]=angle;trial=self.clip(trial);value=self.score(trial)
      if value<cost-1e-6:seed,cost=trial,value
   if cost<self.score(x)-1e-5:
    self.rescuing=True;x,_,_=self.optimize(seed);self.rescuing=False
  return x,before,self.score(x,True)

class ContactFit(FineFit):
 def optimize(self,start=None):
  x,before,after=super().optimize(start)
  if getattr(self,'rescuing',False) or after['max_depth_cm']<=.035:return x,before,after
  best=self.score(x)
  # Local coordinate polishing resolves changes of the nearest edge at thin
  # magazine walls. All candidates retain the original arm lengths.
  for step in [2.,1.,.5]:
   for sweep in range(2):
    for i in list(range(3,6))+list(range(3))+list(range(6,len(x))):
     for direction in [-1,1]:
      trial=x.copy();trial[i]+=direction*(step if i>=6 else step*.5 if i>=3 else .025);trial=self.clip(trial);cost=self.score(trial)
      if cost<best-1e-6:x,best=trial,cost
    if self.score(x,True)['max_depth_cm']<=.035:break
  return x,before,self.score(x,True)
