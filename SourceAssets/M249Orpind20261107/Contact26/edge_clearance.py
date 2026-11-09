"""Small palm clearance, bounded against the user's accepted native path."""
from pathlib import Path
import runpy,pickle,numpy as np,json,sys,itertools
r=Path(__file__).resolve().parent;n=runpy.run_path(str(r/'guard_fit.py'),run_name='edge_clearance');F=n['FineFit'];s=n['s'];family=sys.argv[sys.argv.index('--')+1]
file=r/(family+'_native.pkl');backup=r/(family+'_before_edge.pkl')
if not backup.exists():backup.write_bytes(file.read_bytes())
data=pickle.load(open(backup,'rb'));fit=None;hand=s['ix']['hand_l'];directions=[np.array(v,dtype=float)/np.linalg.norm(v) for v in itertools.product([-1,0,1],repeat=3) if any(v)]
for path,rows in data.items():
 empty='_empty' in path;label='polished' if family=='canted' and empty else 'verified';folder=r.parent/'Contact25'/label/f'45_{"empty" if empty else "normal"}_{family}_left'
 j=json.loads((folder/'review.json').read_text());poses=np.fromfile(folder/'poses.f32',np.float32).reshape(-1,4+j['bone_count']*7);previous=np.zeros(3)
 for row in rows:
  original=poses[np.argmin(abs(poses[:,1]-row['time'])),4:].reshape(-1,7)[hand,:3].astype(float);row['accepted_hand_position']=original
  w=row['after_world'];fit=F(w,family,stride=1) if fit is None else fit;fit.reset(w);zero=np.zeros(len(n['limits']));points=s['skin'](fit.pose(zero));depth,near=fit.measure(points,fit.sample);initial=float(depth.max());root=fit.root;offset=root[:3,:3].T@(w[hand,:3,3]-original);best=(initial,offset.copy());possible=np.zeros(len(points),dtype=bool)
  for name,tree,lo,hi in fit.trees:possible|=np.all(points>=lo-.65,axis=1)&np.all(points<=hi+.65,axis=1)
  ids=np.flatnonzero(possible)
  if initial>.025:
   for radius in [.15,.25,.35]:
    for axis in directions:
     target=axis*radius;x=zero.copy();x[:3]=target-offset;p=s['skin'](fit.pose(x));dep,_=fit.measure(p[ids],ids);cost=float(dep.max())
     if cost<best[0]-1e-6 or (cost<.025 and best[0]<.025 and np.linalg.norm(target-previous)<np.linalg.norm(best[1]-previous)):best=(cost,target)
    if best[0]<=.025:break
   for step in [.05,.025]:
    for axis in np.eye(3):
     for sign in [-1,1]:
      target=best[1]+axis*step*sign;length=np.linalg.norm(target)
      if length>.35:target*=.35/length
      x=zero.copy();x[:3]=target-offset;p=s['skin'](fit.pose(x));dep,_=fit.measure(p[ids],ids);cost=float(dep.max())
      if cost<best[0]-1e-6:best=(cost,target)
   x=zero.copy();x[:3]=best[1]-offset;new=root@fit.pose(x);dep,_=fit.measure(s['skin'](fit.pose(x)),fit.sample);full=float(dep.max())
   if full<initial:
    row['after_world']=new;row['after']['max_depth_cm']=full;previous=best[1]
   else:previous=offset
  else:previous=offset
  print('EDGE_CLEARANCE',family,path.split('.')[-1],round(row['time'],6),round(initial,4),'->',round(row['after']['max_depth_cm'],4),'offset_mm',round(np.linalg.norm(row['after_world'][hand,:3,3]-original)*10,3),flush=True)
 pickle.dump(data,open(file,'wb'))
print('EDGE_COMPLETE',family,flush=True)
