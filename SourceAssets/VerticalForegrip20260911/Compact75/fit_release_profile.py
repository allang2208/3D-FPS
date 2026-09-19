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

from collections import Counter
profile=[]
digits=['index','middle','ring','pinky','thumb']
digit_ids={d:{v.index for v in ob.data.vertices if sum(g.weight for g in v.groups if groups[g.group].startswith(d) and groups[g.group].endswith('_l'))>.5} for d in digits}
def hits(d,delta):
 bpy.context.view_layer.update();e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();m.calc_loop_triangles();vv=[inv@e.matrix_world@v.co+delta for v in m.vertices];ff=[tuple(tr.vertices) for tr in m.loop_triangles if any(i in digit_ids[d] for i in tr.vertices)];ht=BVHTree.FromPolygons(vv,ff,all_triangles=True);count=len(set(i for i,j in ht.overlap(tree)));e.to_mesh_clear();return count
for k in range(37):
 t=k/36;opening=smooth(t*1.5);delta=Vector(data['release_vector'])*smooth(t);entry={'u':t,'basis':{}}
 for n,b in r.pose.bones.items():
  if n.endswith('_l') and n.startswith(tuple(digits)):
   q=Matrix(data['basis'][n]).to_quaternion()
   if not n.startswith('thumb') and any(x in n for x in ['_01_','_02_','_03_']):q=q.slerp(Quaternion((0,0,1),0),opening)
   b.rotation_quaternion=q
 for d in digits:
  current=hits(d,delta)
  if current and t>0:
   bones=[r.pose.bones[f'{d}_{i:02}_l'] for i in [1,2,3]];native=[b.rotation_quaternion.copy() for b in bones];best=None
   values=[-30,-15,0,15,30] if d=='thumb' else [-20,-10,0,10,20]
   for x,y,z in itertools.product(values,repeat=3):
    if d=='thumb':
     bones[0].rotation_quaternion=native[0]@Quaternion((1,0,0),math.radians(x))@Quaternion((0,1,0),math.radians(y))@Quaternion((0,0,1),math.radians(z))
    else:
     for b,q,a in zip(bones,native,[x,y,z]):b.rotation_quaternion=q@Quaternion((0,0,1),math.radians(a))
    count=hits(d,delta);score=count*100+abs(x)+abs(y)+abs(z)
    if best is None or score<best[0]:best=(score,[b.rotation_quaternion.copy() for b in bones],count)
   for b,q in zip(bones,best[1]):b.rotation_quaternion=q
  entry.setdefault('hits',{})[d]=hits(d,delta)
 for n,b in r.pose.bones.items():
  if n.endswith('_l') and n.startswith(tuple(digits)):entry['basis'][n]=list(b.rotation_quaternion)
 profile.append(entry);print(t,entry['hits'],flush=True)
(O/'release_profile.json').write_text(json.dumps(profile,indent=2))
