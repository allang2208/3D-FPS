import json,math
from pathlib import Path
import bpy
from mathutils import Vector
P=Path(__file__).parent
author=P.parents[1]/'RuneSword20260913/InspectRhythmContactV80'
bpy.ops.wm.open_mainfile(filepath=str(author/'AzureRunesword_InspectRhythmContactV80.blend'))
s=bpy.context.scene;r=bpy.data.objects['SK_RuneSword_Rig']
base=json.loads((author/'authoring_v80.json').read_text())
s.frame_set(0);bpy.context.view_layer.update()
w0=r.pose.bones['WPN_root'].matrix.to_quaternion()
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
rows=[]
for frame in range(73):
    s.frame_set(frame);bpy.context.view_layer.update()
    m={n:r.pose.bones[n].matrix.copy() for n in ['WPN_root','hand_r','lowerarm_r','upperarm_r']}
    blade=m['WPN_root'].to_quaternion()@w0.inverted()@Vector(base['blade_axis_idle'])
    fore=(m['hand_r'].translation-m['lowerarm_r'].translation).normalized()
    rest_dir=(rest['hand_r'].translation-rest['lowerarm_r'].translation).normalized()
    hand_axis=m['hand_r'].to_quaternion()@rest['hand_r'].to_quaternion().inverted()@rest_dir
    hand=m['hand_r'].translation
    rows.append({'seconds':frame/120.,'hand_cm':list(hand*100),'elbow_cm':list(m['lowerarm_r'].translation*100),
        'blade_dir':list(blade),'blade_elevation_deg':math.degrees(math.asin(max(-1,min(1,blade.z)))),
        'wrist_bend_deg':math.degrees(fore.angle(hand_axis)),
        'hand_screen_percent':[100*(.5+hand.x/(2*hand.y*math.tan(math.radians(37.5))*16/9)),
                               100*(.5-hand.z/(2*hand.y*math.tan(math.radians(37.5))))]})
(P/'source_measurements.json').write_text(json.dumps(rows,indent=2))
print('DOWNSTROKE_SOURCE_MEASURED')
