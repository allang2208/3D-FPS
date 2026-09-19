import bpy,json,math
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4HK416Replica20260910/M4_HK416_Drum_Editable.blend');r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;report={}
for action,f in [('M4_idle',0),('M4_reload',80),('M4_reload',95),('M4_reload',120)]:
 a=bpy.data.actions[action];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(f);bpy.context.view_layer.update();rows={}
 for d in ['index','middle','ring','pinky','thumb']:
  bs=[r.pose.bones[f'{d}_{j:02}_l'] for j in [1,2,3]];dirs=[(b.tail-b.head).normalized() for b in bs];rows[d]={'local_euler':[list(map(lambda x:round(math.degrees(x),1),b.rotation_quaternion.to_euler())) for b in bs],'bend':[round(math.degrees(dirs[i].angle(dirs[i+1])),1) for i in [0,1]],'meta':list(map(lambda x:round(math.degrees(x),1),r.pose.bones[d+'_metacarpal_l'].rotation_quaternion.to_euler())) if d!='thumb' else None}
 report[action+str(f)]=rows
(O/'native_finger_reference.json').write_text(json.dumps(report,indent=2));print(report)
