"""Transfer existing native V9 right-hand correctives to the SVD blue glove.

Base glove vertices, binding, weights, materials and the V9 hand are unchanged.
The glove currently has no morphs, so it misses the accepted skin's joint
corrections. Mapping is constrained by native finger/side, in native rest space.
"""
from pathlib import Path
import sys,json,numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from check_surfaces import *
from scipy.spatial import cKDTree
import trimesh
from scipy import sparse
O=HERE
T=np.array(arms['triangles']);S=np.array(arms['positions']);G=np.array(glove['positions'])
def group(n):
    side=n[-1] if n.endswith(('_l','_r')) else 'c'
    part=next((v for v in ('thumb','index','middle','ring','pinky') if n.startswith(v)),'palm')
    return side+'_'+part
srcgroups=np.array([group(names[j]) for j in W.argmax(1)])
dstgroups=np.array([group(names[j]) for j in blue.weights.argmax(1)])
facegroups=np.array([max(set(srcgroups[t]),key=list(srcgroups[t]).count) for t in T])
centers=S[T].mean(1);area=np.linalg.norm(np.cross(S[T[:,1]]-S[T[:,0]],S[T[:,2]]-S[T[:,0]]),axis=1)
mapped=np.zeros((len(G),3),int);bary=np.zeros((len(G),3));distances=np.zeros(len(G))
for key in sorted(set(dstgroups)):
    dst=np.flatnonzero(dstgroups==key);pool=np.flatnonzero((facegroups==key)&(area>1e-8))
    if not len(pool):raise RuntimeError('No matching V9 surface group '+key)
    tree=cKDTree(centers[pool]);k=min(32,len(pool))
    for start in range(0,len(dst),256):
        chunk=dst[start:start+256];_,ix=tree.query(G[chunk],k=k);tri=pool[np.asarray(ix).reshape(len(chunk),k)]
        points=np.repeat(G[chunk],k,axis=0);triangles=S[T[tri]].reshape(-1,3,3)
        closest=trimesh.triangles.closest_point(triangles,points)
        d=np.linalg.norm(closest-points,axis=1).reshape(-1,k);winner=d.argmin(1);best=tri[np.arange(len(chunk)),winner]
        cp=closest.reshape(-1,k,3)[np.arange(len(chunk)),winner]
        mapped[chunk]=T[best];bary[chunk]=trimesh.triangles.points_to_barycentric(S[T[best]],cp)
        distances[chunk]=d.min(1)
transfer={}
for name,delta in deltas.items():
    if '_R' not in name:continue
    value=np.einsum('vi,vij->vj',bary,delta[mapped]);value[~np.char.startswith(dstgroups,'r_')]=0
    if np.linalg.norm(value,axis=1).max()>.0001:transfer[name]=value
def posed(p):
    weights=driver.weights(matrix_pose(p));v=G.copy()
    for n,d in transfer.items():v+=d*weights.get(n,0)
    result=np.zeros_like(v);A=np.zeros((len(v),3,3))
    for j in blue.used:
        m=p[j]@blue.inv[j];result+=(v@m[:3,:3].T+m[:3,3])*blue.weights[:,j,None]
        A+=m[:3,:3]*blue.weights[:,j,None,None]
    return result,A
# The glove's old cloth topology also folds in its held grip. Keep that repair
# inside the corresponding V9 grip corrective; the unposed glove stays intact.
TW=blue.T;N=len(blue.first);edges=np.vstack([TW[:,[0,1]],TW[:,[1,2]],TW[:,[2,0]]]);edges=np.unique(np.sort(edges,axis=1),axis=0)
adj=sparse.coo_matrix((np.ones(len(edges)*2),(np.r_[edges[:,0],edges[:,1]],np.r_[edges[:,1],edges[:,0]])),shape=(N,N)).tocsr()
average=sparse.diags(1/np.maximum(np.array(adj.sum(1)).ravel(),1))@adj
def welded(v):
    x=np.zeros((N,3));np.add.at(x,blue.weld,v);return x/blue.counts[:,None]
def bad_faces(x):
    fn=np.cross(x[TW[:,1]]-x[TW[:,0]],x[TW[:,2]]-x[TW[:,0]]);vn=np.zeros_like(x)
    for k in range(3):np.add.at(vn,TW[:,k],fn)
    vn/=np.maximum(np.linalg.norm(vn,axis=1)[:,None],1e-10)
    return np.flatnonzero((np.einsum('ij,ij->i',fn,vn[TW].mean(1))<0)&blue.mask)
grip='JC_Grip_R_0_51_48_48';transfer.setdefault(grip,np.zeros_like(G));starting_grip=transfer[grip].copy()
if '--refine' in sys.argv:
    previous=np.load(O/'glove-correctives.npz')
    transfer={name:previous[name].copy() for name in previous.files}
poses=np.load(O/'poses.npz')['base'];guard=[]
for round_ in range(3):
    for fi in [0,3,20,68,90]:
        p=poses[fi];v,A=posed(p);start=welded(v);x=start.copy();weight=driver.weights(matrix_pose(p)).get(grip,0)
        if weight<.5:raise RuntimeError('Wrong held-grip corrective')
        before=len(bad_faces(x))
        print('GLOVE_GUARD',round_,fi,before,flush=True)
        for iteration in range(80):
            bad=bad_faces(x)
            if not len(bad):break
            vs=np.unique(TW[bad]);vs=np.unique(np.r_[vs,adj[vs].indices])
            d=.35*((average@x)[vs]-x[vs]);x[vs]+=d
        corr=(x-start)[blue.weld];rest=np.linalg.solve(A,corr[...,None])[...,0]/weight
        if np.linalg.norm(rest,axis=1).max()>.35:raise RuntimeError('Glove correction exceeds 3.5 mm')
        transfer[grip]+=rest
        guard.append({'round':round_,'frame':fi,'folds_before':before,'folds_after':len(bad_faces(x)),'maximum_added_rest_cm':float(np.linalg.norm(rest,axis=1).max())})
np.savez_compressed(O/'glove-correctives.npz',**transfer)
report={'path':glove['path'],'input_sha256':glove['sha256'],'mapping':'native side/finger constrained V9 triangle barycentrics',
    'morphs':list(transfer),'maximum_mapping_distance_cm':float(distances.max()),'p95_mapping_distance_cm':float(np.quantile(distances,.95)),
    'base_geometry_changed':False,'V9_changed':False,'frames':[],'cloth_grip_guard':guard,
    'maximum_cloth_grip_guard_cm':float(np.linalg.norm(transfer[grip]-starting_grip,axis=1).max())}
poses=np.load(O/'poses.npz')['base']
for i in [0,3,6,20,40,68,75,90,108]:
    p=poses[i];weights=driver.weights(matrix_pose(p));v=G.copy()
    for n,d in transfer.items():v+=d*weights.get(n,0)
    posed=np.zeros_like(v)
    for j in blue.used:
        m=p[j]@blue.inv[j];posed+=(v@m[:3,:3].T+m[:3,3])*blue.weights[:,j,None]
    report['frames'].append({'frame':i,'folds_before':blue.folds(blue.evaluate(p)),'folds_after':blue.folds(posed)})
(O/'glove-correctives.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
