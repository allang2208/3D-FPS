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
 for digit,vals in [('pinky',p[3:6]),('index',[p[12],*p[6:8]]),('middle',[p[13],*p[8:10]]),('ring',[p[14],*p[10:12]])]:
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

def smooth(x):
 x=max(0,min(1,x));return x*x*(3-2*x)
profile=[];p=[0,0,0,89,60,35,60,35,60,35,60,35,0,0,0]
for frame in [k/2 for k in range(23)]:
 opening=smooth(frame/4);retreat=smooth((frame-4)/5);p[1]=.11*retreat
 if frame<=4 or frame>=8.5:
  for i in [6,8,10]:p[i]=60*(1-opening)
  for i in [7,9,11]:p[i]=35*(1-opening)
  for i in [12,13,14]:p[i]=0
  counts=evaluate(p,True)[1];profile.append({'frame':frame,'parameters':p.copy(),'hits':counts});print('RELEASE_FRAME',profile[-1],flush=True);continue
 prior=p.copy()
 for digit,indices in [('index',[12,6,7]),('middle',[13,8,9]),('ring',[14,10,11])]:
  target=[0,60*(1-opening),35*(1-opening)]
  def score(q):
   hits=evaluate(q,True)[1][digit]
   return hits*100+sum((q[i]-t)**2*.0005+(q[i]-prior[i])**2*.00005 for i,t in zip(indices,target))
  for step in [15,5,2]:
   for cycle in range(2):
    for j,i in enumerate(indices):
     best=(score(p),p.copy())
     for v in [p[i]-step,p[i]+step,target[j]]:
      q=p.copy();q[i]=max(-25 if j==0 else 0,min(25 if j==0 else 70 if j==1 else 45,v));val=score(q)
      if val<best[0]:best=(val,q)
     p=best[1]
 counts=evaluate(p,True)[1];profile.append({'frame':frame,'parameters':p.copy(),'hits':counts});print('RELEASE_FRAME',profile[-1],flush=True)
(O/'release_profile.json').write_text(json.dumps(profile,indent=2))
