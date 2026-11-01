from pathlib import Path
exec(compile((Path(__file__).parent/'solve.py').read_text().split("\nif __name__=='__main__':")[0],'setup','exec'))
from mathutils.bvhtree import BVHTree
grip_deltas={}  # Fit from the original held fingers, never a prior fit.
params=json.loads((O/'solve.json').read_text())['parameters'];row=apply(base,params);set_pose(row);deps=bpy.context.evaluated_depsgraph_get();ob=bpy.data.objects['M24_base'].evaluated_get(deps);me=ob.to_mesh();tree=BVHTree.FromPolygons([ob.matrix_world@v.co for v in me.vertices],[tuple(p.vertices) for p in me.polygons]);ob.to_mesh_clear()
P0=np.array([v.co[:] for v in skin.data.shape_keys.key_blocks[0].data]);P=P0.copy()
for key in skin.data.shape_keys.key_blocks[1:]:
    if key.value:P+=(np.array([v.co[:] for v in key.data])-P0)*key.value
groups={g.index:g.name for g in skin.vertex_groups};locals={n:row[parents[n]].inverted()@m if parents[n] else m for n,m in row.items()};rest_inv={n:m.inverted() for n,m in rest.items()};deltas={};report={}
for digit in ('thumb','index','middle','ring','pinky'):
    ids=np.array([v.index for v in skin.data.vertices if sum(g.weight for g in v.groups if groups[g.group].startswith(digit+'_') and groups[g.group].endswith('_l'))>.65][::2]);points=P[ids];weights={}
    for k,i in enumerate(ids):
        for g in skin.data.vertices[int(i)].groups:weights.setdefault(groups[g.group],np.zeros(len(ids)))[k]=g.weight
    joints=[digit+f'_{i:02d}_l' for i in (1,2,3)];orig=[(local_rest[n].inverted()@locals[n]).to_euler() for n in joints];values=[e.copy() for e in orig]
    def posed(vs):
        rr=dict(row)
        for n,e in zip(joints,vs):rr[n]=rr[parents[n]]@Matrix.LocRotScale(locals[n].translation,local_rest[n].to_quaternion()@e.to_quaternion(),Vector((1,1,1)))
        return rr
    def cost(vs):
        rr=posed(vs);X=np.zeros_like(points)
        for n,w in weights.items():
            M=np.array(rr[n]@rest_inv[n]);X+=(points@M[:3,:3].T+M[:3,3])*w[:,None]
        error=0.
        for p in X:
            hit=tree.find_nearest(Vector(p))
            if hit[0] is None or hit[3]>.035:continue
            signed=hit[3] if (Vector(p)-hit[0]).dot(hit[1])>=0 else -hit[3];error+=max(0,.0007-signed)**2
        return error*9e5+sum((Vector(a)-Vector(b)).length_squared for a,b in zip(vs,orig))*.4
    start=cost(values)
    for step in (8,4,2,1,.5):
        for _ in range(8):
            changed=False
            for j in range(3):
                for dim in ((1,2) if j==0 else (2,)):
                    opts=[values]
                    for sign in (-1,1):
                        v=[e.copy() for e in values];lim=math.radians(30 if dim==2 else 15);v[j][dim]=max(orig[j][dim]-lim,min(orig[j][dim]+lim,v[j][dim]+math.radians(step)*sign));opts.append(v)
                    best=min(opts,key=cost)
                    if cost(best)<cost(values)-1e-8:values=best;changed=True
            if not changed:break
    rr=posed(values)
    for n in joints:
        q=(rr[parents[n]].inverted()@rr[n]).to_quaternion()@locals[n].to_quaternion().inverted();deltas[n]=list(q)
    report[digit]={'before':start,'after':cost(values)}
(O/'grip_deltas.json').write_text(json.dumps(deltas));(O/'grip_fit.json').write_text(json.dumps(report,indent=2));print('IDLE_GRIP_FIT',json.dumps(report),flush=True)
