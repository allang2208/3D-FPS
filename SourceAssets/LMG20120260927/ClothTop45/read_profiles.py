import bpy,bmesh,json
from pathlib import Path
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Install30/LMG201_R30_NativeFit.blend'),use_scripts=False);ob=bpy.data.objects['AmmoBag'];out={}
for z in [-.060,-.055,-.05,-.045,-.04,-.035,-.03,-.025,-.02,-.01]:
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);r=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(0,0,z),plane_no=(0,0,1),clear_outer=True,clear_inner=False)
    edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-z)<1e-6 for v in e.verts)];adj={}
    for e in edges:
        for v in e.verts:adj.setdefault(v,[]).append(e.other_vert(v))
    unseen=set(adj);rows=[]
    while unseen:
        group=[];todo=[next(iter(unseen))]
        while todo:
            v=todo.pop()
            if v not in unseen:continue
            unseen.remove(v);group.append(v);todo.extend(adj[v])
        rows.append({'n':len(group),'bad_degree':sum(len(adj[v])!=2 for v in group),'bounds':[[min(v.co[i] for v in group),max(v.co[i] for v in group)] for i in range(2)]})
    out[str(z)]=rows;bm.free()
(O/'Inspection/profiles.json').write_text(json.dumps(out,indent=2))
belt=bpy.data.objects['AmmoBelt'];rows={}
for z in [-.003,0.,.004,.009]:
    points=[v.co for v in belt.data.vertices if v.co.z<z]
    rows[str(z)]=[[min(p[i] for p in points),max(p[i] for p in points)] for i in range(3)] if points else []
(O/'Inspection/belt_interface.json').write_text(json.dumps(rows,indent=2));print('C45_PROFILES_READ',flush=True)
