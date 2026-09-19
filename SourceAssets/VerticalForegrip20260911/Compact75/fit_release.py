import bpy,json,math,itertools
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'A_M4_Vertical_idle.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;s.frame_set(0);bpy.context.view_layer.update();r.animation_data.action=None
data=json.loads((O/'fit_final.json').read_text());G=r.pose.bones['WPN_root'].matrix@Matrix(data['grip_in_root']);inv=G.inverted()
ob=bpy.data.objects['SK_Manny_Arms_Export'];groups={g.index:g.name for g in ob.vertex_groups}
ids={v.index for v in ob.data.vertices if sum(g.weight for g in v.groups if groups[g.group].endswith('_l') and groups[g.group].startswith(('hand','index','middle','ring','pinky','thumb')))>.5}
dg=bpy.context.evaluated_depsgraph_get();grip=next(o for o in s.objects if o.name.startswith('VG_'));e=grip.evaluated_get(dg);m=e.to_mesh();m.calc_loop_triangles();tree=BVHTree.FromPolygons([inv@e.matrix_world@v.co for v in m.vertices],[tuple(t.vertices) for t in m.loop_triangles],all_triangles=True);e.to_mesh_clear()
def smooth(x):x=max(0,min(1,x));return x*x*(3-2*x)
best=None
for delay in [1,1.5,2,3]:
 samples=[]
 for k in range(1,9):
  t=k/8;opening=smooth(t*delay)
  for n,b in r.pose.bones.items():
   if n.startswith(('index','middle','ring','pinky')) and n.endswith('_l'):
    q=Matrix(data['basis'][n]).to_quaternion()
    if '_02_' in n or '_03_' in n or '_01_' in n:
     angle=(15 if '_02_' in n else 10 if '_03_' in n else 0) if n.startswith('pinky') else 0
     q=q.slerp(Quaternion((0,0,1),math.radians(angle)),opening)
    b.rotation_quaternion=q
  bpy.context.view_layer.update();e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();m.calc_loop_triangles()
  vv=[inv@e.matrix_world@v.co for v in m.vertices];ff=[tuple(t.vertices) for t in m.loop_triangles if any(i in ids for i in t.vertices)];samples.append((t,vv,ff));e.to_mesh_clear()
 for x,y,z in itertools.product([-.06,-.03,0,.03,.06],[.03,.06,.09,.12],[-.04,0,.04]):
  shift=Vector((x,y,z));total=worst=0
  for t,vv,ff in samples:
   delta=shift*smooth(t);ht=BVHTree.FromPolygons([v+delta for v in vv],ff,all_triangles=True);hits=len(set(i for i,j in ht.overlap(tree)));total+=hits;worst=max(worst,hits)
  score=total*10+worst*20+shift.length*100
  if best is None or score<best[0]:best=(score,[x,y,z],delay,total,worst);print('RELEASE_CANDIDATE',best,flush=True)
data['release_vector']=best[1];data['release_open_speed']=best[2];data['release_open_delay']=0
(O/'fit_final.json').write_text(json.dumps(data,indent=2));(O/'release_fit.json').write_text(json.dumps({'translation_m':best[1],'opening_delay_fraction':best[2],'total_crossings':best[3],'max_crossings':best[4]},indent=2));print('PRISM_RELEASE_FIT_DONE',best,flush=True)
