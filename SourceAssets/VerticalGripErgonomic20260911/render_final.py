import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;sys.path.insert(0,str(O));from inspect_reference import setup_render
from fit_pose import measure
report={}
for variant in ['vertical','prism']:
 d=O/variant;bpy.ops.wm.open_mainfile(filepath=str(d/'FinalFit.blend'));r=bpy.data.objects['SK_M4_Infima'];bpy.context.view_layer.update();fit=json.loads((d/'fit_final.json').read_text());G=r.pose.bones['WPN_root'].matrix@Matrix(fit['grip_in_root']);p={b.name:b.matrix.copy() for b in r.pose.bones};rest={b.name:b.matrix_local.copy() for b in r.data.bones};v=(p['hand_l'].translation-p['lowerarm_l'].translation).normalized();h=p['hand_l'].to_3x3()@rest['hand_l'].to_3x3().inverted()@(rest['hand_l'].translation-rest['lowerarm_l'].translation).normalized();q=p['hand_l'].to_quaternion()@(p['lowerarm_l'].to_quaternion()@rest['lowerarm_l'].to_quaternion().inverted()@rest['hand_l'].to_quaternion()).inverted();twist=(2*math.atan2(Vector((q.x,q.y,q.z)).dot(v),q.w)+math.pi)%(2*math.pi)-math.pi
 row={'wrist_axis_bend_deg':math.degrees(v.angle(h)),'forearm_twist_deg':math.degrees(twist),'elbow_flex_deg':math.degrees((p['lowerarm_l'].translation-p['upperarm_l'].translation).angle(p['hand_l'].translation-p['lowerarm_l'].translation)),'flexion_plane_degrees':{},'position_mount':{n:list(G.inverted()@p[n].translation) for n in ['upperarm_l','lowerarm_l','hand_l']},'static_surface':measure(r,G,'VG_' if variant=='vertical' else 'PH_')}
 for digit in ['index','middle','ring','pinky']:
  a,b,c=[G.inverted()@p[f'{digit}_{j:02}_l'].translation for j in [1,2,3]];normal=(b-a).cross(c-b).normalized();row['flexion_plane_degrees'][digit]=math.degrees(math.acos(min(1,abs(normal.z))))
 report[variant]=row;setup_render(r,G,'final_'+variant)
(O/'final_pose_metrics.json').write_text(json.dumps(report,indent=2));print('FINAL_POSE_METRICS',report)
