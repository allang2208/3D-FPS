import json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_ray_tri
O=Path(__file__).parent
author=O.parent/'Super90Speedloader20261007/author_speedloader.py';s={'__file__':str(author)}
exec(compile(author.read_text().split('def local_rows(')[0],str(author),'exec'),s)
D=np.load(O/'Diagnostics/saved_mesh_inputs.npz');names=D['names'].tolist();index={n:i for i,n in enumerate(names)}
vertices=D['vertices'].copy();weights=D['weights'];faces=D['faces'];labels=D['labels'];rest=D['rest'];ri=np.linalg.inv(rest)
guide=np.load(O/'guide_geometry.npz');base=len(vertices);vertices=np.vstack([vertices,guide['vertices']]);nw=np.zeros((len(guide['vertices']),len(names)));nw[:,index['WPN_root']]=1;weights=np.vstack([weights,nw]);faces=np.vstack([faces,guide['faces']+base]);labels=np.r_[labels,np.full(len(guide['faces']),'gun')]
weighted={n:np.flatnonzero(weights[:,j]>1e-6) for j,n in enumerate(names)}
pre={n:vertices[weighted[n]]@ri[j].T for j,n in enumerate(names)}
skin={k:faces[labels==k].tolist() for k in ('left','right')}
solids={k:faces[labels==k].tolist() for k in ('gun','props')}
dominant=np.argmax(np.sum(weights[faces],axis=1),axis=1)
skin_names={k:np.asarray(names)[dominant[labels==k]].tolist() for k in ('left','right')}
def deform(p):
    result=np.zeros((len(vertices),3))
    for j,n in enumerate(names):
        ids=weighted[n]
        if len(ids):result[ids]+=(pre[n]@np.asarray(p[n]).T)[:,:3]*weights[ids,j,None]
    return [Vector(v) for v in result]
def cuts(a,b):
    for tri,other in ((a,b),(b,a)):
        for i in range(3):
            start=tri[i];edge=tri[(i+1)%3]-start;hit=intersect_ray_tri(*other,edge,start,True)
            if hit is not None and edge.length_squared>1e-14:
                t=(hit-start).dot(edge)/edge.length_squared
                if 1e-5<t<1-1e-5:return True
    return False
def collision(p,props=True,sides=('left','right')):
    vs=deform(p);out={}
    trees={k:BVHTree.FromPolygons(vs,f,all_triangles=True) for k,f in solids.items() if props or k!='props'}
    for side in sides:
        sf=skin[side];st=BVHTree.FromPolygons(vs,sf,all_triangles=True);out[side]={}
        for k,tree in trees.items():
            gf=solids[k];hit={a for a,b in st.overlap(tree) if cuts([vs[i] for i in sf[a]],[vs[i] for i in gf[b]])};by={}
            for a in hit:
                n=skin_names[side][a];by[n]=by.get(n,0)+1
            out[side][k]={'count':len(hit),'bones':by}
    return out
def wrist_swing(p,side):
    lo='lowerarm_'+side;hand='hand_'+side;axis=(p[hand].translation-p[lo].translation).normalized()
    neutral=p[lo].to_quaternion()@s['rest'][lo].to_quaternion().inverted()@s['rest'][hand].to_quaternion()
    dq=p[hand].to_quaternion()@neutral.inverted();angle=2*math.atan2(Vector((dq.x,dq.y,dq.z)).dot(axis),dq.w)
    swing=(dq@Quaternion(axis,angle).inverted()).angle
    return math.degrees(min(swing,2*math.pi-swing))
