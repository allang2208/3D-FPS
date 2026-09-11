import bpy,json,itertools
from pathlib import Path
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;result={}
for label,p in [('before',O.parent/'VerticalGripRaised20260911/prism'),('after',O/'prism')]:
 bpy.ops.wm.open_mainfile(filepath=str(p/'A_M4_Prism_reload.blend'));s=bpy.context.scene;ob=bpy.data.objects['SK_Manny_Arms_Export'];groups={g.index:g.name for g in ob.vertex_groups};ob.data.calc_loop_triangles();faces={}
 for d in ['index','middle','ring','pinky','thumb']:
  ids={v.index for v in ob.data.vertices if sum(g.weight for g in v.groups if groups[g.group].startswith(d+'_') and groups[g.group].endswith('_l'))>.85};faces[d]=[tuple(t.vertices) for t in ob.data.loop_triangles if all(i in ids for i in t.vertices)]
 out={}
 for f in [k/2 for k in range(33)]+[k/2 for k in range(204,253)]:
  s.frame_set(int(f),subframe=f%1);e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();v=[e.matrix_world@x.co for x in m.vertices];trees={d:BVHTree.FromPolygons(v,fs,all_triangles=True) for d,fs in faces.items()};out[str(f)]={a+'-'+b:len(trees[a].overlap(trees[b])) for a,b in itertools.combinations(trees,2)};e.to_mesh_clear()
 result[label]=out
(O/'self_transitions.json').write_text(json.dumps(result,indent=2));print('SELF_TRANSITIONS_DONE')
