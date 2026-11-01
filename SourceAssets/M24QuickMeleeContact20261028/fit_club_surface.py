"""Fit a native right-hand power grip to the actual M24 stock surface."""
from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text().split("\nif __name__=='__main__':")[0],'library','exec'))
import numpy as np
from mathutils import Euler
from mathutils.bvhtree import BVHTree
skin=bpy.data.objects['M24_V9_BareArms'];gun=bpy.data.objects['M24_base'];gun.data.calc_loop_triangles();bv=BVHTree.FromPolygons([v.co for v in gun.data.vertices],[t.vertices[:] for t in gun.data.loop_triangles],all_triangles=True)
idle,loc=pose('idle',0);M=rest['WPN_root']@idle['WPN_root'].inverted();pivot=Vector((0,-.115,.048));q=Quaternion((0,1,0),math.radians(75))@Quaternion((1,0,0),math.radians(90));H=Matrix.LocRotScale(pivot-q@Vector((0,0,.04)),q,Vector((1,1,1)))@M@idle['hand_r']
indices={n:i for i,n in enumerate(names)};gn=[g.name for g in skin.vertex_groups];V=np.array([(*v.co,1) for v in skin.data.vertices]);weights=np.zeros((len(V),len(names)))
for v in skin.data.vertices:
 for g in v.groups:
  if gn[g.group] in indices:weights[v.index,indices[gn[g.group]]]=g.weight
handbones=[n for n in names if under(n,'hand_r')];handids=[indices[n] for n in handbones];pure=weights[:,handids].sum(1)>.96;dom=weights.argmax(1);restinv=np.array([np.array(rest[n].inverted()) for n in names]);digits=[f'{d}_{j:02d}_r' for d in ('index','middle','ring','pinky','thumb') for j in (1,2,3)]
qs={n:loc[n].to_quaternion() for n in digits};basis={n:(local_rest[n].inverted()@loc[n]).to_euler() for n in digits}
for j in (1,2,3):basis[f'index_{j:02d}_r']=basis[f'middle_{j:02d}_r'].copy();qs[f'index_{j:02d}_r']=local_rest[f'index_{j:02d}_r'].to_quaternion()@basis[f'index_{j:02d}_r'].to_quaternion()
rays=[Vector((1,.073,.047)).normalized(),Vector((.031,1,.051)).normalized(),Vector((.047,.061,1)).normalized()]
def handrow(hand,rotations):
 out={n:m.copy() for n,m in rest.items()};out['hand_r']=hand
 for n in names:
  if n=='hand_r' or not under(n,'hand_r'):continue
  p,q,sc=loc[n].decompose();out[n]=out[parents[n]]@Matrix.LocRotScale(p,rotations.get(n,q),sc)
 return out
def sdf(X):
 ds=[]
 for x in X:
  p=Vector(x);_,_,_,d=bv.find_nearest(p);inside=0
  if d<.04:
   for direction in rays:
    hit,n,_,_=bv.ray_cast(p,direction);inside+=hit is not None and n.dot(direction)>0
  ds.append(d*1000*(-1 if inside>=2 else 1))
 return np.array(ds)
def bind(selected):return np.einsum('vk,kij,vj->kvi',weights[selected],restinv,V[selected],optimize=True)
def points(row,W):return np.einsum('kij,kvj->vi',np.array([np.array(row[n]) for n in names]),W,optimize=True)[:,:3]
# Fit palm and metacarpals before closing any individual digit.
palmids=[indices[n] for n in handbones if n=='hand_r' or 'metacarpal' in n]
thumbbase=(dom==indices['thumb_01_r'])&(np.linalg.norm(V[:,:3]-np.array(rest['thumb_01_r'].translation),axis=1)<.017)
selected=np.where(pure&(np.isin(dom,palmids)|thumbbase))[0][::5];W=bind(selected)
def palm_cost(delta):
 hh=H.copy();hh.translation+=Vector(delta);ds=sdf(points(handrow(hh,qs),W));pen=np.maximum(-ds-.3,0);near=np.sort(abs(ds))[:10]
 return float(12*np.mean(pen**2)+8*pen.max()**2+.35*np.mean((near-1.5)**2)+.004*(Vector(delta).length*1000)**2)
delta=[0,0,0];value=palm_cost(delta)
for x in (-.02,-.01,0,.01,.02):
 for y in (-.02,0,.02):
  for z in (-.03,-.02,-.01,0,.01):
   trial=[x,y,z];c=palm_cost(trial)
   if c<value:delta=trial;value=c
for step in (.005,.002):
 for _ in range(2):
  for axis in range(3):
   for sign in (-1,1):
    trial=list(delta);trial[axis]+=sign*step
    if any(abs(v)>.04 for v in trial):continue
    c=palm_cost(trial)
    if c<value:delta=trial;value=c
