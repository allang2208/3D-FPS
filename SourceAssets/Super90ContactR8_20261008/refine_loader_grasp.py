"""Bounded left-hand refinement against saved prop triangles, preserving bones."""
import json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_ray_tri
O=Path(__file__).parent;render=O/'render_saved.py';ns={'__file__':str(render)}
exec(compile(render.read_text().split('items=[]')[0],str(render),'exec'),ns)
s=ns['s'];rest=s['rest'];names=s['names'];idx={n:i for i,n in enumerate(names)}
verts=[];weights=[];skin=[];solid=[]
for key in ('weapon','props'):
 for ob in ns['groups'][key]:
    offset=len(verts);ob.data.calc_loop_triangles()
    for v in ob.data.vertices:
        verts.append([*(ob.matrix_world@v.co),1]);w=[0.]*len(names)
        for g in v.groups:w[idx[ob.vertex_groups[g.group].name]]=g.weight
        weights.append(w)
    for t in ob.data.loop_triangles:
        ids=tuple(offset+i for i in t.vertices);mat=ob.data.materials[t.material_index]
        if key=='props':solid.append(ids)
        elif 'Bare' in mat.name and all(sum(weights[i][idx[n]] for n in ['hand_l']+s['finger_names']['l'])>.98 for i in ids):skin.append(ids)
verts=np.asarray(verts);weights=np.asarray(weights);ri={n:np.asarray(rest[n].inverted()) for n in names}
weighted={n:np.flatnonzero(weights[:,j]>.00001) for j,n in enumerate(names)}
def deform(p):
    result=np.zeros((len(verts),3))
    for j,n in enumerate(names):
        ids=weighted[n]
        if len(ids):result[ids]+=(verts[ids]@(np.asarray(p[n])@ri[n]).T)[:,:3]*weights[ids,j,None]
    return [Vector(v) for v in result]
def cuts(a,b):
    for tri,other in ((a,b),(b,a)):
        for i in range(3):
            start=tri[i];edge=tri[(i+1)%3]-start;hit=intersect_ray_tri(*other,edge,start,True)
            if hit is not None and edge.length_squared>1e-14:
                t=(hit-start).dot(edge)/edge.length_squared
                if 1e-5<t<1-1e-5:return True
    return False
p,handle,_=s['pose'](87,7,False);base=s['hand_in_handle'].copy()
local={n:m.copy() for n,m in s['handle_fingers'].items()}
original_local={n:m.copy() for n,m in local.items()}
vs0=deform(p);gb=BVHTree.FromPolygons(vs0,solid,all_triangles=True)
sample_ids=sorted(set(i for t in skin for i in t))[::12]
def evaluate(x):
    hand=base.copy();hand.translation+=Vector(x)
    target=handle@hand;pose={n:m.copy() for n,m in p.items()};pose['hand_l']=target
    for n in s['finger_names']['l']:pose[n]=pose[s['parents'][n]]@local[n]
    vs=deform(pose);tree=BVHTree.FromPolygons(vs,skin,all_triangles=True)
    crossings={a for a,b in tree.overlap(gb) if cuts([vs[i] for i in skin[a]],[vs0[i] for i in solid[b]])}
    nearest=[gb.find_nearest(vs[i])[3] for i in sample_ids]
    # Keep the original enclosed grasp; only a small placement correction is allowed.
    gap=min(nearest)
    return len(crossings)+np.linalg.norm(x)*3000+max(0,gap-.002)*100000,len(crossings),hand
x=np.zeros(3);best,count,_=evaluate(x);before=count
for step in (.003,.0015,.00075):
 for _ in range(6):
    changed=False
    for j in range(3):
     for sign in (-1,1):
        trial=x.copy();trial[j]=np.clip(trial[j]+sign*step,-.009,.009)
        cost,num,_=evaluate(trial)
        if cost<best:x,best,count=trial,cost,num;changed=True
    if not changed:break
 print('LOADER_PLACEMENT',step,x.tolist(),count,flush=True)
report=[]
for n in s['finger_names']['l']:
    original=local[n].copy();pos,q0,scale=original.decompose();angles=[0.,0.]
    def rotated(v):return Matrix.LocRotScale(pos,q0@Quaternion((1,0,0),math.radians(v[0]))@Quaternion((0,0,1),math.radians(v[1])),scale)
    for step in (4.,2.):
     for _ in range(2):
        changed=False
        for j in range(2):
         for sign in (-1,1):
            trial=angles.copy();trial[j]=max(-8.,min(8.,trial[j]+step*sign));local[n]=rotated(trial)
            cost,num,_=evaluate(x)
            if cost<best:angles,best,count=trial,cost,num;changed=True
        local[n]=rotated(angles)
        if not changed:break
    report.append({'bone':n,'local_xz_degrees':angles,'remaining_triangles':count})
    print('LOADER_DIGIT',report[-1],flush=True)
_,count,hand=evaluate(x)
out=json.loads((O/'hand_fit.json').read_text())
out['loader_hand_in_handle']=[list(r) for r in hand]
out['loader_finger_local']={n:[list(r) for r in m] for n,m in local.items()}
out['loader_refinement']={'offset_handle_m':x.tolist(),'before_hand_triangles':before,'after_hand_triangles':count,'joints':report}
(O/'loader_fit_candidate.json').write_text(json.dumps(out,indent=2))
print('LOADER_CANDIDATE',before,count,flush=True)
