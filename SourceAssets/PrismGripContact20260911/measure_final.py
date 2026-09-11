import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;result={}
for label,p in [('before',O.parent/'VerticalGripRaised20260911/prism'),('after',O/'prism')]:
 bpy.ops.wm.open_mainfile(filepath=str(p/'A_M4_Prism_idle.blend'));r=bpy.data.objects['SK_M4_Infima'];bpy.context.scene.frame_set(0);bpy.context.view_layer.update();f=json.loads((p/'fit_final.json').read_text());G=r.pose.bones['WPN_root'].matrix@Matrix(f['grip_in_root']);I=G.inverted();out={}
 for d in ['index','middle','ring','pinky']:
  a=I@r.pose.bones[d+'_01_l'].head;b=I@r.pose.bones[d+'_02_l'].head;c=I@r.pose.bones[d+'_03_l'].head;n=(b-a).cross(c-b).normalized();out[d]={'plane_from_horizontal_degrees':math.degrees(math.acos(min(1,abs(n.z)))),'mcp_z_mm':a.z*1000}
 rest=r.data.bones;l=r.pose.bones['lowerarm_l'];h=r.pose.bones['hand_l'];v=(h.head-l.head).normalized();d=h.matrix.to_3x3()@rest['hand_l'].matrix_local.to_3x3().inverted()@(rest['hand_l'].head_local-rest['lowerarm_l'].head_local).normalized();out['wrist_axis_bend_degrees']=math.degrees(v.angle(d));result[label]=out
(O/'pose_metrics.json').write_text(json.dumps(result,indent=2));print('POSE_METRICS',result)
