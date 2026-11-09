from pathlib import Path
import pickle,importlib.util,numpy as np,json,hashlib
r=Path(__file__).resolve().parent;previous=r.parent/'Contact25'
sp=importlib.util.spec_from_file_location('contact_motion',previous/'motion.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
sp=importlib.util.spec_from_file_location('contact_settle',previous/'settle_motion.py');q=importlib.util.module_from_spec(sp);sp.loader.exec_module(q)
d=pickle.load(open(r/'current.pkl','rb'));m.s['d']=d
out={}
for family,profile in d['profiles'].items():
 for path,c in d['clips'].items():
  row=next((v for v in profile['clips'] if v['base']==path),None)
  if not row:continue
  times=np.unique(np.round(np.r_[c['times'],*[v['times'] for v in row['tracks']]],6))
  times=np.clip(times,0,c['duration']);times=np.unique(times)
  raw=q.interpolate(np.array(c['times']),np.array(c['frames']),times)
  out[(family,path)]=dict(times=times,world=m.world(m.layer(raw,path,family,times)))
pickle.dump(out,open(r/'baseline.pkl','wb'));print('CONTACT26_BASELINE',len(out),flush=True)
