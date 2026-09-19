import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Hand_MAT_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];a=bpy.data.actions['M4_MAT_equip_charge'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(18);bpy.context.view_layer.update();inv=r.pose.bones['WPN_root'].matrix.inverted();dg=bpy.context.evaluated_depsgraph_get()
for name in ['M4_M4 Body_Export','M4_Stock Classic Unreal_Export','SK_Manny_Arms_Export']:
 obj=bpy.data.objects[name];ev=obj.evaluated_get(dg);m=ev.to_mesh()
 for bn in (['WPN_ChargingHandle'] if 'Body' in name else ['WPN_root'] if 'Stock' in name else ['index_03_r','middle_03_r','thumb_03_r']):
  inds=[v.index for v in obj.data.vertices if any(obj.vertex_groups[g.group].name==bn and g.weight>.7 for g in v.groups)]
  ps=[inv@ev.matrix_world@m.vertices[i].co for i in inds]
  if ps:print(name,bn,'bounds',[[round(min(v[j] for v in ps),4),round(max(v[j] for v in ps),4)] for j in range(3)],'center',list(sum(ps,Vector())/len(ps)))
 ev.to_mesh_clear()
