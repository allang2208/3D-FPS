import bpy,bmesh,json
from pathlib import Path
R=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(R/'BedroomPilot_Source.blend'))
rows=[]
for key in ('WallShelf','DeskRail'):
    ob=bpy.data.objects['SM_BP_'+key];bm=bmesh.new();bm.from_mesh(ob.data)
    edges=[e for e in bm.edges if not e.is_manifold]
    roles=sorted({ob.data.materials[f.material_index].name for e in edges for f in e.link_faces})
    points=[list(v.co) for e in edges for v in e.verts]
    rows.append(dict(mesh=key,roles=roles,points=points));bm.free()
(R/'typography-edge-locations.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
print([(r['mesh'],r['roles']) for r in rows])
