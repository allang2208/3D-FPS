import bpy,json,math
from mathutils import Vector
from pathlib import Path
O=Path(__file__).parent;P=O.parent/'Compact75';bpy.ops.wm.open_mainfile(filepath=str(P/'A_M4_Foregrip_idle.blend'));r=bpy.data.objects['SK_M4_Infima'];bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
u=r.pose.bones['upperarm_l'];l=r.pose.bones['lowerarm_l'];h=r.pose.bones['hand_l'];rest=r.data.bones
v=(h.head-l.head).normalized();desired=h.matrix.to_3x3()@rest['hand_l'].matrix_local.to_3x3().inverted()@(rest['hand_l'].head_local-rest['lowerarm_l'].head_local).normalized();neutral=l.matrix.to_quaternion()@rest['lowerarm_l'].matrix_local.to_quaternion().inverted()@rest['hand_l'].matrix_local.to_quaternion();q=h.matrix.to_quaternion()@neutral.inverted();twist=2*math.atan2(Vector((q.x,q.y,q.z)).dot(v),q.w);twist=(twist+math.pi)%(2*math.pi)-math.pi
print('ARM_MEASURE',json.dumps({'wrist_direction_bend_deg':math.degrees(v.angle(desired)),'wrist_axial_twist_deg':math.degrees(twist),'shoulder':list(u.head),'elbow':list(l.head),'wrist':list(h.head),'ideal_forearm_direction':list(desired)}))
