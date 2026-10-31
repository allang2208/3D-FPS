"""Requested mesh investigation: closed lamp walls, UV area and author LOD0 counts."""
import bpy,bmesh,json
from pathlib import Path
R=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(R/'BedroomPilot_Source.blend'))
rows=[]
for ob in bpy.context.scene.objects:
    if ob.type!='MESH' or not ob.name.startswith('SM_BP_'):continue
    me=ob.data;bm=bmesh.new();bm.from_mesh(me)
    row=dict(key=ob.name.removeprefix('SM_BP_'),triangles=len(me.polygons),boundary_edges=sum(e.is_boundary for e in bm.edges),nonmanifold_edges=sum(not e.is_manifold and not e.is_boundary for e in bm.edges),degenerate_faces=sum(f.calc_area()<1e-13 for f in bm.faces))
    bm.free();uv=me.uv_layers.active.data;bad=0
    for p in me.polygons:
        a,b,c=[uv[i].uv for i in p.loop_indices];area=abs((b.x-a.x)*(c.y-a.y)-(c.x-a.x)*(b.y-a.y))*.5
        if p.area>1e-12 and area<1e-13:bad+=1
    row['degenerate_uv_triangles']=bad;rows.append(row)
    print('SOURCE_DETAIL',row)
(R/'source-geometry.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
