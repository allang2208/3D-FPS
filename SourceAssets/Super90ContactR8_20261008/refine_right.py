"""Refine only the contact fit against triangles of the actual saved UE mesh."""
import json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_ray_tri
folder=Path(__file__).parent;review=folder.parents[1]/'Saved/Super90R7Review20261008/render_saved.py'
ns={'__file__':str(review)};exec(compile(review.read_text().split('items=[]')[0],str(review),'exec'),ns)
s=ns['s'];rest=s['rest'];names=list(rest);index={n:i for i,n in enumerate(names)}
verts=[];weights=[];triangles=[];gun=[];p=s['pose'](104,7,False)[0]
for ob in ns['groups']['weapon']:
    ob.data.calc_loop_triangles();offset=len(verts)
    for v in ob.data.vertices:
        verts.append([*(ob.matrix_world@v.co),1]);row=[0.]*len(names)
        for g in v.groups:row[index[ob.vertex_groups[g.group].name]]=g.weight
        weights.append(row)
    for t in ob.data.loop_triangles:
        mat=ob.data.materials[t.material_index];ids=tuple(offset+i for i in t.vertices)
        if 'Bare' not in mat.name:gun.append(ids)
        elif sum(sum(weights[i][index[n]] for n in names if n.endswith('_r')) for i in ids)>1.5:triangles.append(ids)
verts=np.asarray(verts);weights=np.asarray(weights);ri={n:np.asarray(rest[n].inverted()) for n in names}
def deform(p):
    result=np.zeros((len(verts),3))
    for j,n in enumerate(names):
        ids=np.flatnonzero(weights[:,j]>.00001)
        if len(ids):result[ids]+=(verts[ids]@(np.asarray(p[n])@ri[n]).T)[:,:3]*weights[ids,j,None]
    return [Vector(v) for v in result]
baseverts=deform(p);gb=BVHTree.FromPolygons(baseverts,gun,all_triangles=True)
def cuts(a,b):
    for tri,other in ((a,b),(b,a)):
        for i in range(3):
            start=tri[i];edge=tri[(i+1)%3]-start;hit=intersect_ray_tri(*other,edge,start,True)
            if hit is not None and edge.length_squared>1e-14:
                t=(hit-start).dot(edge)/edge.length_squared
                if 1e-5<t<1-1e-5:return True
    return False
base=Matrix(s['hand_fit']['right_hand_in_idle']);move=s['G0']@s['R0'].inverted();calls=0
def cost(x):
    global calls
    hand=base.copy();hand.translation+=move.to_3x3()@Vector(x)
    s['hand_fit']['right_hand_in_idle']=[list(r) for r in hand]
    s['pose_cache'].clear()
    vs=deform(s['pose'](104,7,False)[0]);tree=BVHTree.FromPolygons(vs,triangles,all_triangles=True)
    crossing={a for a,b in tree.overlap(gb) if cuts([vs[i] for i in triangles[a]],[baseverts[i] for i in gun[b]])}
    calls+=1
    return len(crossing)+np.linalg.norm(x)*3000,len(crossing)
x=np.zeros(3);best,count=cost(x);before=count
for step in (() if 'right_exact_refinement' in s['hand_fit'] else (.003,.0015,.00075)):
  for _ in range(8):
    changed=False
    for j in range(3):
      for sign in (-1,1):
        trial=x.copy();trial[j]=np.clip(trial[j]+step*sign,-.012,.012);c,n=cost(trial)
        if c<best:x,best,count=trial,c,n;changed=True
    if not changed:break
  print('EXACT_RIGHT_FIT',step,x.tolist(),count,flush=True)
cost(x)
joint_report=[]
def rotate_towards(original,target,t):
    p,q,scale=original.decompose();dq=target.to_quaternion()@q.inverted()
    if dq.w<0:dq.negate()
    return Matrix.LocRotScale(p,Quaternion(dq.axis,dq.angle*t)@q,scale)
for n in s['finger_names']['r']:
    original=Matrix(s['hand_fit']['right_finger_local'][n]);target=s['local_rest'][n]
    angle=original.to_quaternion().rotation_difference(target.to_quaternion()).angle
    angle=min(angle,2*math.pi-angle);limit=min(.4,math.radians(15)/max(angle,.001))
    best_t=0.;best_count=count
    for t in (-limit,-limit*.5,limit*.5,limit):
        local=rotate_towards(original,target,t)
        s['hand_fit']['right_finger_local'][n]=[list(r) for r in local]
        _,num=cost(x)
        if num<best_count:best_count=num;best_t=t
    s['hand_fit']['right_finger_local'][n]=[list(r) for r in rotate_towards(original,target,best_t)]
    count=best_count;joint_report.append({'bone':n,'blend':best_t,'remaining_triangles':count})
out=json.loads((folder/'hand_fit.json').read_text());out['right_hand_in_idle']=s['hand_fit']['right_hand_in_idle']
out['right_finger_local']=s['hand_fit']['right_finger_local'];out['right_joint_refinement']=joint_report
axis_report=[]
for n in s['finger_names']['r']:
    original=Matrix(s['hand_fit']['right_finger_local'][n]);pos,q0,scale=original.decompose();angles=[0.,0.]
    def rotated(values):
        q=q0@Quaternion((1,0,0),math.radians(values[0]))@Quaternion((0,0,1),math.radians(values[1]))
        return Matrix.LocRotScale(pos,q,scale)
    for step in (4.,2.):
      for _ in range(3):
        changed=False
        for j in range(2):
          for sign in (-1,1):
            trial=angles.copy();trial[j]=max(-12.,min(12.,trial[j]+step*sign))
            s['hand_fit']['right_finger_local'][n]=[list(r) for r in rotated(trial)]
            _,num=cost(x)
            if num<count:angles,count=trial,num;changed=True
        s['hand_fit']['right_finger_local'][n]=[list(r) for r in rotated(angles)]
        if not changed:break
    axis_report.append({'bone':n,'local_xz_degrees':angles,'remaining_triangles':count})
out['right_finger_local']=s['hand_fit']['right_finger_local'];out['right_axis_refinement']=axis_report
out['right_exact_refinement']={'offset_native_m':x.tolist(),'before_triangles':before,'after_triangles':count,'evaluations':calls}
(folder/'hand_fit.json').write_text(json.dumps(out,indent=2))
print('RIGHT_JOINTS',before,count,flush=True)
