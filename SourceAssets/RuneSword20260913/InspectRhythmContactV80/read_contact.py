import bpy,sys,json
from pathlib import Path
from mathutils import Vector,kdtree
P=Path(__file__).parent;sys.path.insert(0,str(P));from visible_bare import attach
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'InspectForwardSpinV54/AzureRunesword_InspectForwardSpinV79.blend'))
r=bpy.data.objects['SK_RuneSword_Rig'];a=attach(r);s=bpy.context.scene;s.frame_set(0);bpy.context.view_layer.update();d=bpy.context.evaluated_depsgraph_get()
w=r.pose.bones['WPN_root'].matrix;blade=bpy.data.objects['RuneSword_Blade'];bm=blade.evaluated_get(d).to_mesh();am=a.evaluated_get(d).to_mesh()
pts=[(w.inverted()@(blade.matrix_world@v.co),blade.matrix_world@v.co) for v in bm.vertices];hp=[p for local,p in pts if -.10<local.z<-.03];kd=kdtree.KDTree(len(hp))
for i,p in enumerate(hp):kd.insert(p,i)
kd.balance()
for bone in ['hand_r','thumb_01_r','thumb_02_r','index_01_r','index_02_r','middle_01_r']:
 group=a.vertex_groups[bone].index;rows=[]
 for v in a.data.vertices:
  if not any(g.group==group and g.weight>.35 for g in v.groups):continue
  vp=a.matrix_world@am.vertices[v.index].co;sp,_,dist=kd.find(vp);local=w.inverted()@sp
  if -.075<local.z<-.03:rows.append((dist,v.index,list(local),list(r.pose.bones['hand_r'].matrix.inverted()@sp)))
 print(bone,sorted(rows)[:3])
