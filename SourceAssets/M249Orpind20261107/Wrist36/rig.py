"""Joint-only M249 authoring. This module never writes meshes or assets."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
from pathlib import Path
import sys,pickle,json,gzip
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.optimize import minimize
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'Wrist33'))
from pose import matrix,rot,unit,compose,encode,layer,sample,metrics
d=pickle.load(open(ROOT.parent/'Wrist33/current.pkl','rb'))
g=pickle.load(open(ROOT.parent/'Wrist33/geometry.pkl','rb'))
names=d['names'];ix={n:i for i,n in enumerate(names)};parents=d['parents'];B=matrix(d['bind']);invB=np.linalg.inv(B)
vertices=np.array(g['vertices']);faces=np.array(g['faces']);sections=np.array(g['sections'])
dominant=np.array([max(ws,key=lambda a:a[1])[0] for ws in g['weights']])
groups={}
for i,ws in enumerate(g['weights']):
    for b,v in ws:
        ids,pts=groups.setdefault(b,([],[]));ids.append(i);pts.append(np.r_[vertices[i],1]*v)
groups=[(b,np.array(ids),np.array(pts)) for b,(ids,pts) in groups.items()]
def skin(w):
    p=np.zeros_like(vertices);xf=w@invB
    for b,ids,pts in groups:p[ids]+=pts@xf[b,:3,:].T
    return p
def payload(f):
    folder='Wrist35' if f=='prism' else 'Wrist34'
    return json.load(gzip.open(ROOT.parent/folder/(f+'.json.gz'),'rt'))
def ease(x):
    x=np.clip(x,0,1);return x*x*(3-2*x)
def frame(x,z):
    x=unit(x);z=unit(z-x*(x@z));return np.column_stack((x,np.cross(z,x),z))
def indices(side):
    cl,ua,la,ha=[ix[n+'_'+side] for n in ['clavicle','upperarm','lowerarm','hand']]
    arm=[ix[n+'_'+side] for n in ['upperarm','upperarm_twist_01','upperarm_twist_02','lowerarm','lowerarm_twist_01','lowerarm_twist_02']]
    hand=[i for i,n in enumerate(names) if n.endswith('_'+side) and (n.startswith(('thumb','index','middle','ring','pinky')) or n=='hand_'+side)]
    return cl,ua,la,ha,arm,hand
def solve(w,x,side='l',shift=None,hand_rotation=None,station_weight=1.):
    cl,ua,la,ha,arm,hand=indices(side);out=w.copy()
    shift=np.zeros(3) if shift is None else shift
    hand_rotation=np.eye(3) if hand_rotation is None else hand_rotation
    a0,e0,h0=[w[i,:3,3] for i in [ua,la,ha]]
    for i in hand:
        out[i,:3,:3]=hand_rotation@w[i,:3,:3]
        out[i,:3,3]=h0+shift+hand_rotation@(w[i,:3,3]-h0)
    c=w[cl,:3,3];delta=R.from_rotvec(x[:3]).as_matrix();a=c+delta@(a0-c);h=out[ha,:3,3]
    out[cl,:3,:3]=delta@w[cl,:3,:3]
    lu=np.linalg.norm(e0-a0);ll=np.linalg.norm(h0-e0);direction=unit(h-a);dist=np.linalg.norm(h-a)
    along=(lu*lu-ll*ll+dist*dist)/(2*dist);radius=np.sqrt(max(1e-6,lu*lu-along*along));center=a+direction*along
    pole=unit(e0-center-direction*((e0-center)@direction));e=center+R.from_rotvec(direction*x[3]).as_matrix()@pole*radius
    n0=unit(np.cross(e0-a0,h0-e0));n=unit(np.cross(e-a,h-e))
    du=frame(e-a,n)@frame(e0-a0,n0).T;dl=frame(h-e,n)@frame(h0-e0,n0).T
    for i in arm:
        up=names[i].startswith('upperarm');q=du if up else dl;origin=a if up else e;old=a0 if up else e0
        out[i,:3,:3]=q@w[i,:3,:3];out[i,:3,3]=origin+q@(w[i,:3,3]-old)
    fore=unit(h-e);lower=rot(out[la])@rot(B[la]).T;hd=rot(out[ha])@rot(B[ha]).T
    q=R.from_matrix(hd@lower.T).as_quat();tau=(2*np.arctan2(q[:3]@fore,q[3])+np.pi)%(2*np.pi)-np.pi
    for b,share in [('lowerarm_twist_01',1.),('lowerarm_twist_02',.5)]:
        i=ix[b+'_'+side]
        target=R.from_rotvec(fore*tau*share).as_matrix()@lower@rot(B[i]);prior=rot(out[i])
        delta=(R.from_matrix(target)*R.from_matrix(prior).inv()).as_rotvec()
        out[i,:3,:3]=(R.from_rotvec(delta*station_weight).as_matrix()@prior)*np.linalg.norm(w[i,:3,:3],axis=0)
    return out
def bend(w,side='l'):
    cl,ua,la,ha,arm,hand=indices(side)
    fore=unit(w[ha,:3,3]-w[la,:3,3]);rest=unit(B[ha,:3,3]-B[la,:3,3]);wanted=rot(w[ha])@rot(B[ha]).T@rest
    return np.degrees(np.arccos(np.clip(fore@wanted,-1,1)))
def preserve_local(old,new,owned):
    a=encode(old,parents);b=encode(new,parents);a[:,owned,3:7]=b[:,owned,3:7]
    return compose(a,parents)
