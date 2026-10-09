"""Keep the loaded wrist fixed; clear the tube by rotating the elbow plane."""
import json,math,numpy as np,itertools
from pathlib import Path
from mathutils import Vector,Quaternion,Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_ray_tri
O=Path(__file__).parent;render=O/'render_saved.py';ns={'__file__':str(render)}
exec(compile(render.read_text().split('items=[]')[0],str(render),'exec'),ns)
s=ns['s'];names=s['names'];rest=s['rest'];idx={n:i for i,n in enumerate(names)}
verts=[];weights=[];arm=[];solid=[]
for key in ('weapon','props'):
 for ob in ns['groups'][key]:
    offset=len(verts);ob.data.calc_loop_triangles()
    for v in ob.data.vertices:
        verts.append([*(ob.matrix_world@v.co),1]);w=[0.]*len(names)
        for g in v.groups:w[idx[ob.vertex_groups[g.group].name]]=g.weight
        weights.append(w)
    for t in ob.data.loop_triangles:
        ids=tuple(offset+i for i in t.vertices);mat=ob.data.materials[t.material_index]
        if key=='props' or 'Bare' not in mat.name:solid.append(ids)
        elif any(sum(weights[i][idx[n]] for n in names if 'arm' in n and n.endswith('_l'))>.65 for i in ids):arm.append(ids)
verts=np.asarray(verts);weights=np.asarray(weights);ri={n:np.asarray(rest[n].inverted()) for n in names}
def deform(p):
    vs=np.zeros((len(verts),3))
    for j,n in enumerate(names):
        selected=np.flatnonzero(weights[:,j]>.00001)
        if len(selected):vs[selected]+=(verts[selected]@(np.asarray(p[n])@ri[n]).T)[:,:3]*weights[selected,j,None]
    return [Vector(v) for v in vs]
def cuts(a,b):
    for tri,other in ((a,b),(b,a)):
        for i in range(3):
            start=tri[i];edge=tri[(i+1)%3]-start;hit=intersect_ray_tri(*other,edge,start,True)
            if hit is not None and edge.length_squared>1e-14:
                t=(hit-start).dot(edge)/edge.length_squared
                if 1e-5<t<1-1e-5:return True
    return False
rows=[]
for roll,angle in itertools.product((90,),range(-80,91,10)):
    s['handle_turn']=Matrix.Rotation(math.pi/2,4,'Y')@Matrix.Rotation(math.radians(roll),4,'Z')
    s['support_fit']['left_loader_pole_degrees']=angle;s['pose_cache'].clear();counts=[];swings=[]
    for f in (87,100,114,118,122):
        p=s['pose'](f,7,False)[0];vs=deform(p)
        at=BVHTree.FromPolygons(vs,arm,all_triangles=True);bt=BVHTree.FromPolygons(vs,solid,all_triangles=True)
        counts.append(len({a for a,b in at.overlap(bt) if cuts([vs[i] for i in arm[a]],[vs[i] for i in solid[b]])}))
        ql=p['lowerarm_l'].to_quaternion();qh=p['hand_l'].to_quaternion();axis=(p['hand_l'].translation-p['lowerarm_l'].translation).normalized()
        neutral=ql@rest['lowerarm_l'].to_quaternion().inverted()@rest['hand_l'].to_quaternion();dq=qh@neutral.inverted()
        twist=2*math.atan2(Vector((dq.x,dq.y,dq.z)).dot(axis),dq.w);swing=(dq@Quaternion(axis,twist).inverted()).angle
        swings.append(math.degrees(min(swing,2*math.pi-swing)))
    row={'angle':angle,'handle_roll':roll,'counts':counts,'swing_degrees':swings,'score':sum(counts)*10+1000*max(0,max(swings[:3])-40)**2+angle*angle*.02+(roll-105)**2*.002}
    rows.append(row);print('ELBOW_FIT',row,flush=True)
best=min(rows,key=lambda r:r['score']);result=json.loads((O/'support_fit.json').read_text());result['left_loader_pole_degrees']=best['angle'];result['left_loader_clearance']={'selected':best,'candidates':rows}
result['loader_handle_roll_degrees']=best['handle_roll']
(O/'support_fit_candidate.json').write_text(json.dumps(result,indent=2));print('LEFT_LOADER_ELBOW',best)
