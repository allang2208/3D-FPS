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

import itertools
def smooth(x):
 x=max(0,min(1,x));return x*x*(3-2*x)
best=None
for dx,dz in itertools.product([-.012,-.006,0,.006,.012],repeat=2):
 hits=0;details={}
 for ftime in [k/2 for k in range(19)]:
  opening=smooth(ftime/4);retreat=smooth((ftime-4)/5);offset=opening*(1-retreat)
  p=[dx*offset,.11*retreat,dz*offset,89,60,35,60*(1-opening),35*(1-opening),60*(1-opening),35*(1-opening),60*(1-opening),35*(1-opening)]
  result=evaluate(p,True);count=sum(result[1].values());hits+=count
  if count:details[ftime]=result[1]
 score=hits*100+abs(dx)+abs(dz)
 if best is None or score<best[0]:
  best=(score,dx,dz,hits,details);print('PATH_BEST',best,flush=True)
(O/'release_search.json').write_text(json.dumps(best,indent=2))
