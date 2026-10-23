"""Read original canvas components to locate the two pocket mouths."""
import bpy,bmesh,json
from pathlib import Path

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BackpacksReview20261021';R.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P/'SourceAssets/PortableBackpackAlice20261019/AliceBackpack_uv_bevel.blend'))
ob=bpy.data.objects['SM_AliceBackpack'];bm=bmesh.new();bm.from_mesh(ob.data);bm.faces.ensure_lookup_table()
ob.data.calc_loop_triangles()
snapshot=dict(positions=[list(v.co) for v in ob.data.vertices],triangles=[list(f.vertices) for f in ob.data.loop_triangles],
              triangle_materials=[f.material_index for f in ob.data.loop_triangles],
              matrix=[list(row) for row in ob.matrix_world])
(R/'alice_source.json').write_text(json.dumps(snapshot),encoding='utf-8')
remaining={f for f in bm.faces if f.material_index==0};rows=[]
while remaining:
    first=next(iter(remaining));group=set();stack=[first]
    while stack:
        f=stack.pop()
        if f in group:continue
        group.add(f);remaining.discard(f)
        stack.extend(n for e in f.edges for n in e.link_faces if n in remaining)
    verts={v for f in group for v in f.verts};coords=[v.co for v in verts]
    lo=[min(v[i] for v in coords) for i in range(3)];hi=[max(v[i] for v in coords) for i in range(3)]
    rows.append(dict(faces=len(group),ids=sorted(f.index for f in group),lo=lo,hi=hi,
                     boundary_edges=sum(len([f for f in e.link_faces if f in group])==1 for e in {e for f in group for e in f.edges})))
rows.sort(key=lambda r:r['faces'],reverse=True)
(R/'alice_canvas_components.json').write_text(json.dumps(rows),encoding='utf-8')
print('ALICE_CANVAS_PARTS',[{k:v for k,v in r.items() if k!='ids'} for r in rows],flush=True)
bm.free()
