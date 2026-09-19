import bpy,json
from pathlib import Path
from mathutils import Vector
out=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath='E:/3d/3-dfps/tools/chest-sapphire-20260908/warehouse_chest_v6.blend')
o=bpy.data.objects['BodyAssembly'];m=o.data
adj=[[] for v in m.vertices]
for e in m.edges:
 a,b=e.vertices;adj[a].append(b);adj[b].append(a)
seen=set();rows=[]
for start in range(len(adj)):
 if start in seen:continue
 q=[start];seen.add(start);ids=[]
 while q:
  v=q.pop();ids.append(v)
  for n in adj[v]:
   if n not in seen:seen.add(n);q.append(n)
 ss=set(ids);polys=[p for p in m.polygons if p.vertices[0] in ss]
 lo=[min(m.vertices[i].co[k] for i in ids) for k in range(3)];hi=[max(m.vertices[i].co[k] for i in ids) for k in range(3)]
 rows.append({'id':len(rows),'verts':len(ids),'faces':len(polys),'lo':lo,'hi':hi,'center':[(a+b)/2 for a,b in zip(lo,hi)],'materials':list({m.materials[p.material_index].name for p in polys})})
(out/'components.json').write_text(json.dumps(rows,indent=2))
for r in rows:
 if 'Gold_PBR' in r['materials']:print(r)
print('OBJECTS',[(o.name,o.type) for o in bpy.data.objects])
