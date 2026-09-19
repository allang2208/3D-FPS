import bpy,json,math
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;report=json.loads((O/'finger_anatomy.json').read_text())
for label,file in [('natural','grip_fitted.blend')]:
 bpy.ops.wm.open_mainfile(filepath=str(O/file));r=bpy.data.objects['SK_M4_Infima'];bpy.context.scene.frame_set(0);bpy.context.view_layer.update();rows={}
 for d in ['index','middle','ring','pinky','thumb']:
  bs=[r.pose.bones[f'{d}_{j:02}_l'] for j in [1,2,3]];dirs=[(b.tail-b.head).normalized() for b in bs];rows[d]={'local_euler_degrees':[[math.degrees(x) for x in b.rotation_quaternion.to_euler()] for b in bs],'PIP_IP_and_DIP_bend_degrees':[math.degrees(dirs[i].angle(dirs[i+1])) for i in [0,1]]}
  if label=='natural' and d!='thumb':
   assert rows[d]['PIP_IP_and_DIP_bend_degrees'][0]<85
   assert rows[d]['PIP_IP_and_DIP_bend_degrees'][1]<55
   assert max(abs(math.degrees(x)) for x in r.pose.bones[d+'_metacarpal_l'].rotation_quaternion.to_euler())<.001
 report[label]=rows
(O/'finger_anatomy.json').write_text(json.dumps(report,indent=2));print('NATURAL_FINGER_LIMITS_PASS',report['natural'])
