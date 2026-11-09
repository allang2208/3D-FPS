from pathlib import Path
import runpy,pickle,numpy as np
r=Path(__file__).resolve().parent;s=runpy.run_path(str(r/'fit.py'),run_name='fit_module');rows=pickle.load(open(r/'corrected.pkl','rb'));src=(r/'depths.py').read_text();ns={};exec(src[src.index('def winding'):src.index('for folder in sorted')],{'np':np},ns)
for family,tm in [('vertical',3.1416667),('vertical',3.175),('angled',3.3166667),('base',3.125)]:
 key=next(k for k in rows if k[0]==family and 'side_reload.' in k[1]);row=rows[key];k=np.argmin(abs(row['times']-tm));w=row['world'][k];root=s['rigid'](w[s['ix']['WPN_root']]);points=s['skin'](np.linalg.inv(root)@w)
 for name,p in s['data']['parts'][family].items():
  fit=s['Fit'](w,family,[name],stride=1);depth,_=fit.measure(points,fit.sample);ids=np.flatnonzero(depth>.18)
  if not len(ids):continue
  ids=ids[np.argsort(depth[ids])[-64:]];wn=ns['winding'](points[ids],p['vertices'][p['faces']]);inside=wn>.65
  print('CONFIRMED',family,tm,name,'parity',float(depth[ids].max()),'winding',float(depth[ids][inside].max(initial=0)),'count',int(inside.sum()),flush=True)
