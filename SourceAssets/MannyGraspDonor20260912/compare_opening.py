"""Compare contact on three static poses without altering authored joint axes."""
import bpy,json,itertools
from pathlib import Path
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
report={}
for label,d in [('1.0',O),('0.9',O/'Opening/0.9'),('0.8',O/'Opening/0.8')]:
 bpy.ops.wm.open_mainfile(filepath=str(d/'M4_Donor_Aligned.blend'))
 ob=bpy.data.objects['SK_Manny_Arms_Export'];groups={g.index:g.name for g in ob.vertex_groups};ob.data.calc_loop_triangles()
 ids={v.index for v in ob.data.vertices if sum(g.weight for g in v.groups if groups[g.group].endswith('_l') and groups[g.group].startswith(('thumb_','index_','middle_','ring_','pinky_')))>.85}
 fs=[tuple(t.vertices) for t in ob.data.loop_triangles if all(i in ids for i in t.vertices)]
 dg=bpy.context.evaluated_depsgraph_get();e=ob.evaluated_get(dg);m=e.to_mesh();vs=[e.matrix_world@v.co for v in m.vertices];ht=BVHTree.FromPolygons(vs,fs,all_triangles=True);row={}
 for p in bpy.context.scene.objects:
  if p.type!='MESH' or not p.name.startswith('VG_'):continue
  pe=p.evaluated_get(dg);pm=pe.to_mesh();pm.calc_loop_triangles();pt=BVHTree.FromPolygons([pe.matrix_world@v.co for v in pm.vertices],[tuple(t.vertices) for t in pm.loop_triangles],all_triangles=True)
  hits=ht.overlap(pt);depths=[]
  for i in ids:
   co,no,idx,dist=pt.find_nearest(vs[i])
   if co is not None and (vs[i]-co).dot(no)<0:depths.append(dist*1000)
  depths.sort();row[p.name]={'crossing_triangles':len(set(i for i,j in hits)),'inside_vertices_nearest_normal':len(depths),'max_depth_mm':max(depths,default=0),'p95_depth_mm':depths[int(.95*(len(depths)-1))] if depths else 0}
  pe.to_mesh_clear()
 e.to_mesh_clear();report[label]=row
(O/'opening_comparison.json').write_text(json.dumps(report,indent=2));print('OPENING_COMPARE',json.dumps(report),flush=True)
