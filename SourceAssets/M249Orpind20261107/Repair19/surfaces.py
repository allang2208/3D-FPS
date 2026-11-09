"""Reconstruct actual native mesh skin for requested left-hand contact review."""
from pathlib import Path
import pickle,sys,numpy as np
r=Path(__file__).resolve().parent;sys.path.insert(0,str(r.parent/'Repair06'))
from contact_sweep import matrix
label=sys.argv[1] if len(sys.argv)>1 else 'before'
g=pickle.load(open(r/'geometry.pkl','rb'));cache=pickle.load(open(r/(label+'_world.pkl'),'rb'))
names=g['names'];ix={n:i for i,n in enumerate(names)};v=np.array(g['vertices']);f=np.array(g['faces']);sec=np.array(g['sections']);ib=np.linalg.inv(matrix(g['bind']))
dom=np.array([max(ws,key=lambda p:p[1])[0] for ws in g['weights']]);left=np.array([n.endswith('_l') for n in names])[dom]
groups={}
for j,ws in enumerate(g['weights']):
    for b,w in ws:
        ids,vs=groups.setdefault(b,([],[]));ids.append(j);vs.append(np.r_[v[j],1]*w)
groups=[(b,np.array(ids),np.array(vs)) for b,(ids,vs) in groups.items()]
def skin(w):
    p=np.zeros_like(v);xf=w@ib
    for b,ids,values in groups:p[ids]+=values@xf[b,:3,:].T
    return p
def normalized(w):return w[:3,:3]/np.linalg.norm(w[:3,:3],axis=0)
def state(w,capacity):
    p=skin(w);root=w[ix['WPN_root']];q=normalized(root)
    p=(p-root[:3,3])@q;parts={}
    for name,part in g['parts'].items():
        if name.endswith('_30') and capacity!=30 or name.endswith('_45') and capacity!=45:continue
        bone='WPN_root' if name.endswith('Port') else 'WPN_SOCKET_Magazine';m=w[ix[bone]]
        points=np.array(part['vertices'])@normalized(m).T+m[:3,3]
        parts[name]=dict(vertices=(points-root[:3,3])@q,faces=np.array(part['faces']))
    return dict(vertices=p,parts=parts)
keep=np.array([not any(k in n for k in ('Belt','Box','Bipod','Glass','Reticle')) for n in g['slots']])[sec]
visible=f[keep];materials=np.isin(sec[keep],[7,8,9]).astype(int)
samples={}
times=[0,.30,.38,.46,.50,.55,.60,.65,.70,.72,.85,.93,1.0,1.84,2.22,2.55,2.70,2.75,2.80,2.85,2.90,2.98,3.08,3.18,3.28,3.42,3.62,3.8]
for capacity in (30,45):
    data=cache['reload_base']
    for t in times:
        k=np.argmin(abs(data['times']-t));samples[f'{capacity}_{t:.2f}']=state(data['world'][k],capacity)
with (r/(label+'_surfaces.pkl')).open('wb') as h:pickle.dump(dict(faces=visible,materials=materials,samples=samples,left=left,allfaces=f,sections=sec,dominant=dom),h)
print('SIDE_MAG_SKIN_SAMPLES',label,len(samples),flush=True)
