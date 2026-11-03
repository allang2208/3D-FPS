"""Diagnose the reported protruding cutter shell, without rendering or gameplay."""
from pathlib import Path
import bpy,bmesh,json,numpy as np
P=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
rows=[]
for folder,blend,name in [
 ('SeatInlaidC6','ThorSeats_InlaidC6.blend','SM_ThunderGodHammer_head_mount_ribbed_light'),
 ('CommonSeatsStructuralV7_20261102','ThorSeats_StructuralV7_Editable.blend','SM_ThunderGodHammer_head_mount_ribbed_light_V7')]:
 with bpy.data.libraries.load(str(P.parent/folder/blend),link=False) as(a,b):b.objects=[name]
 ob=b.objects[0];mesh=ob.data;bm=bmesh.new();bm.from_mesh(mesh)
 p=np.array([v.co[:] for v in mesh.vertices])
 outside=np.where((p[:,1]<-.0600)|(p[:,1]>.0590))[0]
 outside_set=set(outside.tolist())
 badfaces=[f for f in mesh.polygons if any(v in outside_set for v in f.vertices)]
 counts={str(i):sum(f.material_index==i for f in badfaces) for i in range(len(mesh.materials))}
 bad=[e for e in bm.edges if not e.is_manifold]
 badverts={v for e in bad for v in e.verts}
 badfaces_bm={f for e in bad for f in e.link_faces}
 before=dict(vertices=len(bm.verts),faces=len(bm.faces),boundary_edges=sum(e.is_boundary for e in bm.edges),nonmanifold_edges=len(bad),volume=bm.calc_volume(signed=True),
  edge_face_counts={str(n):sum(len(e.link_faces)==n for e in bad) for n in range(6)},degenerate_faces=sum(f.calc_area()<1e-14 for f in bm.faces),
  bad_face_areas=sorted(f.calc_area() for f in badfaces_bm)[:12],bad_bounds=[[min(v.co[i] for v in badverts) for i in range(3)],[max(v.co[i] for v in badverts) for i in range(3)]])
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0000001)
 after=dict(vertices=len(bm.verts),faces=len(bm.faces),boundary_edges=sum(e.is_boundary for e in bm.edges),nonmanifold_edges=sum(not e.is_manifold for e in bm.edges),volume=bm.calc_volume(signed=True))
 unseen=set(bm.faces);components=[]
 while unseen:
  seed=unseen.pop();stack=[seed];group=[seed]
  while stack:
   f=stack.pop()
   for e in f.edges:
    for n in e.link_faces:
     if n in unseen:unseen.remove(n);stack.append(n);group.append(n)
  verts={v for f in group for v in f.verts}
  components.append(dict(faces=len(group),vertices=len(verts),bounds=[[min(v.co[i] for v in verts) for i in range(3)],[max(v.co[i] for v in verts) for i in range(3)]]))
 rows.append(dict(source=folder,before=before,after_welding=after,outside_vertices=len(outside),outside_material_faces=counts,components=sorted(components,key=lambda r:-r['faces'])[:8]))
 bm.free()
(P/'reported_geometry.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print(json.dumps(rows,indent=2),flush=True)
