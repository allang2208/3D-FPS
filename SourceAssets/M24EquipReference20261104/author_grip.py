"""Hold each fitted right grip during the rise, then return to its live bolt take."""
from pathlib import Path
import json,gzip,struct
import numpy as np
from scipy.spatial.transform import Rotation as R
O=Path(__file__).resolve().parent
D=json.load(gzip.open(O/'grip_inputs.json.gz','rt'))
fps=30;end=15/fps;hold=6/fps
identity=np.array([0.,0.,0.,0.,0.,0.,1.,0.,0.,0.])
def stamp(v):return struct.unpack('f',struct.pack('f',v))[0]
def mix(a,b,w):
    if w<=0:return a.copy()
    if w>=1:return b.copy()
    p=a+(b-a)*w;qa=R.from_quat(a[3:7]);qb=R.from_quat(b[3:7])
    p[3:7]=(qa*R.from_rotvec((qa.inv()*qb).as_rotvec()*w)).as_quat()
    return p
def sample(tr,t):
    if tr is None:return identity
    ts,vs=tr;i=np.searchsorted(ts,t,side='right')-1
    if i<0:return vs[0]
    if i+1>=len(ts):return vs[-1]
    return mix(vs[i],vs[i+1],(t-ts[i])/(ts[i+1]-ts[i]))
def effective(raw,delta):
    a=raw+delta;a[3:7]=(R.from_quat(delta[3:7])*R.from_quat(raw[3:7])).as_quat();return a
def mat(a):
    m=np.eye(4);m[:3,:3]=R.from_quat(a[3:7]).as_matrix()@np.diag(a[7:]);m[:3,3]=a[:3];return m
def trs(m):
    sc=np.linalg.norm(m[:3,:3],axis=0)
    return np.r_[m[:3,3],R.from_matrix(m[:3,:3]/sc).as_quat(),sc]
def pose(raw,tracks,t):
    loc={};comp={}
    for n,parent in D['parents'].items():
        loc[n]=effective(raw[n],sample(tracks.get(n),t))
        local=mat(loc[n]);comp[n]=(comp[parent]@local if parent else local)
    return loc,comp
def at(t):
    f=t*fps;i=min(int(f),15);return {n:mix(a,raw[i+1][n],f-i) for n,a in raw[i].items()}
raw=[{n:np.array(v) for n,v in row.items()} for row in D['raw']['equip']]
idle={n:np.array(v) for n,v in D['raw']['idle'][0].items()}
patch={}
for family,c in D['profiles'].items():
    data={role:{n:(np.array(tr['times']),np.array(tr['values']).reshape(-1,10)) for n,tr in tracks.items()} for role,tracks in c.items()}
    il,iw=pose(idle,data['idle'],0.);old=data['equip']
    # Carry the current idle hand with the receiver. Once the receiver has risen,
    # taper out the contact correction before the existing pull/lock cues.
    # Only clavicle translation supplies the arm's component-space placement.
    names=D['arm'];times={stamp(i/120) for i in range(61)}
    for n in names:
        if n in old:times.update(t for t in old[n][0] if t<=end)
    times=sorted(times);out={n:{'bone':n,'times':[],'values':[]} for n in names}
    for t in times:
        w=np.clip((t-hold)/(end-hold),0,1);w=w**3*(10+w*(-15+6*w))
        base=at(t);el,ew=pose(base,old,t)
        target_clav=np.linalg.inv(ew[D['parents']['clavicle_r']])@ew['WPN_root']@np.linalg.inv(iw['WPN_root'])@iw['clavicle_r']
        for n in names:
            target=trs(target_clav) if n=='clavicle_r' else il[n].copy()
            # Source bone scales include rig-specific bind offsets. Keep those
            # unchanged across the handoff; only position and rotation are owned.
            desired=mix(target,el[n],float(w));old_delta=sample(old.get(n),t)
            if t>=end-1e-8:delta=old_delta.copy()
            else:
                rot=(R.from_quat(desired[3:7])*R.from_quat(base[n][3:7]).inv()).as_quat()
                delta=np.r_[desired[:3]-base[n][:3],rot,old_delta[7:]]
            tr=out[n]
            q=delta[3:7]
            if tr['times'] and np.dot(q,tr['values'][-7:-3])<0:q*=-1
            tr['times'].append(float(t));tr['values'].extend(delta.tolist())
    for n in names:
        tr=out[n]
        if n in old:
            ts,vs=old[n]
            for t,v in zip(ts,vs):
                if t<=end+1e-8:continue
                a=v.copy()
                if np.dot(a[3:7],tr['values'][-7:-3])<0:a[3:7]*=-1
                tr['times'].append(float(t));tr['values'].extend(a.tolist())
        # Unchanged tracks are not republished. Missing identity tracks stay sparse.
        vs=np.array(tr['values']).reshape(-1,10)
        if n not in old and (np.max(abs(vs[:,:3]))<1e-6 and np.max(abs(vs[:,3:6]))<1e-6 and np.max(abs(vs[:,7:]))<1e-6):del out[n]
    patch[family]=out;print(family,len(out),flush=True)
with gzip.open(O/'grip_patch.json.gz','wt',compresslevel=2) as f:json.dump(patch,f,separators=(',',':'))
