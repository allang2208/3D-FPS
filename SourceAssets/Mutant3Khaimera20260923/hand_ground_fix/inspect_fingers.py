import bpy,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT.parent/'Mutant3_Khaimera_Feral.blend'))
mesh=bpy.data.objects['Mesh0'];points=[mesh.matrix_world@v.co for v in mesh.data.vertices]
neighbors=[set() for _ in points]
for e in mesh.data.edges:
 a,b=e.vertices;neighbors[a].add(b);neighbors[b].add(a)
weld={}
for i,p in enumerate(points):
 key=tuple(round(x,5) for x in p)
 if key in weld:neighbors[i].add(weld[key]);neighbors[weld[key]].add(i)
 else:weld[key]=i
out={}
for side,sign in [('Left',1),('Right',-1)]:
 out[side]={}
 for cut in [.775,.79,.8,.81,.82,.83,.84]:
  remaining={i for i,p in enumerate(points) if p.x*sign>cut};parts=[]
  while remaining:
   seed=remaining.pop();comp={seed};queue=[seed]
   while queue:
    for other in neighbors[queue.pop()]&remaining:remaining.remove(other);comp.add(other);queue.append(other)
   if len(comp)<4:continue
   lo=[min(points[i][k] for i in comp) for k in range(3)];hi=[max(points[i][k] for i in comp) for k in range(3)]
   parts.append({'n':len(comp),'lo':lo,'hi':hi,'ids':list(comp)})
  out[side][str(cut)]=parts
  print(side,cut,[(p['n'],[round(v,3) for v in p['lo']],[round(v,3) for v in p['hi']]) for p in parts])
(ROOT/'finger_components.json').write_text(json.dumps(out),encoding='utf-8')
