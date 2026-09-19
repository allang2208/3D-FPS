import bpy,json,numpy as np
from pathlib import Path
from mathutils import Matrix
P=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'ASH12Surface20260919/ASH12_Surface_Editable.blend'))
g=bpy.data.objects['ASH12_Export'];f=Matrix(json.loads((P/'source_measurements.json').read_text())['matrix'])
ps=np.array([tuple(f@v.co) for v in g.data.vertices]);faces=[p for p in g.data.polygons if p.material_index==4];ids=sorted({i for p in faces for i in p.vertices});a=ps[ids]
vectors=[]
for e in g.data.edges:
 i,j=e.vertices
 if i in ids and j in ids:
  d=ps[j]-ps[i];length=np.linalg.norm(d)
  if length>.02:vectors.append([round(length,5),*(d/length).round(4).tolist(),ps[i].round(5).tolist(),ps[j].round(5).tolist()])
print('LONG_EDGES',json.dumps(sorted(vectors,reverse=True)[:30]))
