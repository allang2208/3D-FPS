from pathlib import Path
import bpy,json
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'Before/Highland_Peakwatch3to6_Production.blend'))
obj=bpy.data.objects['SM_Highland_Peakwatch3to6'];me=obj.data
adj=[[] for _ in me.vertices]
for e in me.edges:
    a,b=e.vertices;adj[a].append(b);adj[b].append(a)
unseen=set(range(len(me.vertices)));rows=[]
while unseen:
    first=min(unseen);stack=[first];unseen.remove(first);indices=[]
    while stack:
        i=stack.pop();indices.append(i)
        for j in adj[i]:
            if j in unseen:unseen.remove(j);stack.append(j)
    group=set(indices);polys=[p for p in me.polygons if p.vertices[0] in group]
    coords=[me.vertices[i].co for i in indices]
    lo=[min(v[i] for v in coords) for i in range(3)];hi=[max(v[i] for v in coords) for i in range(3)]
    row=dict(first=first,verts=len(indices),faces=len(polys),lo=lo,hi=hi,
        materials=sorted({me.materials[p.material_index].name for p in polys}))
    rows.append(row)
(P/'source-components.json').write_text(json.dumps(rows,indent=2))
for r in rows:
    if r['hi'][1]-r['lo'][1]>2 and r['lo'][2]<23:
        print(json.dumps(r))
