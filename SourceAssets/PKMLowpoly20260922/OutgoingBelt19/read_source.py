"""Read the existing visual tab and belt attachment geometry for authoring."""
import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;R=O.parent
bpy.ops.wm.open_mainfile(filepath=str(R/'CarryHandle18/PKM_CarryHandle_Editable.blend'),use_scripts=False)
r=bpy.data.objects['PKM_Manny_Rig'];r.data.pose_position='REST'
fit=Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix'])
B=r.data.bones['WPN_root'].matrix_local@fit
ob=bpy.data.objects['PKM_Part_113'];coords=[B.inverted()@ob.matrix_world@v.co for v in ob.data.vertices]
adj={i:set() for i in range(len(coords))}
for e in ob.data.edges:
 a,b=e.vertices;adj[a].add(b);adj[b].add(a)
remaining=set(adj);islands=[]
while remaining:
 todo=[remaining.pop()];ids=[]
 while todo:
  i=todo.pop();ids.append(i)
  for j in adj[i]&remaining:remaining.remove(j);todo.append(j)
 pts=[coords[i] for i in ids]
 islands.append({'vertices':len(ids),'bounds':[[min(v[k] for v in pts) for k in range(3)],[max(v[k] for v in pts) for k in range(3)]]})
out={'islands':islands,'points':[list(v) for v in coords],'materials':[m.name for m in ob.data.materials],
 'root_rest':[list(row) for row in r.data.bones['WPN_root'].matrix_local],
 'empty_rest':[list(row) for row in r.data.bones['PKM_EmptyLink'].matrix_local],
 'belt_centers':json.loads((R/'Belt08/belt_layout.json').read_text())['centers']}
(O/'source_geometry.json').write_text(json.dumps(out,indent=2))
print('TAB_SOURCE',json.dumps({k:v for k,v in out.items() if k not in ['points','belt_centers']}),flush=True)
