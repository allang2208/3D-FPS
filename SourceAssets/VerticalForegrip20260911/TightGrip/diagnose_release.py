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

for k in range(9):
 t=k/8;opening=smooth(t*data['release_open_speed'])
 for n,b in r.pose.bones.items():
  if n.startswith(('index','middle','ring','pinky')) and n.endswith('_l'):
   q=Matrix(data['basis'][n]).to_quaternion()
   if any(x in n for x in ['_01_','_02_','_03_']):
    angle=(15 if '_02_' in n else 10 if '_03_' in n else 0) if n.startswith('pinky') else 0
    q=q.slerp(Quaternion((0,0,1),math.radians(angle)),opening)
   b.rotation_quaternion=q
 bpy.context.view_layer.update();e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();m.calc_loop_triangles()
 delta=Vector(data['release_vector'])*smooth(t);vv=[inv@e.matrix_world@v.co+delta for v in m.vertices];ff=[tuple(tr.vertices) for tr in m.loop_triangles if any(i in ids for i in tr.vertices)]
 ht=BVHTree.FromPolygons(vv,ff,all_triangles=True);hits=set(i for i,j in ht.overlap(tree));names={}
 for i in hits:
  n=max([(g.weight,groups[g.group]) for vid in ff[i] for g in ob.data.vertices[vid].groups])[1];names[n]=names.get(n,0)+1
 print(t,names,flush=True);e.to_mesh_clear()
