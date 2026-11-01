from pathlib import Path
exec(compile((Path(__file__).parent/'setup.py').read_text(),'setup','exec'))
from mathutils.bvhtree import BVHTree
base=pose('idle',0)[0];set_pose(base);rt=base['WPN_root']@rest['WPN_root'].inverted()
locals={n:base[parents[n]].inverted()@m if parents[n] else m for n,m in base.items()}
joints=['thumb_01_l','thumb_02_l','thumb_03_l'];orig=[(local_rest[n].inverted()@locals[n]).to_euler() for n in joints]
P0=np.array([v.co[:] for v in skin.data.shape_keys.key_blocks[0].data]);P=P0.copy()
for key in skin.data.shape_keys.key_blocks[1:]:
    if key.value:P+=(np.array([v.co[:] for v in key.data])-P0)*key.value
groups={g.index:g.name for g in skin.vertex_groups}
ids=np.array([v.index for v in skin.data.vertices if sum(g.weight for g in v.groups if groups[g.group] in joints)>.65][::2]);points=P[ids];weights={}
for k,i in enumerate(ids):
    for g in skin.data.vertices[int(i)].groups:weights.setdefault(groups[g.group],np.zeros(len(ids)))[k]=g.weight
rinv={n:m.inverted() for n,m in rest.items()}
# Use the new metal forend at its real attachment transform.
tree=BVHTree.FromPolygons([rt@advanced_rest@v.co for v in advanced.data.vertices],[tuple(p.vertices) for p in advanced.data.polygons])
target_tip=rt@Vector((-.033,.354,.100));target_ip=rt@Vector((-.040,.342,.086))
tip_local=Vector((.020,0,0))
def posed(v):
    rr=dict(base);values=[e.copy() for e in orig]
    values[0].y+=v[0];values[0].z+=v[1];values[1].z+=v[2];values[2].z+=v[3]
    for n,e in zip(joints,values):rr[n]=rr[parents[n]]@Matrix.LocRotScale(locals[n].translation,local_rest[n].to_quaternion()@e.to_quaternion(),Vector((1,1,1)))
    return rr
def cost(v,details=False):
    rr=posed(v);X=np.zeros_like(points)
    for n,w in weights.items():
        M=np.array(rr[n]@rinv[n]);X+=(points@M[:3,:3].T+M[:3,3])*w[:,None]
    depths=[]
    for p in X:
        hit=tree.find_nearest(Vector(p))
        signed=hit[3] if (Vector(p)-hit[0]).dot(hit[1])>=0 else -hit[3]
        depths.append(max(0,.001-signed))
    tip=rr[joints[-1]]@tip_local;ip=rr[joints[-1]].translation
    result=(tip-target_tip).length_squared*18000+(ip-target_ip).length_squared*5000+sum(d*d for d in depths)*3e5+sum(x*x for x in v)*.025
    if details:return {'cost':result,'deltas_deg':[math.degrees(x) for x in v],'tip_source':list(rt.inverted()@tip),'ip_source':list(rt.inverted()@ip),'max_penetration_mm':max(depths)*1000-1,'mcp_bend':angle(rr[joints[1]].translation-rr[joints[0]].translation,ip-rr[joints[1]].translation),'ip_bend':angle(ip-rr[joints[1]].translation,tip-ip)}
    return result
limits=[(-35,35),(-40,40),(-35,65),(-35,55)]
best=None
for initial in ([0,0,0,0],[10,-15,40,25],[-15,20,35,20]):
    values=[math.radians(v) for v in initial]
    for step in (12,6,3,1.5,.5):
        for _ in range(10):
            options=[values]
            for j in range(4):
                for sign in (-1,1):
                    v=list(values);v[j]=max(math.radians(limits[j][0]),min(math.radians(limits[j][1]),v[j]+sign*math.radians(step)));options.append(v)
            chosen=min(options,key=cost)
            if chosen==values:break
            values=chosen
    if best is None or cost(values)<cost(best):best=values
fixed=posed(best);deltas={n:list((fixed[parents[n]].inverted()@fixed[n]).to_quaternion()@locals[n].to_quaternion().inverted()) for n in joints}
(O/'thumb_deltas.json').write_text(json.dumps(deltas));(O/'thumb_fit.json').write_text(json.dumps({'before':cost([0]*4,True),'after':cost(best,True)},indent=2))
folder=O/'Candidate';folder.mkdir(exist_ok=True)
view(fixed,folder/'thumb.png','thumb');view(fixed,folder/'idle.png')
print('THUMB_FIT',json.dumps(cost(best,True)),flush=True)
