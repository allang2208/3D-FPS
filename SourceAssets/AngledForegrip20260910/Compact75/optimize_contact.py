import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'A_M4_Foregrip_idle.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;s.frame_set(0);bpy.context.view_layer.update();r.animation_data.action=None
f=json.loads((O/'fit_final.json').read_text());root=r.pose.bones['WPN_root'].matrix.copy();G=root@Matrix(f['grip_in_root']);H=r.pose.bones['hand_l'].matrix.copy();axes=[G.to_3x3().col[i].normalized() for i in range(3)]
trees=[]
for ob in [x for x in s.objects if x.name.startswith('FG_')]:
 e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();m.calc_loop_triangles();trees.append(BVHTree.FromPolygons([e.matrix_world@v.co for v in m.vertices],[tuple(t.vertices) for t in m.loop_triangles],all_triangles=True));e.to_mesh_clear()
ob=bpy.data.objects['SK_Manny_Arms_Export'];groups={g.index:g.name for g in ob.vertex_groups};labels={v.index:max([(g.weight,groups[g.group]) for g in v.groups if groups[g.group].endswith('_l')],default=(0,''))[1].split('_')[0] for v in ob.data.vertices};digits=['index','middle','ring','pinky','thumb']
# Translation is a rigid hand placement, flexion stays on the verified Z axis.
p=[0,0,0,65,60,35,60,35,60,35,60,35]
def evaluate(p,detail=False):
 T=H.copy();T.translation+=sum((axes[i]*p[i] for i in range(3)),Vector());r.pose.bones['hand_l'].matrix=T
 for digit,vals in [('pinky',p[3:6]),('index',[0,*p[6:8]]),('middle',[0,*p[8:10]]),('ring',[0,*p[10:12]])]:
  for j,deg in enumerate(vals,1):r.pose.bones[f'{digit}_{j:02}_l'].rotation_quaternion=Quaternion((0,0,1),math.radians(deg))
 bpy.context.view_layer.update();e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();m.calc_loop_triangles();v=[e.matrix_world@x.co for x in m.vertices];faces=[];fl=[]
 for t in m.loop_triangles:
  tag=next((labels[i] for i in t.vertices if labels[i] in digits),'')
  if tag:faces.append(tuple(t.vertices));fl.append(tag)
 tree=BVHTree.FromPolygons(v,faces,all_triangles=True);hit=set()
 for other in trees:hit.update(i for i,j in tree.overlap(other))
 counts={d:sum(fl[i]==d for i in hit) for d in digits}
 # Pinky phalanges must stay on the near side, outside the hole.
 inv=G.inverted();pinky=[inv@r.pose.bones[f'pinky_{j:02}_l'].head for j in [2,3]]
 outside=sum(max(0,.20-x.y)**2 for x in pinky)*10000
 score=len(hit)*30+outside+sum((p[i]/.012)**2 for i in range(3))+sum(((p[i]-60)/35)**2 for i in [6,8,10])
 e.to_mesh_clear()
 return (score,counts,[list(x) for x in pinky]) if detail else score
bounds=[(-.018,.022),(-.025,.025),(-.025,.01),(45,100),(30,75),(15,45),(35,70),(15,45),(35,70),(15,45),(35,70),(15,45)]
for step in [.006,.003,.0015]:
 for iteration in range(4):
  changed=False
  for i in range(len(p)):
   best=(evaluate(p),p.copy())
   for sign in [-1,1]:
    q=p.copy();q[i]=max(bounds[i][0],min(bounds[i][1],q[i]+sign*(step if i<3 else step*2000)))
    score=evaluate(q)
    if score<best[0]:best=(score,q)
   if best[1]!=p:changed=True;p=best[1]
  print('FIT_STEP',step,iteration,p,evaluate(p,True),flush=True)
  if not changed:break
import itertools
best=(evaluate(p),p.copy());origin=p.copy()
for dx,dy,dz in itertools.product([-.002,-.001,0,.001,.002],repeat=3):
 q=origin.copy();q[0]+=dx;q[1]+=dy;q[2]+=dz;score=evaluate(q)
 if score<best[0]:best=(score,q)
p=best[1]
result=evaluate(p,True);f['hand_in_root']=[list(v) for v in root.inverted()@r.pose.bones['hand_l'].matrix]
for b in r.pose.bones:
 if b.name.startswith(tuple(digits)):f['basis'][b.name]=[list(v) for v in b.matrix_basis]
f['compact_fit']={'parameters':p,'score':result[0],'collisions':result[1],'pinky_points':result[2]};(O/'fit_final.json').write_text(json.dumps(f,indent=2));print('COMPACT_OPTIMIZED',f['compact_fit'])
