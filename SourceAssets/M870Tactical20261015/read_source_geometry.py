"""Read source geometry for mechanical authoring; no rendering or gameplay."""
import bpy, json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(O/'Original/Source/source/M870_Tactical.fbx'))
report=[]
for ob in bpy.context.scene.objects:
    if ob.type!='MESH': continue
    coords=[ob.matrix_world@v.co for v in ob.data.vertices]
    neighbors=[set() for v in coords]
    for e in ob.data.edges:
        a,b=e.vertices;neighbors[a].add(b);neighbors[b].add(a)
    unseen=set(range(len(coords)));islands=[]
    while unseen:
        pending=[unseen.pop()];ids=[]
        while pending:
            i=pending.pop();ids.append(i)
            for n in neighbors[i]&unseen:unseen.remove(n);pending.append(n)
        p=[coords[i] for i in ids]
        islands.append(dict(ids=ids,count=len(ids),lo=[min(v[k] for v in p) for k in range(3)],hi=[max(v[k] for v in p) for k in range(3)]))
    report.append(dict(name=ob.name,matrix=[list(r) for r in ob.matrix_world],vertices=len(coords),faces=len(ob.data.polygons),materials=[m.name for m in ob.data.materials],islands=sorted(islands,key=lambda a:-a['count'])))
(O/'source_geometry.json').write_text(json.dumps(report,indent=2))
for ob in report:
    print(ob['name'],ob['vertices'],ob['faces'],ob['materials'])
    for i,c in enumerate(ob['islands']): print(i,c['count'],[round(x,4) for x in c['lo']],[round(x,4) for x in c['hi']])
