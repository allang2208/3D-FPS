import bpy,json,itertools
from pathlib import Path
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;result={}
for label,path in [('old',O.parent/'VerticalGripRaised20260911/prism/A_M4_Prism_idle.blend'),('new',O/'prism/A_M4_Prism_idle.blend')]:
 bpy.ops.wm.open_mainfile(filepath=str(path));bpy.context.scene.frame_set(0);dg=bpy.context.evaluated_depsgraph_get();ob=bpy.data.objects['SK_Manny_Arms_Export'];ev=ob.evaluated_get(dg);m=ev.to_mesh();m.calc_loop_triangles();v=[ev.matrix_world@x.co for x in m.vertices];groups={g.index:g.name for g in ob.vertex_groups};trees={}
 for digit in ['index','middle','ring','pinky','thumb']:
  ids={x.index for x in ob.data.vertices if sum(g.weight for g in x.groups if groups[g.group].startswith(digit+'_') and groups[g.group].endswith('_l'))>.85};faces=[tuple(t.vertices) for t in m.loop_triangles if all(i in ids for i in t.vertices)];trees[digit]=BVHTree.FromPolygons(v,faces,all_triangles=True)
 result[label]={a+'-'+b:len(trees[a].overlap(trees[b])) for a,b in itertools.combinations(['index','middle','ring','pinky','thumb'],2)}
print('SELF_CONTACT',result);(O/'self_contact.json').write_text(json.dumps(result,indent=2))
