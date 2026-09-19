import bpy,json,sys,collections
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'akm/canted/A_AKM_canted_reload.blend'));r=bpy.data.objects['SK_M4_Infima'];bpy.context.scene.frame_set(6);ob=bpy.data.objects['SK_Manny_Arms_Export'];groups={g.index:g.name for g in ob.vertex_groups};labels={v.index:max([(g.weight,groups[g.group]) for g in v.groups],default=(0,''))[1] for v in ob.data.vertices};dg=bpy.context.evaluated_depsgraph_get();e=ob.evaluated_get(dg);m=e.to_mesh();m.calc_loop_triangles();v=[e.matrix_world@x.co for x in m.vertices];faces=[tuple(t.vertices) for t in m.loop_triangles if any(labels[i].endswith('_l') and labels[i].startswith(('index','middle','ring','pinky','thumb')) for i in t.vertices)];hand=BVHTree.FromPolygons(v,faces,all_triangles=True)
p=bpy.data.objects['SM_AKM_canted'];e=p.evaluated_get(dg);m=e.to_mesh();m.calc_loop_triangles();pv=[e.matrix_world@x.co for x in m.vertices];tree=BVHTree.FromPolygons(pv,[tuple(t.vertices) for t in m.loop_triangles],all_triangles=True);hits=hand.overlap(tree);report=collections.defaultdict(list);inv=(r.matrix_world@r.pose.bones['WPN_root'].matrix).inverted()
for i,j in hits:report[p.data.materials[m.loop_triangles[j].material_index].name].append(list(inv@(sum((v[k] for k in faces[i]),Vector())/3)))
print({k:{'count':len(v),'bbox':[[min(x[i] for x in v),max(x[i] for x in v)] for i in range(3)]} for k,v in report.items()})
for d in ['index','middle','ring','pinky','thumb']:
 vv=[inv@v[i] for i in labels if labels[i].startswith(d+'_') and labels[i].endswith('_l')]
 print('DIGIT_ROOT_BOUNDS',d,[[min(x[i] for x in vv),max(x[i] for x in vv)] for i in range(3)])
