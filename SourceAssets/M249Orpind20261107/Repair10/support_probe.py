"""Fit the shared return contact to the actual factory foregrip surface."""
from pathlib import Path
import numpy as np,pickle,json,sys,trimesh
from motion import *
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'Repair06'))
from contact_sweep import intersect
r=Path(__file__).resolve().parent;g=pickle.load(open(r/'geometry.pkl','rb'));m=pickle.load(open(r/'m249_inputs.pkl','rb'))
names=m['names'];parents={n:(names[p] if p>=0 else None) for n,p in zip(names,m['parents'])}
B={n:matrix(v) for n,v in zip(names,m['bind'])};L={n:matrix(v) for n,v in zip(names,m['frames'][0])};H=compose(names,parents,L)
v=np.array(g['vertices']);f=np.array(g['faces']);s=np.array(g['sections']);dom=np.array([max(ws,key=lambda a:a[1])[0] for ws in g['weights']])
hb=[]
for n in names:
    p=n
    while p and p!='hand_l':p=parents[p]
    if p:hb.append(n)
hand=np.array([n in hb for n in names])[dom];hf=f[hand[f].all(1)];handids=np.unique(hf)
p=np.zeros_like(v)
for i,n in enumerate(names):
    ids=np.array([k for k,w in enumerate(g['weights']) if any(j==i for j,_ in w)])
    if not len(ids):continue
    weights=np.array([sum(w for j,w in g['weights'][k] if j==i) for k in ids])
    p[ids]+=(np.c_[v[ids],np.ones(len(ids))]@(H[n]@np.linalg.inv(B[n])).T)[:,:3]*weights[:,None]
obstacles={}
for slot in ('M249_Factory_Foregrip','M249_Factory_Receiver','M249_Factory_Handguard'):
    fs=f[s==g['slots'].index(slot)];mesh=trimesh.Trimesh(p,fs,process=False);obstacles[slot]=(mesh,mesh.triangles,mesh.triangles.min((0,1)),mesh.triangles.max((0,1)))
def collisions(q):
    tri=q[hf];mi=tri.min(1);ma=tri.max(1);hits={}
    for slot,(mesh,t,lo,hi) in obstacles.items():
        count=0
        for j in np.nonzero(((ma>=lo)&(mi<=hi)).all(1))[0]:
            for k in mesh.triangles_tree.intersection(np.r_[mi[j],ma[j]]):
                if intersect(tri[j],t[k]):count+=1;break
        hits[slot]=count
    return hits
result=[]
for dz in (0.,-1.,-2.,-3.,-4.):
    for dx in (0.,-1.,-2.,-3.):
        for dy in (0.,-1.,-2.):
            shift=np.array([dx,dy,dz]);q=p.copy();q[handids]+=shift;hits=collisions(q)
            result.append(dict(shift=shift.tolist(),hits=hits,total=sum(hits.values())))
result.sort(key=lambda a:(a['total'],np.linalg.norm(a['shift'])))
(r/'support_probes.json').write_text(json.dumps(result,indent=2));print(result[:12],flush=True)
