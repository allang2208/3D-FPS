import bpy,json,itertools,math
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Foregrip_Pose.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;data=json.loads((O/'fit_pose.json').read_text());G=Matrix(data['grip_matrix']);old={b.name:b.matrix.copy() for b in r.pose.bones};dg=bpy.context.evaluated_depsgraph_get()
trees=[]
for ob in [x for x in s.objects if x.name.startswith('FG_')]:
 e=ob.evaluated_get(dg);m=e.to_mesh();m.calc_loop_triangles();trees.append(BVHTree.FromPolygons([e.matrix_world@v.co for v in m.vertices],[tuple(t.vertices) for t in m.loop_triangles],all_triangles=True));e.to_mesh_clear()
ob=bpy.data.objects['SK_Manny_Arms_Export'];groups={g.index:g.name for g in ob.vertex_groups}
selected={v.index for v in ob.data.vertices if sum(g.weight for g in v.groups if groups[g.group].endswith('_l') and groups[g.group].startswith(('index','middle','ring','pinky','thumb','hand')))>.5}
e=ob.evaluated_get(dg);m=e.to_mesh();m.calc_loop_triangles();vertices=[e.matrix_world@v.co for v in m.vertices];faces=[tuple(t.vertices) for t in m.loop_triangles if all(i in selected for i in t.vertices)];e.to_mesh_clear()
results=[]
for x,y,z,angle in itertools.product([-.08,-.04,0,.04],[-.15,-.10,-.05],[-.04,0,.04],[0,5,10,15,20,-5]):
 offset=G.to_3x3()@Vector((x,y,z));pivot=G@Vector((.16,0,.035));axis=G.to_3x3().col[1].normalized();rot=Matrix.Rotation(math.radians(angle),3,axis);hand=BVHTree.FromPolygons([pivot+rot@(v-pivot)+offset for v in vertices],faces,all_triangles=True);hits=set()
 for tree in trees:
  for i,j in hand.overlap(tree):hits.add(i)
 results.append({'shift_grip':[x,y,z],'shift_m':list(offset),'palm_angle_deg':angle,'triangles':len(hits)})
results.sort(key=lambda x:(x['triangles'],sum(v*v for v in x['shift_m'])))
(O/'clearance_search.json').write_text(json.dumps(results[:30],indent=2));print('BEST',results[:10])
