import bpy,json,math,itertools
from pathlib import Path
from mathutils import Matrix,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'A_M4_Foregrip_idle.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;s.frame_set(0);bpy.context.view_layer.update();r.animation_data.action=None
data=json.loads((O/'fit_final.json').read_text());G=r.pose.bones['WPN_root'].matrix@Matrix(data['grip_in_root']);axis=G.to_3x3().col[1].normalized();trees=[];dg=bpy.context.evaluated_depsgraph_get()
for ob in [x for x in s.objects if x.name.startswith('FG_')]:
 e=ob.evaluated_get(dg);m=e.to_mesh();m.calc_loop_triangles();trees.append(BVHTree.FromPolygons([e.matrix_world@v.co for v in m.vertices],[tuple(t.vertices) for t in m.loop_triangles],all_triangles=True));e.to_mesh_clear()
ob=bpy.data.objects['SK_Manny_Arms_Export'];groups={g.index:g.name for g in ob.vertex_groups};ids={v.index for v in ob.data.vertices if sum(g.weight for g in v.groups if groups[g.group].startswith('pinky') and groups[g.group].endswith('_l'))>.5}
original=[r.pose.bones[f'pinky_{j:02}_l'].rotation_quaternion.copy() for j in [1,2,3]];best=None
for angles in itertools.product([-10,-5,0,5,10],[0,10,20,30,40],[0,10,20,30]):
 total=0;worst=0
 for blend in [.5,1]:
  for j,ang in enumerate(angles,1):r.pose.bones[f'pinky_{j:02}_l'].rotation_quaternion=original[j-1].slerp(Quaternion((0,0,1),math.radians(ang)),blend)
  bpy.context.view_layer.update();e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();m.calc_loop_triangles();faces=[tuple(t.vertices) for t in m.loop_triangles if any(i in ids for i in t.vertices)];v=[e.matrix_world@x.co for x in m.vertices];e.to_mesh_clear()
  for shift in ([0] if blend<1 else [0,.02,.04,.06,.08,.11]):
   tree=BVHTree.FromPolygons([p+axis*shift for p in v],faces,all_triangles=True);hits=set()
   for other in trees:
    for i,j in tree.overlap(other):hits.add(i)
   total+=len(hits);worst=max(worst,len(hits))
 score=total*100+abs(angles[0])+abs(angles[1]-20)*.1+abs(angles[2])*.1
 if best is None or score<best[0]:best=(score,angles,total,worst)
data['opening_pinky']=best[1];(O/'fit_final.json').write_text(json.dumps(data,indent=2));(O/'release_fit.json').write_text(json.dumps({'angles':best[1],'sum_crossing_triangles':best[2],'max_crossing_triangles':best[3]},indent=2));print('RELEASE_FIT',best)
