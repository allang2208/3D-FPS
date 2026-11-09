from pathlib import Path
import runpy,pickle,numpy as np,itertools
r=Path(__file__).resolve().parent;n=runpy.run_path(str(r/'guard_fit.py'),run_name='grid_probe');F=n['FineFit'];s=n['s'];data=pickle.load(open(r/'base_guarded.pkl','rb'));baseline=pickle.load(open(r/'baseline.pkl','rb'))
key=next(k for k in data if 'side_reload.' in k[0]);row=data[key];fit=F(row['world'][0],'base',stride=1);peak=(0,None)
for k,t in enumerate(row['times']):
 if not 2.76<t<3.5:continue
 fit.reset(row['world'][k]);depth=fit.score(np.zeros(len(n['limits'])),True)['max_depth_cm']
 if depth>peak[0]:peak=(depth,k)
k=peak[1];w=row['world'][k];fit.reset(w);gun=s['rigid'](w[s['ix']['WPN_root']]);old=baseline[('base',key[0])]['world'][k];offset=gun[:3,:3].T@(w[s['ix']['hand_l'],:3,3]-old[s['ix']['hand_l'],:3,3]);points=s['skin'](fit.pose(np.zeros(len(n['limits']))));dep,near=fit.measure(points,fit.sample);ids=np.flatnonzero(near<.45)
best=(float(dep.max()),offset)
for length in [.1,.2]:
 for direction in itertools.product([-1,0,1],repeat=3):
  if not any(direction):continue
  target=np.array(direction)*length/np.linalg.norm(direction);x=np.zeros(len(n['limits']));x[:3]=target-offset;p=s['skin'](fit.pose(x));d,_=fit.measure(p[ids],ids);depth=float(d.max())
  if depth<best[0]:best=(depth,target)
x=np.zeros(len(n['limits']));x[:3]=best[1]-offset;d,_=fit.measure(s['skin'](fit.pose(x)),fit.sample)
print('PALM_GRID',row['times'][k],peak[0],float(d.max()),best[1].tolist(),flush=True)
