from pathlib import Path
import pickle,runpy,numpy as np
r=Path(__file__).resolve().parent;s=runpy.run_path(str(r/'fit.py'),run_name='fit_module');row=pickle.load(open(r/'idle_fit.pkl','rb'))['canted'];fit=s['Fit'](row['old_world'],'canted',[n for n in s['data']['parts']['canted'] if 'side_mag' not in n],stride=1)
for label,x in [('original',np.zeros(len(s['limits']))),('candidate',row['parameters'])]:
 p=s['skin'](fit.pose(x));depth,_=fit.measure(p,fit.sample)
 for bone in np.unique(s['dom']):
  ids=np.flatnonzero((s['dom']==bone)&(depth>.03))
  if len(ids):print(label,s['names'][bone],len(ids),float(depth[ids].max()),flush=True)
