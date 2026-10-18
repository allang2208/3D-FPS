"""Fit native thumb joint flexion against full mixed V8 skin, no production writes."""
import sys,json,copy,math
from pathlib import Path
import numpy as np,bpy
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;sys.path.insert(0,str(O));import pose_model as P
m=copy.deepcopy(P.data['roasted_large_lamb']);food=BVHTree.FromPolygons(P.geometry['vertices'],P.geometry['faces'])
_,object_world,base,_=P.solve(m,2.75,False);base={n:object_world.inverted()@v for n,v in base.items()}
def inside(p):
    votes=0
    for direction in [(1,.371,.619),(-.417,1,.293),(.269,-.529,1)]:
        dr=Vector(direction).normalized();origin=Vector(p);hits=0
        for _ in range(24):
            hit,_,_,_=food.ray_cast(origin,dr,100)
            if hit is None:break
            hits+=1;origin=hit+dr*.0001
        votes+=hits%2
    return votes>=2
def quats(params):
    # Native bone X follows each thumb segment; MCP/IP bend around native Y.
    y,z,mcp,ip=params
    return [(Matrix.Rotation(math.radians(z),3,'Z')@Matrix.Rotation(math.radians(y),3,'Y')).to_quaternion(),Matrix.Rotation(math.radians(mcp),3,'Y').to_quaternion(),Matrix.Rotation(math.radians(ip),3,'Y').to_quaternion()]
def packed(q):return [float(q.x),float(q.y),float(q.z),float(q.w)]
report={};original=np.array(P.skin['positions']);tris=np.array(P.skin['triangles'])
edges=np.unique(np.sort(np.concatenate([tris[:,[0,1]],tris[:,[1,2]],tris[:,[2,0]]]),axis=1),axis=0)
for side in ['l','r']:
    names=[f'thumb_{j:02}_{side}' for j in range(1,4)]
    ids=np.where(sum(P.weights[n] for n in names)>.025)[0];positions=P.pos[ids]
    ws={n:w[ids] for n,w in P.weights.items() if np.any(w[ids])}
    ps={n:base[n] for n in P.order}
    fixed=np.zeros((len(ids),3))
    for n,w in ws.items():
        if n not in names:fixed+=(positions@np.array(base[n]@P.inv[n]).T)[:,:3]*w[:,None]
    relevant=edges[np.isin(edges,ids).any(axis=1)];lens=np.linalg.norm(original[relevant[:,0]]-original[relevant[:,1]],axis=1)
    # Final metrics use all skin vertices; fit contact uses every affected vertex.
    def points(params=None):
        out=fixed.copy();pose=base.copy()
        if params is not None:
            for n,q in zip(names,quats(params)):
                inherited=pose[P.parent[n]]@P.local[n];pose[n]=P.mat(inherited.to_3x3()@q.to_matrix(),inherited.translation)
        for n in names:out+=(positions@np.array(pose[n]@P.inv[n]).T)[:,:3]*ws[n][:,None]
        return out,pose
    def evaluate(params=None,details=False):
        pts,pose=points(params);ds=[]
        for p in pts:
            _,_,_,distance=food.find_nearest(Vector(p))
            ds.append(-distance if distance<1.2 and inside(p) else distance)
        ds=np.array(ds);penetration=np.minimum(ds-.015,0)
        score=2200*np.mean(penetration**2)+4500*max(0,-float(ds.min())-.015)**2
        # Contact on a patch of the distal phalanx, not a single bone point.
        distal=np.where(ws[names[-1]]>.65)[0];nearest=np.sort(np.abs(ds[distal]))[:max(12,len(distal)//8)]
        gap=float(nearest.mean());score+=85*max(0,gap-.07)**2
        if params is not None:
            # Prefer broad opposition and gentle IP flexion over a hooked tip.
            score+=.002*(params[2]-24)**2+.004*(params[3]-18)**2
            score+=.001*((params[0]-anchor[0])**2+(params[1]-anchor[1])**2)
        if details:return dict(cost=score,thumb_vertices=len(ids),max_depth_cm=max(0,-float(ds.min())),vertices_inside_0_5mm=int(np.sum(ds<-.05)),distal_patch_gap_cm=gap,joint_degrees=params)
        return score
    anchor=[0,12,24,18] if side=='l' else [-17,5,24,18]
    params=anchor.copy();before=evaluate(None,True);best=evaluate(params)
    limits=[(-32,30),(-10,36),(0,45),(0,35)]
    best_start=params.copy();best_score=best
    for start in [anchor,[-5,15,24,18],[-22,20,15,18],[8,12,30,15],[-5,-5,30,30]]:
        params=start.copy();best=evaluate(params)
        for step in [8,4,2,1,.5]:
            for iteration in range(3):
                changed=False
                for j in range(4):
                    chosen=params;value=best
                    for delta in [-step,step]:
                        attempt=params.copy();attempt[j]+=delta
                        if not limits[j][0]<=attempt[j]<=limits[j][1]:continue
                        cost=evaluate(attempt)
                        if cost<value:value=cost;chosen=attempt
                    if chosen!=params:changed=True;params=chosen;best=value
                if not changed:break
        print('THUMB_FIT',side,start,params,best,flush=True)
        if best<best_score:best_start=params.copy();best_score=best
    params=best_start
    dp=(m['digits'] if side=='l' else m['right_digits'])['thumb'];dp['local_rotations']=[packed(q) for q in quats(params)]
    dp.pop('preserve_native_roll',None)
    report[side]={'before':before,'after':evaluate(params,True),'native_axes':'thumb_01 native Y/Z opposition; thumb_02/03 native Y flexion; no axial roll or IP side-bend'}
    (O/'candidate_motion.json').write_text(json.dumps(m,indent=2))
(O/'thumb_fit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
P.render(m,2.75,'candidate_present');P.render(m,4.65,'candidate_bite')
