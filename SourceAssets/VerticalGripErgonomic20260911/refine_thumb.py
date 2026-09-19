import bpy,json,math,sys,itertools
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;sys.path.insert(0,str(O));from fit_pose import measure
from inspect_reference import setup_render
for variant in sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['vertical','prism']:
 d=O/variant;bpy.ops.wm.open_mainfile(filepath=str(d/'Contact.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;fit=json.loads((d/'fit_final.json').read_text());G=r.pose.bones['WPN_root'].matrix@Matrix(fit['grip_in_root']);ob=bpy.data.objects['SK_Manny_Arms_Export'];groups={g.index:g.name for g in ob.vertex_groups};ob.data.calc_loop_triangles();ids={};faces={};trees={}
 for digit in ['index','middle','ring','pinky','thumb']:
  ids[digit]={v.index for v in ob.data.vertices if sum(g.weight for g in v.groups if groups[g.group].startswith(digit+'_') and groups[g.group].endswith('_l'))>.85};faces[digit]=[tuple(t.vertices) for t in ob.data.loop_triangles if all(i in ids[digit] for i in t.vertices)]
 e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();v=[e.matrix_world@x.co for x in m.vertices]
 for digit in ['index','middle','ring','pinky']:trees[digit]=BVHTree.FromPolygons(v,faces[digit],all_triangles=True)
 e.to_mesh_clear();vv=[];ff=[]
 for part in s.objects:
  if not part.name.startswith('VG_' if variant=='vertical' else 'PH_'):continue
  ev=part.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();mesh.calc_loop_triangles();offset=len(vv);vv.extend([ev.matrix_world@x.co for x in mesh.vertices]);ff.extend([tuple(i+offset for i in t.vertices) for t in mesh.loop_triangles]);ev.to_mesh_clear()
 trees['grip']=BVHTree.FromPolygons(vv,ff,all_triangles=True)
 b=r.pose.bones['thumb_01_l'];base=b.rotation_quaternion.copy();best=None
 def evaluate(params):
  b.rotation_quaternion=base@Quaternion((1,0,0),math.radians(params[0]))@Quaternion((0,1,0),math.radians(params[1]))@Quaternion((0,0,1),math.radians(params[2]));bpy.context.view_layer.update();ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();v=[ev.matrix_world@x.co for x in m.vertices];t=BVHTree.FromPolygons(v,faces['thumb'],all_triangles=True);hits=sum(len(t.overlap(tree)) for tree in trees.values());near=sorted(trees['index'].find_nearest(v[i])[3] for i in ids['thumb']);gap=sum(near[:5])/5;ev.to_mesh_clear();return hits*10+abs(gap-.0008)*1000+sum(x*x for x in params)*.0004,hits,gap
 for params in itertools.product([-12,-6,0,6,12],repeat=3):
  score,hits,gap=evaluate(params)
  if best is None or score<best[0]:best=(score,params,hits,gap)
 center=best[1]
 for delta in itertools.product([-2,0,2],repeat=3):
  params=tuple(a+b for a,b in zip(center,delta));score,hits,gap=evaluate(params)
  if score<best[0]:best=(score,params,hits,gap)
 evaluate(best[1]);result=measure(r,G,'VG_' if variant=='vertical' else 'PH_');result['thumb_refinement']=best
 (d/'final_measure.json').write_text(json.dumps(result,indent=2));print('FINAL',variant,result,flush=True)
 fit['basis']={b.name:[list(x) for x in b.matrix_basis] for b in r.pose.bones if b.name.startswith(('index','middle','ring','pinky','thumb')) and b.name.endswith('_l')};(d/'fit_final.json').write_text(json.dumps(fit,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(d/'FinalFit.blend'));setup_render(r,G,'final_'+variant)
