"""Triangle-level left-arm / optic contact sweep over saved native animation keys."""
from pathlib import Path
import pickle,json
import numpy as np
from scipy.spatial.transform import Rotation
import trimesh
from numba import njit
r=Path(__file__).resolve().parent

@njit
def intersect(a,b):
    ea=np.empty((3,3));eb=np.empty((3,3))
    for i in range(3):ea[i]=a[(i+1)%3]-a[i];eb[i]=b[(i+1)%3]-b[i]
    na=np.cross(ea[0],ea[1]);nb=np.cross(eb[0],eb[1])
    axes=np.empty((17,3));axes[0]=na;axes[1]=nb;k=2
    for i in range(3):
        for j in range(3):axes[k]=np.cross(ea[i],eb[j]);k+=1
    for i in range(3):axes[k]=np.cross(na,ea[i]);axes[k+3]=np.cross(nb,eb[i]);k+=1
    for axis in axes:
        if np.dot(axis,axis)<1e-18:continue
        pa=a@axis;pb=b@axis
        if pa.max()<pb.min()-1e-8 or pb.max()<pa.min()-1e-8:return False
    return True

def matrix(values):
    a=np.asarray(values);m=np.zeros(a.shape[:-1]+(4,4));m[...,3,3]=1
    m[...,:3,:3]=Rotation.from_quat(a[...,3:7].reshape(-1,4)).as_matrix().reshape(a.shape[:-1]+(3,3))*a[...,None,7:]
    m[...,:3,3]=a[...,:3];return m

def run():
    d=pickle.load(open(r/'geometry.pkl','rb'));v=np.asarray(d['vertices']);f=np.asarray(d['faces']);names=d['names'];parents=d['parents']
    bind=matrix(d['bind']);invbind=np.linalg.inv(bind);slots=d['slots'];sections=np.asarray(d['sections'])
    dominant=np.array([max(row,key=lambda w:w[1])[0] for row in d['weights']])
    left=np.array([names[i].endswith('_l') for i in dominant]);lf=f[left[f].all(1)]
    optical=np.array([s in ('M249_OpticalHousing','M249_MagnifierGlass') for s in slots]);of=f[optical[sections]]
    optic=trimesh.Trimesh(vertices=v,faces=of,process=False);tree=optic.triangles_tree;tri=v[of];lo=tri.min((0,1));hi=tri.max((0,1))
    groups=[]
    for bone in np.unique(dominant[left]):
        ids=[];weights=[]
        for i,row in enumerate(d['weights']):
            if not left[i]:continue
            for b,w in row:
                if b==bone:ids.append(i);weights.append(w)
        if ids:
            ids=np.array(ids);groups.append((bone,ids,np.c_[v[ids],np.ones(len(ids))]*np.array(weights)[:,None]))
    # Include small influences from a non-dominant helper as well.
    included={g[0] for g in groups}
    for bone in sorted({b for i,row in enumerate(d['weights']) if left[i] for b,w in row}-included):
        pairs=[(i,w) for i,row in enumerate(d['weights']) if left[i] for b,w in row if b==bone]
        ids=np.array([i for i,w in pairs]);weights=np.array([w for i,w in pairs]);groups.append((bone,ids,np.c_[v[ids],np.ones(len(ids))]*weights[:,None]))
    report={};cover=names.index('PKM_Cover')
    for role in ('reload','reload_empty'):
        src=pickle.load(open(r/(role+'_local.pkl'),'rb'));world=matrix(src['frames'])
        for i,p in enumerate(parents):
            if p>=0:world[:,i]=world[:,p]@world[:,i]
        np.savez_compressed(r/(role+'_world.npz'),world=world)
        contacts=[]
        for frame,pose in enumerate(world):
            xf=pose@invbind;points=np.zeros_like(v)
            for b,ids,p in groups:points[ids]+=p@xf[b,:3,:].T
            # The optic is rigid on the cover; query its fixed bind-space BVH.
            inv=np.linalg.inv(xf[cover]);points=points@inv[:3,:3].T+inv[:3,3]
            hand=points[lf];mins=hand.min(1);maxs=hand.max(1)
            near=np.nonzero(((maxs>=lo)&(mins<=hi)).all(1))[0];hits=[];bones=set()
            for j in near:
                for k in tree.intersection(np.r_[mins[j],maxs[j]]):
                    if intersect(hand[j],tri[k]):
                        hits.append(j);bones.update(names[i] for i in dominant[lf[j]]);break
            if hits:contacts.append({'frame':frame,'seconds':frame/src['fps'],'triangles':len(hits),'bones':sorted(bones)})
        report[role]={'keys':len(world),'fps':src['fps'],'contact_frames':contacts}
        print(role,'contact frames',len(contacts),'worst',sorted(contacts,key=lambda a:-a['triangles'])[:5],flush=True)
    (r/'contact_sweep.json').write_text(json.dumps(report,indent=2),encoding='utf8')
if __name__=='__main__':run()