H.translation+=Vector(delta);print('PALM_FIT',delta,value,flush=True);report={}
for digit in ('middle','ring','pinky','index','thumb'):
 ns=[f'{digit}_{j:02d}_r' for j in (1,2,3)];selected=np.where(pure&np.isin(dom,[indices[n] for n in ns]))[0][::4];W=bind(selected);tip=dom[selected]==indices[ns[2]]
 if digit=='thumb':
  prior=handrow(H,qs)
  def swung(directions):
   rotations=dict(qs);current=handrow(H,rotations)
   for n,child,direction in zip(ns[:2],ns[1:],directions):
    target=Vector(direction).normalized();original=current[child].translation-current[n].translation
    rot=original.rotation_difference(target)@current[n].to_quaternion();rotations[n]=current[parents[n]].to_quaternion().inverted()@rot
    current=handrow(H,rotations)
   return current,rotations
  def thumbscore(directions,detail=False):
   current,_=swung(directions);ds=sdf(points(current,W));pen=np.maximum(-ds-.25,0);near=np.sort(abs(ds[tip]))[:8]
   angles=[math.degrees(prior[n].to_quaternion().rotation_difference(current[n].to_quaternion()).angle) for n in ns[:2]]
   val=float(20*np.mean(pen**2)+10*pen.max()**2+.7*np.mean((near-1.3)**2)+.004*sum(v*v for v in angles))
   return {'score':val,'penetration_mm':float(pen.max()),'tip_gap_mm':float(near.mean()),'swing_degrees':angles,'directions':directions} if detail else val
  best=None;val=1e30
  for x1 in (-1.5,-1,-.5,0,.5):
   for y1 in (-.5,0,.5,1):
    for x2 in (-1,-.5,0,.5):
     for y2 in (0,.5,1,1.5):
      d=((x1,y1,1),(x2,y2,1));v=thumbscore(d)
      if v<val:best=d;val=v
  values=[best[0][0],best[0][1],best[1][0],best[1][1]]
  for step in (.25,.1,.05):
   for _ in range(2):
    for axis in range(4):
     for sign in (-1,1):
      trial=list(values);trial[axis]+=sign*step;d=((trial[0],trial[1],1),(trial[2],trial[3],1));v=thumbscore(d)
      if v<val:values=trial;best=d;val=v
  _,qs=swung(best);report[digit]=thumbscore(best,True);print('THUMB_SWING',report[digit],flush=True);continue
 initial=[math.degrees(basis[n].z) for n in ns]+[math.degrees(basis[ns[0]].y)]
 if digit=='thumb':initial=[math.degrees(v) for v in basis[ns[0]]]+[math.degrees(basis[ns[1]].z),math.degrees(basis[ns[2]].z)]
 bounds=[(v-40,v+40) for v in initial];bounds[-1]=(initial[-1]-22,initial[-1]+22)
 if digit=='thumb':bounds=[(v-28,v+28) for v in initial]
 def trialpose(values):
  rotations=dict(qs)
  for j,n in enumerate(ns):
   e=basis[n].copy()
   if digit=='thumb':
    if j==0:e=Euler(tuple(math.radians(v) for v in values[:3]))
    else:e.z=math.radians(values[2+j])
   else:
    e.z=math.radians(values[j])
    if j==0:e.y=math.radians(values[3])
   rotations[n]=local_rest[n].to_quaternion()@e.to_quaternion()
  return handrow(H,rotations),rotations
 def score(values,details=False):
  row,_=trialpose(values);ds=sdf(points(row,W));pen=np.maximum(-ds-.25,0);near=np.sort(abs(ds[tip]))[:8]
  cost=float(20*np.mean(pen**2)+10*pen.max()**2+.7*np.mean((near-1.3)**2)+.015*np.sum((np.array(values)-initial)**2))
  return {'score':cost,'penetration_mm':float(pen.max()),'tip_gap_mm':float(near.mean()),'parameters':values} if details else cost
 best=list(initial);bestval=score(best)
 for step in (20,10,5,2):
  for _ in range(3):
   for axis in range(len(best)):
    for sign in (-1,1):
     values=list(best);values[axis]=max(bounds[axis][0],min(bounds[axis][1],values[axis]+sign*step));v=score(values)
     if v<bestval:best=values;bestval=v
 _,qs=trialpose(best);report[digit]=score(best,True);print('FINGER_FIT',digit,report[digit],flush=True)
result={'hand':[list(v) for v in H],'rotations':{n:list(q) for n,q in qs.items()},'palm_offset_m':delta,'contact':report};(O/'club_surface_fit.json').write_text(json.dumps(result,indent=2));print('CLUB_SURFACE_FIT_READY',flush=True)
