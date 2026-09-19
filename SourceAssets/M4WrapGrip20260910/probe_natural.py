import bpy,json
from pathlib import Path
from mathutils.bvhtree import BVHTree
from mathutils import Vector
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'natural_grip.blend'));r=bpy.data.objects['SK_M4_Infima'];h=bpy.data.objects['SK_Manny_Arms_Export'];mag=bpy.data.objects['M4_Magazine Light.003_Export'];body=bpy.data.objects['M4_M4 Body_Export'];bpy.context.scene.frame_set(0);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();inv=r.pose.bones['WPN_SOCKET_Magazine'].matrix.inverted();trees=[]
for o in [mag,body]:
 ev=o.evaluated_get(dg);m=ev.to_mesh();trees.append(BVHTree.FromPolygons([inv@ev.matrix_world@v.co for v in m.vertices],[list(p.vertices) for p in m.polygons]));ev.to_mesh_clear()
ev=h.evaluated_get(dg);m=ev.to_mesh();vs=[inv@ev.matrix_world@v.co for v in m.vertices];report={}
for digit in ['hand','index','middle','ring','pinky','thumb']:
 ids={v.index for v in h.data.vertices if sum(g.weight for g in v.groups if h.vertex_groups[g.group].name.endswith('_l') and h.vertex_groups[g.group].name.startswith(digit))>.7};fs=[list(p.vertices) for p in m.polygons if any(i in ids for i in p.vertices)];tree=BVHTree.FromPolygons(vs,fs);depth=0;inside=0
 for i in ids:
  p=vs[i];a=trees[0].ray_cast(Vector((-.15,p.y,p.z)),Vector((1,0,0)),.3)[0];b=trees[0].ray_cast(Vector((.15,p.y,p.z)),Vector((-1,0,0)),.3)[0]
  if a is not None and b is not None and a.x<p.x<b.x:depth=max(depth,min(p.x-a.x,b.x-p.x)*1000);inside+=1
 counts={}
 for face,_ in tree.overlap(trees[0]):
  for vi in fs[face]:
   g=max(h.data.vertices[vi].groups,key=lambda g:g.weight);bn=h.vertex_groups[g.group].name;counts[bn]=counts.get(bn,0)+1
 print(digit,counts)
 report[digit]={'mag_pairs':len(tree.overlap(trees[0])),'body_pairs':len(tree.overlap(trees[1])),'depth_mm':depth,'inside':inside,'nearest_mag_mm':min(trees[0].find_nearest(vs[i])[3] for i in ids)*1000}
ev.to_mesh_clear();(O/'natural_probe.json').write_text(json.dumps(report,indent=2));print(report)
