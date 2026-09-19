import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4HandMATRepair20260910/M4_Hand_MAT_Editable.blend');r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;a=bpy.data.actions['M4_MAT_reload'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(80);bpy.context.view_layer.update()
mat=r.pose.bones['WPN_SOCKET_Magazine'].matrix.copy();inv=mat.inverted();shift=Vector((0,0,-.008));poses={b.name:b.matrix.copy() for b in r.pose.bones}
b=r.pose.bones['clavicle_l'];m=poses[b.name];m.translation+=mat.to_3x3()@shift;b.matrix=m
bpy.context.view_layer.update();mesh=bpy.data.objects['SK_Manny_Arms_Export'];mag=next(o for o in r.children if o.type=='MESH' and 'Magazine' in o.name);dep=bpy.context.evaluated_depsgraph_get();ev=mag.evaluated_get(dep);m=ev.to_mesh();vs=[inv@ev.matrix_world@v.co for v in m.vertices];tree=BVHTree.FromPolygons(vs,[list(p.vertices) for p in m.polygons]);ev.to_mesh_clear();bounds=[[min(p[i] for p in vs),max(p[i] for p in vs)] for i in range(3)]
base={b.name:b.rotation_quaternion.copy() for b in r.pose.bones};result={}
for digit in ['index','middle','ring','pinky','thumb']:
 ids=[v.index for v in mesh.data.vertices if sum(g.weight for g in v.groups if mesh.vertex_groups[g.group].name.startswith(digit) and mesh.vertex_groups[g.group].name.endswith('_l'))>.4]
 def evaluate():
  bpy.context.view_layer.update();ev=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();ps=[inv@ev.matrix_world@m.vertices[i].co for i in ids];ev.to_mesh_clear();ds=[]
  for p in ps:
   if not(bounds[1][0]<p.y<bounds[1][1] and bounds[2][0]<p.z<bounds[2][1]):continue
   left=tree.ray_cast(Vector((-.1,p.y,p.z)),Vector((1,0,0)),.2)[0];right=tree.ray_cast(Vector((.1,p.y,p.z)),Vector((-1,0,0)),.2)[0]
   if left is not None and right is not None and left.x<p.x<right.x:ds.append(min(p.x-left.x,right.x-p.x)*1000)
  return sum(d*d for d in ds)+len([d for d in ds if d>.5])*10,max(ds,default=0),len(ds)
 before=evaluate();offset=[0,0,0]
 for step in [15,8,4,2]:
  for iteration in range(3):
   changed=False
   for j in [2,3,1]:
    n=f'{digit}_{j:02}_l';b=r.pose.bones[n];current=offset[j-1];best=evaluate()[0]+sum(v*v for v in offset)*.025;choose=current
    for d in [current-step,current+step]:
     if abs(d)>40:continue
     q=base[n]@Quaternion(Vector((0,0,1)),math.radians(d));ez=math.degrees(q.to_euler().z)
     if digit!='thumb' and not ((-45 if j==1 else -5)<=ez<=(85 if j==1 else 100 if j==2 else 75)):continue
     b.rotation_quaternion=q;cost=evaluate()[0]+(sum(v*v for v in offset)-current*current+d*d)*.025
     if cost<best:best=cost;choose=d
    offset[j-1]=choose;b.rotation_quaternion=base[n]@Quaternion(Vector((0,0,1)),math.radians(choose));changed|=choose!=current
   if not changed:break
 result[digit]={'before':before,'after':evaluate(),'offset_deg':offset}
result['shift']=list(shift);result['finger_local_rotations']={f'{digit}_{j:02}_l':list(r.pose.bones[f'{digit}_{j:02}_l'].rotation_quaternion) for digit in ['thumb','index','middle','ring','pinky'] for j in [1,2,3]}
(O/'fitted_grip.json').write_text(json.dumps(result,indent=2));print('FINGER_FIT',json.dumps(result))
