import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'MeleeGuards20260915/OriginalGuardReference.blend'))
obj=bpy.data.objects['FrostCrystalSword_Blade']
bm=bmesh.new();bm.from_mesh(obj.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
outer=[f for f in bm.faces if abs(f.calc_center_median().x)>.060 and -.048<f.calc_center_median().z<.065]
bmesh.ops.delete(bm,geom=outer,context='FACES')
report={}
for sign in [-1,1]:
    edges=[e for e in bm.edges if e.is_boundary and all(sign*v.co.x>.050 for v in e.verts)]
    vertices=set(v for e in edges for v in e.verts)
    groups=[]
    while vertices:
        group={vertices.pop()};todo=list(group)
        while todo:
            v=todo.pop()
            for e in v.link_edges:
                if e not in edges:continue
                w=e.other_vert(v)
                if w in vertices:vertices.remove(w);group.add(w);todo.append(w)
        groups.append(group)
    report[str(sign)]=[{'count':len(g),'min':[min(v.co[a] for v in g) for a in range(3)],'max':[max(v.co[a] for v in g) for a in range(3)],'valences':list(set(sum(e in edges for e in v.link_edges) for v in g))} for g in groups]
print('SEAM_TOPOLOGY',json.dumps(report),flush=True)
(P/'seam_topology.json').write_text(json.dumps(report,indent=2))
