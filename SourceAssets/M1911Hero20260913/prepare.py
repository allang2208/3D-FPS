"""Read the accepted M1911 author model for local surface reconstruction."""
import bpy, bmesh, json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M1911P9Retarget20260913/M1911_P9_Manny_Editable.blend'))
rig=bpy.data.objects['SK_M1911_Manny']; gun=bpy.data.objects['M1911_Export']
root=rig.data.bones['WPN_root'].matrix_local
coords=[root.inverted()@v.co for v in gun.data.vertices]
adj=[set() for v in coords]
for e in gun.data.edges:
    a,b=e.vertices;adj[a].add(b);adj[b].add(a)
remaining=set(range(len(coords)));parts=[]
while remaining:
    todo=[remaining.pop()];ids=set(todo)
    while todo:
        for j in adj[todo.pop()]:
            if j in remaining:remaining.remove(j);ids.add(j);todo.append(j)
    parts.append(sorted(ids))
parts.sort(key=lambda v:(-len(v),v[0]))
groups={g.index:g.name for g in gun.vertex_groups}
rows=[]
for i,ids in enumerate(parts):
    ps=[p for p in gun.data.polygons if p.vertices[0] in set(ids)]
    rows.append({'id':i,'vertices':len(ids),'faces':len(ps),'ids':ids,
                 'min':[min(coords[j][k] for j in ids) for k in range(3)],
                 'max':[max(coords[j][k] for j in ids) for k in range(3)],
                 'materials':sorted({gun.data.materials[p.material_index].name for p in ps}),
                 'bones':sorted({groups[g.group] for j in ids for g in gun.data.vertices[j].groups if g.weight>.001})})
report={'parts':rows,'rig_world':[list(r) for r in rig.matrix_world],
        'root_rest':[list(r) for r in root],
        'bones':{b.name:[list(r) for r in root.inverted()@b.matrix_local] for b in rig.data.bones if b.name.startswith('WPN_')},
        'material_slots':[m.name for m in gun.data.materials],
        'original_triangles':sum(len(p.vertices)-2 for p in gun.data.polygons)}
(O/'author_inputs.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
for row in rows:
    print({k:v for k,v in row.items() if k!='ids'},flush=True)
print('M1911_AUTHOR_INPUTS_SAVED',flush=True)
