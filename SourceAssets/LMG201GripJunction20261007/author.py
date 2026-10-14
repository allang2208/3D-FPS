"""Local 201 neck fairing following the retained factory F50 construction."""
import json
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix
O=Path(__file__).parent;(O/'Plans').mkdir(exist_ok=True)
C=json.loads((O/'Input/current.json').read_text());report={}
def unit(v):return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-18)
def read(kind):
    with (O/'Input'/(kind+'.bin')).open('rb') as f:
        h=json.loads(f.readline());nv,nt=h['vertices'],h['triangles']
        p=np.fromfile(f,'<f4',nv*3).reshape(-1,3).astype(float)
        t=np.fromfile(f,'<i4',nt*3).reshape(-1,3);m=np.fromfile(f,'<i4',nt)
        n=np.fromfile(f,'<f4',nt*9).reshape(-1,3,3).astype(float)
        uv=np.fromfile(f,'<f4',nt*6).reshape(-1,3,2)
    return h,p,t,m,n,uv

for kind in C:
    h,source,tri,mat,normal,mask=read(kind)
    _,indices,inv=np.unique(np.round(source,5),axis=0,return_index=True,return_inverse=True)
    original=source[indices];T=inv[tri];nv=len(original)
    edges=np.unique(np.sort(np.concatenate((T[:,[0,1]],T[:,[1,2]],T[:,[2,0]])),axis=1),axis=0)
    edges=edges[edges[:,0]!=edges[:,1]];a,b=edges.T
    adj=coo_matrix((np.ones(len(edges)*2),(np.r_[a,b],np.r_[b,a])),shape=(nv,nv)).tocsr()
    counts=np.maximum(np.asarray(adj.sum(1)).ravel(),1)
    z=original[:,2]
    # Same physical zone, fade and 0.55 mm cap as the existing factory F50 grip.
    weight=np.clip((z+2.8)/1.1,0,1)*np.clip((.45-z)/1.2,0,1)
    # Only a real neck and its immediate blend region may be moved. The source
    # UV4 identifies the reconstructed neck even though it shares the body slot.
    neck_vertex=np.zeros(nv,bool);neck_vertex[np.unique(T[np.any(mask[:,:,0]>1e-5,axis=1)])]=True
    band=(z>-.01) | neck_vertex
    for _ in range(3):band|=(adj@band.astype(float))>0
    weight*=band
    pos=original.copy()
    for _ in range(14):
        pos+=(adj@pos/counts[:,None]-pos)*.40*weight[:,None]
        offset=pos-original;length=np.linalg.norm(offset,axis=1)
        pos=original+offset*np.minimum(1,.055/np.maximum(length,1e-18))[:,None]
    p=pos[T];cross=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0])
    signs=np.where(np.einsum('ij,ij->i',cross,normal.mean(1))<0,-1.,1.)
    cross*=signs[:,None]
    summed=np.zeros((nv,3));vr=T.ravel()
    for axis in range(3):summed[:,axis]=np.bincount(vr,np.repeat(cross[:,axis],3),minlength=nv)
    averaged=unit(summed)[T];strength=np.minimum(1,weight[T]*2.5)
    # Keep each source corner's hemisphere; preserve cap and lower custom normals.
    averaged*=np.where(np.einsum('ijk,ijk->ij',averaged,normal)<0,-1.,1.)[:,:,None]
    newnorm=unit(normal*(1-strength[:,:,None])+averaged*strength[:,:,None])
    updated=source+(pos-original)[inv]
    moved=np.flatnonzero(np.linalg.norm(updated-source,axis=1)>1e-7)
    changed=np.flatnonzero(np.max(np.linalg.norm(newnorm-normal,axis=2),axis=1)>1e-6)
    head={'key':kind,'source_sha256':h['sha256'],'vertices':h['vertices'],'triangles':h['triangles'],'moved':len(moved),'normal_triangles':len(changed)}
    with (O/'Plans'/(kind+'.bin')).open('wb') as f:
        f.write((json.dumps(head)+'\n').encode())
        for a in (moved.astype('<i4'),updated[moved].astype('<f4'),changed.astype('<i4'),newnorm[changed].astype('<f4')):a.tofile(f)
    # Scoped geometry diagnosis requested by the user, separate from game testing.
    edgefaces={};crease_before=[];crease_after=[]
    zone=np.flatnonzero(np.mean(weight[T],axis=1)>.1)
    def face_norms(v):
        p=v[tri];return unit(np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]))
    before=face_norms(source);after=face_norms(updated)
    for ti in zone:
        for i,j in ((0,1),(1,2),(2,0)):
            edge=tuple(sorted((int(T[ti,i]),int(T[ti,j]))))
            if edge in edgefaces:
                other=edgefaces[edge]
                crease_before.append(float(np.degrees(np.arccos(np.clip(before[ti]@before[other],-1,1)))))
                crease_after.append(float(np.degrees(np.arccos(np.clip(after[ti]@after[other],-1,1)))))
            else:edgefaces[edge]=ti
    report[kind]={**head,'max_move_mm':float(np.linalg.norm(updated-source,axis=1).max()*10),'position_frozen_above_cm':.45,
        'position_frozen_below_cm':-2.8,'lower_positions_unchanged':bool(np.array_equal(updated[source[:,2]<=-2.8],source[source[:,2]<=-2.8])),
        'top_positions_unchanged':bool(np.array_equal(updated[source[:,2]>=.45],source[source[:,2]>=.45])),
        'neck_edge_angle_p90_before':float(np.percentile(crease_before,90)) if crease_before else None,
        'neck_edge_angle_p90_after':float(np.percentile(crease_after,90)) if crease_after else None,
        'factory_method':'SurfaceFinish50/model.py bounded grip fairing, 14 steps, 0.55 mm maximum',
        'topology_changed':False,'material_changed':False,'uv_changed':False}
    print('JUNCTION_AUTHORED',kind,json.dumps(report[kind]),flush=True)
(O/'production.json').write_text(json.dumps(report,indent=2))
