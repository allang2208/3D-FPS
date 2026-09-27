"""Extract cross sections and shell IDs as inputs to body authoring."""
import bpy,json
from pathlib import Path
P=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'BowModular20260926/Bow_ModularParts.blend'))
o=bpy.data.objects['SM_Bow_BodyModular'];v=[p.co.copy() for p in o.data.vertices]
adj=[[] for _ in v]
for e in o.data.edges:
 a,b=e.vertices;adj[a].append(b);adj[b].append(a)
left=set(range(len(v)));groups=[]
while left:
 start=left.pop();stack=[start];g=[start]
 while stack:
  for i in adj[stack.pop()]:
   if i in left:left.remove(i);stack.append(i);g.append(i)
 groups.append(g)
rows=[]
for g in groups:
 rows.append(dict(count=len(g),bounds=[[min(v[i][a] for i in g),max(v[i][a] for i in g)] for a in range(3)]))
wood=max(groups,key=lambda g:max(v[i].z for i in g)-min(v[i].z for i in g))
sections=[]
for z in range(-70,71,5):
 pts=[v[i] for i in wood if abs(v[i].z-z)<1.8]
 if pts:sections.append(dict(z=z,n=len(pts),bounds=[[round(min(p[a] for p in pts),4),round(max(p[a] for p in pts),4)] for a in range(2)]))
r=dict(groups=rows,wood_ids=wood,sections=sections)
(P/'donor-inputs.json').write_text(json.dumps(r,indent=2),encoding='utf8')
print(json.dumps(dict(groups=rows,sections=sections)))
