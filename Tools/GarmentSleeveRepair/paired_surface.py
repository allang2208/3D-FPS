"""Relax only conflicting native sleeve patches before emitting both layers."""
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

def normals(p,f):
    n=np.zeros_like(p);cross=-np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]])
    for i in range(3):np.add.at(n,f[:,i],cross)
    return n/np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-12)

def relax(p,f,boundary,clearance,shoulder,axis,thickness=.2,directions=None):
    count=len(p);p=p.copy();before=p.copy()
    rim=[]
    for i,j in boundary:rim.extend([[j,i,i+count],[j,i+count,j+count]])
    ff=np.concatenate([f,f[:,::-1]+count,np.asarray(rim)])
    edges=np.unique(np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1),axis=0)
    src=np.concatenate([edges[:,0],edges[:,1]]);dst=np.concatenate([edges[:,1],edges[:,0]])
    degree=np.bincount(src,minlength=count)
    at_shoulder=np.abs((p-shoulder)@axis)<.0002
    mask=np.zeros(count)
    initial=None
    for step in range(81):
        n=normals(p,f) if directions is None else directions.copy()
        # The thickness rim stays in the same shoulder cut plane.
        n[at_shoulder]-=np.outer(n[at_shoulder]@axis,axis)
        n/=np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-12)
        pp=np.concatenate([p+n*clearance[:,None],p+n*(clearance-thickness)[:,None]])
        tree=BVHTree.FromPolygons([Vector(v) for v in pp],ff.tolist(),all_triangles=True,epsilon=0)
        bad=[(a,b) for a,b in tree.overlap(tree) if a<b and not set(ff[a])&set(ff[b])]
        if initial is None:initial=len(bad)
        if not bad:
            return p,n,dict(initial_intersections=initial,final_intersections=0,relaxation_steps=step,max_surface_adjust_cm=float(np.linalg.norm(p-before,axis=1).max()))
        touched=np.unique(ff[np.array(bad).ravel()].ravel()%count)
        active=np.zeros(count);active[touched]=1
        for _ in range(3):
            spread=np.zeros(count);np.maximum.at(spread,src,active[dst]*.7);active=np.maximum(active,spread)
        mask=np.maximum(mask,active)
        average=np.zeros_like(p);np.add.at(average,src,p[dst]);average/=np.maximum(degree[:,None],1)
        delta=(average-p)*mask[:,None]*.45
        delta[at_shoulder]-=np.outer(delta[at_shoulder]@axis,axis)
        p+=delta
    raise RuntimeError('Paired sleeve patch remains intersecting: '+str(len(bad)))
