import bpy,bmesh,json
from pathlib import Path
from collections import Counter
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KClosure20261018'
bpy.ops.wm.open_mainfile(filepath=str(P/'SourceAssets/Saiga12KDetail20261018/Authoring/Saiga12K_SurfaceRebuilt.blend'))
R={}
for ob in [o for o in bpy.data.objects if o.type=='MESH']:
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001);bm.verts.ensure_lookup_table();seen=set();rows=[]
 for v in bm.verts:
  if v.index in seen:continue
  stack=[v];vs=[];seen.add(v.index)
  while stack:
   a=stack.pop();vs.append(a)
   for e in a.link_edges:
    b=e.other_vert(a)
    if b.index not in seen:seen.add(b.index);stack.append(b)
  edges={e for v in vs for e in v.link_edges};faces={f for v in vs for f in v.link_faces};part=Counter(ob.data.materials[f.material_index].name for f in faces);coords=[v.co for v in vs]
  row={'vertices':len(vs),'triangles':len(faces),'parts':dict(part),'boundary_edges':sum(e.is_boundary for e in edges),'nonmanifold_edges':sum(len(e.link_faces)>2 for e in edges),'bounds_root_cm':[[min(p[i] for p in coords) for i in range(3)],[max(p[i] for p in coords) for i in range(3)]]}
  rows.append(row)
 R[ob.name]={'islands':rows,'boundary_edges':sum(r['boundary_edges'] for r in rows),'nonmanifold_edges':sum(r['nonmanifold_edges'] for r in rows)};bm.free()
(O/'Reports/topology-before.json').write_text(json.dumps(R,indent=2));print('TOPOLOGY',[(k,v['boundary_edges'],v['nonmanifold_edges']) for k,v in R.items()])
