import json,pickle
from pose import *
d=pickle.load(open(r/'current.pkl','rb'));B=matrix(d['bind']);report={}
for path,c in d['clips'].items():
    a=np.array(c['frames']);times=np.array(c['times'])
    for family,profile in d['profiles'].items():
        w=compose(layer(a,path,profile,d['names'],times),d['parents']);m=metrics(w,B,d['names'])
        key=path.split('.')[-1]+'/'+family
        report[key]={k:dict(max=float(abs(v).max()),at=float(times[abs(v).argmax()]),first=float(v[0]),last=float(v[-1])) for k,v in m.items()}
        if family=='base' or path.endswith('_idle'):print(key,report[key],flush=True)
(r/'diagnosis.json').write_text(json.dumps(report,indent=2))
