from pathlib import Path
import runpy,pickle,numpy as np,json,sys
from mathutils import Matrix
r=Path(__file__).resolve().parent;n=runpy.run_path(str(r/'fine_fit.py'),run_name='contact_fine');FineFit=n['FineFit'];s=n['s'];family=sys.argv[sys.argv.index('--')+1]
data=pickle.load(open(r/'baseline.pkl','rb'));checkpoint=r/(family+'_fit.pkl');state=pickle.load(open(checkpoint,'rb')) if checkpoint.exists() else {'curves':{},'reports':{}}
def ease(v):
 v=np.clip(v,0,1);return v*v*v*(v*(v*6-15)+10)
def weight(w,ref,path,t):
 hand=np.linalg.inv(s['rigid'](w[s['ix']['WPN_root']]))@w[s['ix']['hand_l']]
 distance=np.linalg.norm(hand[:3,3]-ref[:3,3]);angle=Matrix(s['rot'](hand)@s['rot'](ref).T).to_quaternion().angle*180/np.pi
 a=(1-ease((distance-.5)/3.5))*(1-ease((angle-4)/28))
 if path.split('.')[-1]=='A_M249_idle':a=1
 if '/SideMagazine' in path and t>2.76:
  end=3.14 if '_empty' in path else 3.5;a=ease(((t-2.76)/(end-2.76)-.7)/.3)
 return float(a)
idle_key=next(k for k in data if k[0]==family and k[1].split('.')[-1]=='A_M249_idle');idle=data[idle_key]['world'][0];fit=FineFit(idle,family,stride=1)
if 'idle' not in state:
 x,before,after=fit.optimize();state['idle']=dict(parameters=x,before=before,after=after);pickle.dump(state,open(checkpoint,'wb'));print('FINE_IDLE',family,after,flush=True)
xidle=state['idle']['parameters'];ref=np.linalg.inv(s['rigid'](idle[s['ix']['WPN_root']]))@idle[s['ix']['hand_l']]
state['reference_hand']=ref
for (fam,path),row in data.items():
 if fam!=family or '/SideMagazine' not in path:continue
 if state['reports'].get(path,{}).get('max_depth_cm',999)<=.03:continue
 ts=row['times'];w=row['world'];end=3.14 if '_empty' in path else 3.5
 ids=np.flatnonzero((ts>2.76)&(ts<end));prepared={}
 for k in ids:
  fit.reset(w[k]);prepared[k]=fit.root@fit.pose(xidle*weight(w[k],ref,path,ts[k]))
 curve=state['curves'].setdefault(path,dict(times=np.array([2.76,end]),values=np.zeros((2,len(xidle)))))
 for iteration in range(10):
  values=np.array([np.interp(ts,curve['times'],curve['values'][:,j]) for j in range(len(xidle))]).T;bad=[];peak=0.;pt=0.
  for k in ids:
   fit.reset(prepared[k]);detail=fit.score(values[k],True);depth=detail['max_depth_cm']
   if depth>peak:peak=depth;pt=float(ts[k])
   if depth>.03:bad.append((depth,k))
  print('FINE_RETURN',family,path.split('.')[-1],iteration,'max',peak,'source',pt,'remaining',len(bad),flush=True)
  if not bad or iteration==9:break
  picked=[]
  for depth,k in sorted(bad,reverse=True):
   if any(abs(ts[k]-ts[j])<.012 for j in picked):continue
   picked.append(k);fit.reset(prepared[k]);near=abs(curve['times']-ts[k])<.025
   seeds=[values[k],np.zeros(len(xidle))]+list(curve['values'][near]);start=min(seeds,key=fit.score);x,before,after=fit.optimize(start)
   kt=curve['times'];kv=curve['values'];match=np.flatnonzero(abs(kt-ts[k])<1e-6)
   if len(match):kv[match[0]]=x
   else:
    at=np.searchsorted(kt,ts[k]);curve['times']=np.insert(kt,at,ts[k]);curve['values']=np.insert(kv,at,x,axis=0)
   pickle.dump(state,open(checkpoint,'wb'))
   print('FINE_KEY',family,round(float(ts[k]),6),after,flush=True)
   if len(picked)>=30:break
 state['reports'][path]=dict(max_depth_cm=peak,source=pt,remaining=len(bad));pickle.dump(state,open(checkpoint,'wb'))
(r/(family+'_report.json')).write_text(json.dumps(dict(idle={k:v for k,v in state['idle'].items() if k!='parameters'},returns=state['reports']),indent=2))
print('FINE_FAMILY_COMPLETE',family,flush=True)
