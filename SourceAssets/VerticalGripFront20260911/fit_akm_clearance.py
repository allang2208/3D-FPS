import bpy,json,sys,math,itertools
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;sys.path.insert(0,str(O));from front_pose import apply
D=O/'akm/vertical';bpy.ops.wm.open_mainfile(filepath=str(D/'A_AKM_vertical_idle.blend'));r=bpy.data.objects['SK_M4_Infima'];bpy.context.scene.frame_set(0);r.animation_data.action=None;old={b.name:b.matrix.copy() for b in r.pose.bones};rest={b.name:b.matrix_local.copy() for b in r.data.bones};basis={b.name:b.matrix_basis.copy() for b in r.pose.bones};fits=json.loads((O/'akm/fits.json').read_text());G=old['WPN_root']@Matrix(fits['vertical']['grip_in_root']);ob=bpy.data.objects['SK_Manny_Arms_Export'];ob.data.calc_loop_triangles();groups={g.index:g.name for g in ob.vertex_groups};faces={};ids={}
for digit in ['index','middle','ring','pinky','thumb']:
 ids[digit]={v.index for v in ob.data.vertices if sum(g.weight for g in v.groups if groups[g.group].startswith(digit+'_') and groups[g.group].endswith('_l'))>.85};faces[digit]=[tuple(t.vertices) for t in ob.data.loop_triangles if all(i in ids[digit] for i in t.vertices)]
part=bpy.data.objects['SM_AKM_vertical'];e=part.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();m.calc_loop_triangles();gt=BVHTree.FromPolygons([e.matrix_world@v.co for v in m.vertices],[tuple(t.vertices) for t in m.loop_triangles],all_triangles=True);e.to_mesh_clear();results=[]
for angle in [0,1,2,3,4,5,6,8,10,-1,-2,-3,-4,-6]:
 p={n:m.copy() for n,m in old.items()};parent=old['hand_l']@rest['hand_l'].inverted()@rest['thumb_01_l'];delta=parent.to_quaternion().inverted()@Quaternion((G.to_3x3()@Vector((0,0,1))).normalized(),math.radians(angle))@parent.to_quaternion()
 for b in r.pose.bones:
  n=b.name
  if not n.startswith('thumb_') or not n.endswith('_l'):continue
  q=basis[n].to_quaternion();q=delta@q if n=='thumb_01_l' else q;p[n]=p[b.parent.name]@rest[b.parent.name].inverted()@rest[n]@q.to_matrix().to_4x4()
 apply(r,p,rest);e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();v=[e.matrix_world@z.co for z in m.vertices];trees={d:BVHTree.FromPolygons(v,f,all_triangles=True) for d,f in faces.items()};hit=len(trees['thumb'].overlap(gt))+sum(len(trees['thumb'].overlap(trees[d])) for d in ['index','middle','ring','pinky']);gap=sum(sorted(trees['index'].find_nearest(v[i])[3] for i in ids['thumb'])[:8])/8;e.to_mesh_clear();results.append({'angle_deg':angle,'hits':hit,'index_gap_m':gap,'delta':list(delta)})
 print('AKM_THUMB_CLEARANCE',results[-1],flush=True)
valid=[x for x in results if x['hits']==0];assert valid;best=min(valid,key=lambda x:abs(x['angle_deg']));fits['vertical']['thumb_root_delta']=best['delta'];fits['vertical']['thumb_root_clearance_deg']=best['angle_deg'];(O/'akm/fits.json').write_text(json.dumps(fits,indent=2));(D/'thumb_clearance.json').write_text(json.dumps({'chosen':best,'samples':results},indent=2));print('AKM_CLEARANCE_PASS',best,flush=True)
