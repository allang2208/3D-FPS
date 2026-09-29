import bpy,json
from pathlib import Path
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath='D:/FPS3D/FPSGAME/SourceAssets/HospitalBed20260929/Exports/SM_HospitalBed.fbx')
for o in bpy.context.scene.objects:
 if o.type!='MESH':continue
 m=o.data; coords=[o.matrix_world@v.co for v in m.vertices]
 print('BED_SOURCE',o.name,len(m.polygons),[min(v[k] for v in coords) for k in range(3)],[max(v[k] for v in coords) for k in range(3)])
 for i,mat in enumerate(m.materials):
  ids={j for p in m.polygons if p.material_index==i for j in p.vertices}
  print('MATERIAL_BOUNDS',mat.name,[min(coords[j][k] for j in ids) for k in range(3)],[max(coords[j][k] for j in ids) for k in range(3)])
 # Components welded by source coordinates, to identify separate metal tubes.
 keys=[tuple(round(float(x),5) for x in v) for v in coords]; graph={k:set() for k in keys}
 for e in m.edges:
  a,b=(keys[i] for i in e.vertices);graph[a].add(b);graph[b].add(a)
 seen=set();parts=[]
 for k in graph:
  if k in seen:continue
  queue=[k];seen.add(k);points=[]
  while queue:
   p=queue.pop();points.append(p)
   for n in graph[p]:
    if n not in seen:seen.add(n);queue.append(n)
  parts.append(dict(n=len(points),min=[min(v[j] for v in points) for j in range(3)],max=[max(v[j] for v in points) for j in range(3)]))
 print('COMPONENTS',json.dumps(sorted(parts,key=lambda x:-x['n'])[:40]))
