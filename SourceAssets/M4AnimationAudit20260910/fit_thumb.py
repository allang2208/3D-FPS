import bpy,json,math
from pathlib import Path
from mathutils import Quaternion,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Hand_MAT_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];a=bpy.data.actions['M4_MAT_equip_charge'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s=bpy.context.scene;s.frame_set(12);bpy.context.view_layer.update();h=bpy.data.objects['SK_Manny_Arms_Export'];body=bpy.data.objects['M4_M4 Body_Export'];dg=bpy.context.evaluated_depsgraph_get();ev=body.evaluated_get(dg);m=ev.to_mesh();bodytree=BVHTree.FromPolygons([ev.matrix_world@v.co for v in m.vertices],[list(p.vertices) for p in m.polygons]);ev.to_mesh_clear();ids={v.index for v in h.data.vertices if any(h.vertex_groups[g.group].name.startswith('thumb') and h.vertex_groups[g.group].name.endswith('_r') and g.weight>.3 for g in v.groups)};b=r.pose.bones['thumb_01_r'];base=b.rotation_quaternion.copy();rows=[]
for axis in [(1,0,0),(0,1,0),(0,0,1)]:
 for deg in [-15,-10,-5,5,10,15]:
  b.rotation_quaternion=base@Quaternion(Vector(axis),math.radians(deg));bpy.context.view_layer.update();ev=h.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();tree=BVHTree.FromPolygons([ev.matrix_world@v.co for v in m.vertices],[list(p.vertices) for p in m.polygons if any(i in ids for i in p.vertices)]);ev.to_mesh_clear();rows.append({'axis':axis,'degrees':deg,'pairs':len(tree.overlap(bodytree))})
print(rows);(O/'thumb_fit.json').write_text(json.dumps(rows,indent=2))
