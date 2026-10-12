"""Fit only the two visibly intersecting digits, bounded around the accepted pose."""
import bpy,json,sys,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;sys.path.insert(0,str(O));from grip_math import load,matrix,pose
d=load('SK_Super90_V7');C=Matrix.Diagonal((.01,-.01,.01,1));Ci=C.inverted()
rest={n:C@matrix(v)@Ci for n,v in d['rest'].items()};parents=d['parents']
grasp={n:C@matrix(v)@Ci for n,v in json.loads((O/'grasp_unfitted.json').read_text())['angled'].items()}
mount=Matrix(((0,-1,0,0),(1,0,0,.16),(0,0,1,-.8015),(0,0,0,1)));inv=np.array(mount.inverted())
donor=load('SK_M4_FoldingSights_HK416');dw,_=pose(donor,load('M4_donors')['angled'])
dn=matrix(donor['rest']['WPN_root'])@dw['WPN_root'].inverted()
auth=json.loads((O.parent/'ASH12UniversalAttachments20260919/authoring_inputs.json').read_text())
models=json.loads((O.parent/'Super90Foregrips20261007/models.json').read_text())
reg=mount@Matrix.Translation((0,0,models['parts']['angled']['body_lift']))@Matrix(auth['donors']['angled']['mount']).inverted()
desired={n:(reg@C@dn@m@Ci).translation for n,m in dw.items() if n.startswith('pinky') and n.endswith('_l')}
bpy.ops.wm.open_mainfile(filepath=str(O/'Exports/SM_Super90_angled_Editable.blend'));ob=next(o for o in bpy.context.scene.objects if o.type=='MESH')
tree=BVHTree.FromPolygons([p.co for p in ob.data.vertices],[list(f.vertices) for f in ob.data.polygons])
points=np.array(d['vertices'])*np.array([.01,-.01,.01]);result={}
for digit in ('pinky',):
    chain=[n for n in grasp if n.startswith(digit)];joints=chain
    ids=[i for i,w in enumerate(d['weights']) if sum(a for n,a in w.items() if n in chain)>.8]
    ids=ids[::2];p=points[ids];weights={n:np.array([d['weights'][i].get(n,0) for i in ids]) for n in grasp}
    local={n:grasp[parents[n]].inverted()@grasp[n] for n in chain}
    def evaluate(parameters,details=False):
        world=dict(grasp)
        for n in chain:
            m=local[n].copy()
            if n in joints:
                a=parameters[joints.index(n)*3:joints.index(n)*3+3]
                q=Quaternion(Vector(a).normalized(),Vector(a).length) if any(a) else Quaternion()
                m=Matrix.LocRotScale(m.translation,q@m.to_quaternion(),m.to_scale())
            world[n]=world[parents[n]]@m
        out=np.zeros_like(p)
        for n in weights:
            m=np.array(world[n]@rest[n].inverted());out+=(p@m[:3,:3].T+m[:3,3])*weights[n][:,None]
        out=out@inv[:3,:3].T+inv[:3,3];signed=[]
        for v in out:
            h,normal,_,distance=tree.find_nearest(Vector(v));signed.append(distance if (Vector(v)-h).dot(normal)>=0 else -distance)
        a=np.array(signed)
        # Deep intersection dominates; a bounded angular cost retains the grasp.
        landmarks=sum((world[n].translation-desired[n]).length_squared * weight for n,weight in ((digit+'_01_l',.4),(digit+'_02_l',1.0),(digit+'_03_l',2.0)))
        cost=12*np.mean(np.maximum(0,-a-.0007)**2)+np.sum(np.array(parameters)**2)*.000004+landmarks
        if details:return {'depth_mm':max(0,-a.min())*1000,'deep_samples':int(sum(a<-.001)),'parameters_degrees':[math.degrees(x) for x in parameters]},world
        return cost
    params=[0.]*(3*len(joints));before,_=evaluate(params,True)
    for step_deg in (6,3,1.5):
        step=math.radians(step_deg)
        for repeat in range(16):
            candidates=[params]
            for i in range(len(params)):
                for sign in (-1,1):
                    q=params.copy();q[i]+=step*sign
                    if all(Vector(q[j:j+3]).length<=math.radians(35) for j in range(0,len(q),3)):candidates.append(q)
            best=min(candidates,key=evaluate)
            if best==params:break
            params=best
    after,world=evaluate(params,True)
    result[digit]={'before':before,'after':after,'joint_rotation_vectors':{n:params[i*3:i*3+3] for i,n in enumerate(joints)}}
    print('DIGIT_CONTACT_FIT '+digit+' '+json.dumps(result[digit]),flush=True)
(O/'angled_digit_fit.json').write_text(json.dumps(result,indent=2))
