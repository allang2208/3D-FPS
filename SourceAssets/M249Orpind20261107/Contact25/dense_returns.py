"""Check interpolated weighted hand skin and add keys only at missed contacts."""
from pathlib import Path
import pickle,runpy,numpy as np,json,sys
r=Path(__file__).resolve().parent
scope={'__file__':str(r/'fit_returns.py')};source=(r/'fit_returns.py').read_text();exec(compile(source.split('for (family,path),row')[0],str(r/'fit_returns.py'),'exec'),scope)
s=scope['s'];ReturnFit=scope['ReturnFit'];rows=scope['corrected'];results=scope['results']
# Blender has no SciPy: evaluate monotone cubic Hermite curves explicitly,
# using the same Fritsch-Carlson derivatives as scipy.interpolate.PchipInterpolator.
def pchip(t,y,x):
 h=np.diff(t);delta=np.diff(y,axis=0)/h[:,None];d=np.zeros_like(y)
 for k in range(1,len(t)-1):
  mask=(delta[k-1]*delta[k])>0;w1=2*h[k]+h[k-1];w2=h[k]+2*h[k-1]
  d[k,mask]=(w1+w2)/(w1/delta[k-1,mask]+w2/delta[k,mask])
 for k,a,b,ha,hb in [(0,0,1,h[0],h[1]),(-1,-1,-2,h[-1],h[-2])]:
  dd=((2*ha+hb)*delta[a]-ha*delta[b])/(ha+hb);dd[np.sign(dd)!=np.sign(delta[a])]=0
  mask=(np.sign(delta[a])!=np.sign(delta[b]))&(abs(dd)>3*abs(delta[a]));dd[mask]=3*delta[a,mask];d[k]=dd
 k=np.clip(np.searchsorted(t,x)-1,0,len(t)-2);u=(x-t[k])/h[k]
 return (2*u**3-3*u*u+1)*y[k]+(u**3-2*u*u+u)*h[k]*d[k]+(-2*u**3+3*u*u)*y[k+1]+(u**3-u*u)*h[k]*d[k+1]
def reset(fit,w,tm):
 fit.original=w.copy();fit.root=s['rigid'](w[s['ix']['WPN_root']]);fit.w=np.linalg.inv(fit.root)@w;fit.local=fit.w.copy()
 if hasattr(fit,'wrist_lock_curve'):fit.fixed_wrist=pchip(fit.wrist_lock_curve['times'],fit.wrist_lock_curve['values'],tm)
 for i,p in enumerate(s['parents']):
  if p>=0:fit.local[i]=np.linalg.inv(fit.w[p])@fit.w[i]
wanted=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
report_path=r/('dense_'+('_'.join(wanted) or 'all')+'.json')
report=json.loads(report_path.read_text()) if report_path.exists() else {}
locks=pickle.load(open(r/'wrist_lock.pkl','rb')) if (r/'wrist_lock.pkl').exists() else {}
for key,curve in results.items():
 family,path=key
 if wanted and family not in wanted:continue
 report_key=family+'/'+path.split('/')[-1]
 if report.get(report_key,{}).get('remaining_over_1_8mm')==0:
  print('DENSE_UNCHANGED_COMPLETE',report_key,flush=True);continue
 row=rows[key];end=3.14 if path.split('.')[0].endswith('_empty') else 3.50;ids=np.flatnonzero((row['times']>2.77)&(row['times']<end-.006));fit=ReturnFit(row['world'][ids[0]],family,stride=1)
 if key in locks:fit.wrist_lock_curve=locks[key]
 for iteration in range(8):
  failures=[];peak=0.;peak_t=0.
  for k in ids:
   tm=row['times'][k];reset(fit,row['world'][k],tm);x=pchip(curve['times'],curve['values'],tm);detail=fit.score(x,True);depth=detail['max_depth_cm']
   if depth>peak:peak=depth;peak_t=float(tm)
   if depth>.18:failures.append((depth,k,x))
  print('DENSE_RETURN',family,path.split('/')[-1],iteration,'peak',peak,'source',peak_t,'failures',len(failures),flush=True)
  if not failures or iteration==7:break
  picked=[]
  for depth,k,x in sorted(failures,key=lambda v:-v[0]):
   if any(abs(row['times'][k]-row['times'][j])<.012 for j in picked):continue
   picked.append(k);reset(fit,row['world'][k],row['times'][k])
   # Reuse nearby clear hand configurations before solving a new key. This
   # avoids trapping a fingertip on the opposite side of a thin magazine lip.
   nearby=abs(curve['times']-row['times'][k])<=.04
   seeds=[x,np.zeros_like(x)]+list(curve['values'][nearby])
   start=min(seeds,key=fit.score)
   xx,_,detail=fit.optimize(start,[(.16,4),(.08,2),(.04,1)])
   tm=float(row['times'][k]);kt=curve['times'];kv=curve['values'];match=np.flatnonzero(abs(kt-tm)<1e-6)
   if len(match):kv[match[0]]=xx
   else:
    at=np.searchsorted(kt,tm);curve['times']=np.insert(kt,at,tm);curve['values']=np.insert(kv,at,xx,axis=0)
   if len(picked)>=20:break
  pickle.dump(results,open(scope['fit_results_path'],'wb'))
 report[family+'/'+path.split('/')[-1]]=dict(max_depth_cm=peak,source=peak_t,remaining_over_1_8mm=len(failures),sample_rate_hz=120)
 report_path.write_text(json.dumps(report,indent=2))
