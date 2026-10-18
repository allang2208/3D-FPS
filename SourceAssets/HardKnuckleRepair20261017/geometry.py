"""Offline native-space cuff utilities. UE face winding is opposite RH cross normals."""
import numpy as np
from collections import defaultdict, Counter

def unit(a):
    a=np.asarray(a,dtype=float)
    return a/max(np.linalg.norm(a),1e-12)

def cuff_normals(points,faces,surface_count):
    points=np.asarray(points);faces=np.asarray(faces)
    q=points[faces];fn=-np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]);vn=np.zeros_like(points)
    # The returned rim is a hard normal boundary. Averaging its narrow end cap
    # into the inner/outer wall can reverse the shading normal on warped wrists.
    for k in range(3):np.add.at(vn,faces[:surface_count,k],fn[:surface_count])
    vn/=np.maximum(np.linalg.norm(vn,axis=1,keepdims=True),1e-12)
    out=vn[faces]
    cap=fn[surface_count:];cap/=np.maximum(np.linalg.norm(cap,axis=1,keepdims=True),1e-12)
    out[surface_count:]=np.repeat(cap[:,None,:],3,axis=1)
    return out.tolist()

def ray_hits(points, faces, origins, directions, front_only=False):
    triangles=np.asarray(points)[np.asarray(faces)]
    v0=triangles[:,0]; e1=triangles[:,1]-v0; e2=triangles[:,2]-v0
    result=[]
    for origin,direction in zip(origins,directions):
        h=np.cross(direction,e2); det=np.einsum('ij,ij->i',e1,h)
        good=np.abs(det)>1e-10
        if front_only:good &= (-np.cross(e1,e2)@direction)>0
        inv=np.divide(1,det,out=np.zeros_like(det),where=good)
        s=origin-v0; u=np.einsum('ij,ij->i',s,h)*inv
        q=np.cross(s,e1); v=q@direction*inv; distance=np.einsum('ij,ij->i',e2,q)*inv
        valid=good&(u>=-1e-7)&(v>=-1e-7)&(u+v<=1.0000001)&(distance>0)&(distance<12)
        if not valid.any():result.append(None);continue
        candidates=np.flatnonzero(valid); j=candidates[np.argmax(distance[candidates])]
        result.append((float(distance[j]),int(j),np.array([1-u[j]-v[j],u[j],v[j]])))
    return result

def arm_basis(bones,side):
    wrist=np.array(bones['hand_'+side]['position'])
    axis=unit(np.array(bones['lowerarm_'+side]['position'])-wrist)
    width=np.array(bones['index_01_'+side]['position'])-bones['pinky_01_'+side]['position']
    width=unit(width-axis*np.dot(width,axis))
    return wrist,axis,width,np.cross(axis,width)

def edge_loops(faces):
    edge_count=Counter(tuple(sorted((int(f[i]),int(f[(i+1)%3])))) for f in faces for i in range(3))
    adj=defaultdict(list)
    for (a,b),n in edge_count.items():
        if n==1:adj[a].append(b);adj[b].append(a)
    loops=[]; unseen=set(adj)
    while unseen:
        start=min(unseen);current=start;prev=None;loop=[]
        while current not in loop:
            loop.append(current);unseen.discard(current)
            candidates=[n for n in adj[current] if n!=prev]
            if not candidates:break
            prev,current=current,candidates[0]
        loops.append(loop)
    return loops
