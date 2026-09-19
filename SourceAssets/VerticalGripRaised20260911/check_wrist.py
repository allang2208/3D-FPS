import bpy,json,math
from pathlib import Path
O=Path(__file__).parent;report={}
for label,p in [('before',O.parent/'VerticalGripClass20260911/vertical/A_M4_Vertical_idle.blend'),('after',O/'vertical/A_M4_Vertical_idle.blend')]:
 bpy.ops.wm.open_mainfile(filepath=str(p));r=bpy.data.objects['SK_M4_Infima'];bpy.context.scene.frame_set(0);bpy.context.view_layer.update();rest=r.data.bones;l=r.pose.bones['lowerarm_l'];h=r.pose.bones['hand_l'];v=(h.head-l.head).normalized();d=h.matrix.to_3x3()@rest['hand_l'].matrix_local.to_3x3().inverted()@(rest['hand_l'].head_local-rest['lowerarm_l'].head_local).normalized();report[label]=math.degrees(v.angle(d))
print('WRIST_BEND',report);(O/'wrist_bend.json').write_text(json.dumps(report,indent=2))
