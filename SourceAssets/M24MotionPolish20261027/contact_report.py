import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M24_MotionPolish_Editable.blend'),use_scripts=False)
s=bpy.context.scene;r=bpy.data.objects['M24_V9_Rig'];skin=bpy.data.objects['M24_V9_BareArms'];bolt=bpy.data.objects['M24_bolt']
a=bpy.data.actions['A_M24_fire'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(28);bpy.context.view_layer.update()
dg=bpy.context.evaluated_depsgraph_get();bo=bolt.evaluated_get(dg);bm=bo.to_mesh();so=skin.evaluated_get(dg);sm=so.to_mesh()
tree=BVHTree.FromPolygons([v.co for v in bm.vertices],[p.vertices[:] for p in bm.polygons])
for finger in ('thumb','index','middle','ring','pinky'):
 items=[]
 for v in skin.data.vertices:
  if sum(g.weight for g in v.groups if skin.vertex_groups[g.group].name.startswith(finger+'_') and skin.vertex_groups[g.group].name.endswith('_r'))<.7:continue
  p=sm.vertices[v.index].co;co,no,_,d=tree.find_nearest(p)
  items.append((d,(p-co).dot(no),v.index))
 print(finger,'near_mm',sorted(round(x[0]*1000,2) for x in items)[:12],'deepest_mm',min(x[1] for x in items)*1000,flush=True)
bo.to_mesh_clear();so.to_mesh_clear()
