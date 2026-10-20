"""Diagnose/fit the thumb root with the approved V9 surface left untouched."""
from pathlib import Path
import sys,numpy as np,json
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'QuickMeleeSVDReferenceR2_20261019'))
from surface import *
O=HERE
poses=np.load(O/'poses.npz')['base'];h=ids['hand_r'];th=[ids['thumb_0'+str(i)+'_r'] for i in (1,2,3)]
_,first,weld=np.unique(np.round(V,5),axis=0,return_index=True,return_inverse=True)
T=weld[np.array(arms['triangles'])];counts=np.bincount(weld);bn=[names[j] for j in dom]
mask=np.array([sum(bn[j].endswith('_r') and bn[j].startswith(('hand','thumb','index','middle','ring','pinky')) for j in tr)>=2 for tr in arms['triangles']])
# Fixed axes in the native hand frame, so the thumb abducts as one chain.
p=poses[0];forward=unit(p[ids['middle_01_r'],:3,3]-p[h,:3,3]);side=unit(p[ids['index_metacarpal_r'],:3,3]-p[ids['pinky_metacarpal_r'],:3,3])
normal=unit(np.cross(forward,side));basis=rigid(p[h])[:3,:3].T@np.stack([normal,forward],axis=1)
def adjust(p,a,b,w=1.):
    C=rigid(p[h])[:3,:3];turn=(R.from_rotvec(C@basis[:,0]*np.deg2rad(a*w))*R.from_rotvec(C@basis[:,1]*np.deg2rad(b*w))).as_matrix()
    q=p.copy();pivot=p[th[0],:3,3]
    for j in th:q[j,:3,3]=pivot+turn@(p[j,:3,3]-pivot);q[j,:3,:3]=turn@p[j,:3,:3]
    return q
def folds(p):
    vv=skinned(arms,p,True);x=np.zeros((len(first),3));np.add.at(x,weld,vv);x/=counts[:,None]
    fn=np.cross(x[T[:,1]]-x[T[:,0]],x[T[:,2]]-x[T[:,0]]);vn=np.zeros_like(x)
    for k in range(3):np.add.at(vn,T[:,k],fn)
    vn/=np.maximum(np.linalg.norm(vn,axis=1)[:,None],1e-10)
    return int(((np.einsum('ij,ij->i',fn,vn[T].mean(1))<0)&mask).sum())
if __name__=='__main__':
    frames=[12,20,40,60,68,75,90]
    choices=[]
    for a in [-12,-8,-4,0,4,8,12]:
        for b in [-12,-8,-4,0,4,8,12]:
            values=[folds(adjust(poses[i],a,b)) for i in frames]
            choices.append({'a':a,'b':b,'folds':values,'score':sum(values)*1000+a*a+b*b})
    choices.sort(key=lambda c:c['score'])
    (O/'thumb-fit-search.json').write_text(json.dumps({'axes_hand_local':basis.tolist(),'frames':frames,'choices':choices},indent=2))
    print(json.dumps(choices[:8],indent=2),flush=True)
