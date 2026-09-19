import bpy,json,math,itertools
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Foregrip_Fitted.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
data=json.loads((O/'fit_pose.json').read_text());G=Matrix(data['grip_matrix']);H=r.pose.bones['hand_l'].matrix.copy();H.translation+=G.to_3x3()@Vector((-.04,-.1,0));r.pose.bones['hand_l'].matrix=H;bpy.context.view_layer.update()
trees=[];dg=bpy.context.evaluated_depsgraph_get()
for ob in [x for x in s.objects if x.name.startswith('FG_')]:
 e=ob.evaluated_get(dg);m=e.to_mesh();m.calc_loop_triangles();trees.append(BVHTree.FromPolygons([e.matrix_world@v.co for v in m.vertices],[tuple(t.vertices) for t in m.loop_triangles],all_triangles=True));e.to_mesh_clear()
ob=bpy.data.objects['SK_Manny_Arms_Export'];groups={g.index:g.name for g in ob.vertex_groups};results={}
def collisions(digit):
 ids={v.index for v in ob.data.vertices if sum(g.weight for g in v.groups if groups[g.group].startswith(digit) and groups[g.group].endswith('_l'))>.5}
 bpy.context.view_layer.update();e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();m.calc_loop_triangles();faces=[tuple(t.vertices) for t in m.loop_triangles if any(i in ids for i in t.vertices)];tree=BVHTree.FromPolygons([e.matrix_world@v.co for v in m.vertices],faces,all_triangles=True);hits=set()
 for other in trees:
  for i,j in tree.overlap(other):hits.add(i)
 e.to_mesh_clear();return len(hits)
for digit in ['index','middle','ring','pinky']:
 best=None
 for mcp,pip,dip in itertools.product([0,5,10,15,-5,-10] if digit=='pinky' else [0],[35,40,45,50,55,60,65,70],[15,20,25,30,35,40]):
  for j,ang in [(1,mcp),(2,pip),(3,dip)]:r.pose.bones[f'{digit}_{j:02}_l'].rotation_quaternion=Quaternion((0,0,1),math.radians(ang))
  count=collisions(digit);score=count*10+abs(pip-60)*.1+abs(dip-35)*.1+abs(mcp)*.2
  if best is None or score<best[0]:best=(score,pip,dip,count,mcp)
 for j,ang in [(1,best[4]),(2,best[1]),(3,best[2])]:r.pose.bones[f'{digit}_{j:02}_l'].rotation_quaternion=Quaternion((0,0,1),math.radians(ang))
 results[digit]={'mcp':best[4],'pip':best[1],'dip':best[2],'crossing_triangles':best[3]}
# Bounded native thumb abduction, evaluated against the external frame.
b=r.pose.bones['thumb_01_l'];native=b.rotation_quaternion.copy();best=None
for deg in range(-30,31,5):
 b.rotation_quaternion=native@Quaternion((0,1,0),math.radians(deg));count=collisions('thumb');score=count*10+abs(deg)*.1
 if best is None or score<best[0]:best=(score,deg,count,b.rotation_quaternion.copy())
b.rotation_quaternion=best[3];bpy.context.view_layer.update();results['thumb']={'native_local_y_delta':best[1],'crossing_triangles':best[2]}
data['hand_in_root']=[list(row) for row in Matrix(data['old']['WPN_root']).inverted()@H]
for b in r.pose.bones:
 if b.name.startswith(('index','middle','ring','pinky','thumb')):data['basis'][b.name]=[list(row) for row in b.matrix_basis]
data['refinement']=results;(O/'fit_final.json').write_text(json.dumps(data,indent=2));(O/'grasp_refinement.json').write_text(json.dumps(results,indent=2));print('GRASP_REFINED',results)
