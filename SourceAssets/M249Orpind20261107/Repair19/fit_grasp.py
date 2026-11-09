"""Fit native palm/finger skin outside the shared upper magazine envelope."""
from pathlib import Path
import pickle,json,sys,numpy as np
from scipy.spatial import ConvexHull
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as R
r=Path(__file__).resolve().parent;sys.path.insert(0,str(r.parent/'Repair06'));from contact_sweep import matrix
g=pickle.load(open(r/'geometry.pkl','rb'));cache=pickle.load(open(r/'before_world.pkl','rb'))['reload_base'];surface=pickle.load(open(r/'before_surfaces.pkl','rb'))['samples']['30_0.72']
ns=g['names'];ix={n:i for i,n in enumerate(ns)};parents=g['parents'];B=matrix(g['bind']);invB=np.linalg.inv(B);base=cache['world'][86].copy();root=base[ix['WPN_root']];Q=root[:3,:3]/100;xf=np.eye(4);xf[:3,:3]=Q.T;xf[:3,3]=-Q.T@root[:3,3];base=xf@base
ls=[np.linalg.inv(base[p])@base[i] if p>=0 else base[i] for i,p in enumerate(parents)]
digits=[i for i,n in enumerate(ns) if n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky'))]
moving=[ix['hand_l'],*digits];dom=np.array([max(ws,key=lambda a:a[1])[0] for ws in g['weights']]);ids=np.where(np.isin(dom,moving))[0]
# Retain all skin landmarks for the final envelope check; use a deterministic
# subset for the nonlinear fit to keep the authoring solve small.
v=np.array(g['vertices'])[ids];groups=[]
lookup=np.full(len(g['vertices']),-1,dtype=int);lookup[ids]=np.arange(len(ids));hf=lookup[np.array(g['faces'])];hf=hf[(hf>=0).all(1)][::2]
for b in range(len(ns)):
    vals=[(j,w) for j,i in enumerate(ids) for bone,w in g['weights'][i] if bone==b]
    if vals:
        js=np.array([j for j,w in vals]);groups.append((b,js,np.c_[v[js],np.ones(len(js))]*np.array([w for j,w in vals])[:,None]))
adjust=[i for i in digits if ns[i].split('_')[-2] in ('01','02','03')];axes=[]
for i in adjust:
    bindlocal=np.linalg.inv(B[parents[i]])@B[i];ar=bindlocal[:3,:3]/np.linalg.norm(bindlocal[:3,:3],axis=0);cr=ls[i][:3,:3]/np.linalg.norm(ls[i][:3,:3],axis=0);rv=R.from_matrix(ar.T@cr).as_rotvec();axes.append(rv/max(np.linalg.norm(rv),1.e-12))
mag=np.array(surface['parts']['SM_m249_side_mag_30']['vertices']);hull=ConvexHull(mag);planes=hull.equations
tips={finger:np.nonzero(dom[ids]==ix[finger+'_03_l'])[0] for finger in ('thumb','index','middle','ring','pinky')}
def skin(x):
    w=base.copy();w[ix['hand_l'],:3,3]+=x[:3]
    w[ix['hand_l'],:3,:3]=R.from_rotvec(x[3:6]).as_matrix()@w[ix['hand_l'],:3,:3]
    edits={i:R.from_rotvec([0,0,x[6+j]]).as_matrix() for j,i in enumerate(adjust)}
    for i in digits:
        a=ls[i].copy()
        if i in edits:a[:3,:3]=edits[i]@a[:3,:3]
        w[i]=w[parents[i]]@a
    transform=w@invB;p=np.zeros_like(v)
    for b,js,values in groups:p[js]+=values@transform[b,:3,:].T
    return p
def distance(p):return (p@planes[:,:3].T+planes[:,3]).max(1)
original=skin(np.zeros(6+len(adjust)))
padids={}
padtargets={}
for finger,j in tips.items():
    sd=distance(original[j]);chosen=j[np.argsort(np.abs(sd))[:max(3,len(j)//6)]];padids[finger]=chosen
    center=original[chosen].mean(0);values=center@planes[:,:3].T+planes[:,3];plane=planes[values.argmax()];padtargets[finger]=center+plane[:3]*(.10-values.max())
def residual(x):
    p=skin(x);sd=distance(p);surface_distance=distance(np.r_[p,p[hf].mean(1)]);pen=np.minimum(surface_distance-.18,0)*40
    # A fingertip patch, rather than a bone origin, establishes each contact.
    contact=np.concatenate([(p[j].mean(0)-padtargets[f])*2. for f,j in padids.items()])
    return np.r_[pen,contact,x[:3]*.1,x[3:6]*2.,x[6:]*.35]
x=np.zeros(6+len(adjust));initial=distance(skin(x));x[2]=.5
sol=least_squares(residual,x,bounds=(np.r_[[-3,-3,-2],[-.35]*3,[-.8]*len(adjust)],np.r_[[3,3,3],[.35]*3,[.8]*len(adjust)]),max_nfev=180,ftol=1.e-7,xtol=1.e-7,gtol=1.e-6)
final=distance(skin(sol.x));data=dict(offset_cm=sol.x[:3].tolist(),palm_rotvec=sol.x[3:6].tolist(),finger_hinge_z={ns[i]:float(sol.x[6+j]) for j,i in enumerate(adjust)},initial_envelope_penetration_cm=float(max(0,-initial.min())),final_envelope_penetration_cm=float(max(0,-final.min())),cost=float(sol.cost),iterations=int(sol.nfev))
(r/'grasp_fit.json').write_text(json.dumps(data,indent=2));print(json.dumps(data,indent=2),flush=True)
