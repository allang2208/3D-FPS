from pathlib import Path
import runpy,pickle,numpy as np
r=Path(__file__).resolve().parent;s=runpy.run_path(str(r/'fit.py'),run_name='fit_module')
src=(r/'depths.py').read_text();ns={};exec(src[src.index('def winding'):src.index('for folder in sorted')],{'np':np},ns)
fitdata=pickle.load(open(r/'idle_fit.pkl','rb'))
for family in ['angled','canted','vertical','prism']:
 fit=s['Fit'](fitdata[family]['old_world'],family,stride=1);p=s['skin'](fit.pose(fitdata[family]['parameters']))
 for name,part in s['data']['parts'][family].items():
  if 'side_mag' in name:continue
  one=s['Fit'](fitdata[family]['old_world'],family,[name],1);d,_=one.measure(p,one.sample);ids=np.flatnonzero(d>.03)
  if not len(ids):continue
  wn=ns['winding'](p[ids],part['vertices'][part['faces']]);inside=wn>.65
  print('CONFIRM',family,name,'candidates',len(ids),'confirmed',int(inside.sum()),'max',float(d[ids][inside].max(initial=0)),'winding_max',float(wn.max()),flush=True)
