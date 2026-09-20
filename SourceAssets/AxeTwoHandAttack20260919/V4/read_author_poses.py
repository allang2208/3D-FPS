"""Read the existing authored key poses as inputs to the left-arm correction.
No rendering, runtime playback, mesh changes or acceptance assertions.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector

here=Path(__file__).resolve().parent
source=here.parent/'V3/Axe_TwoHand_Attack_V3_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
rig=bpy.data.objects['SK_Harvest_Axe_Rig']
scene=bpy.context.scene
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
frames=[]
for clip,times in [('Swing',[0,.17,.275,.405,.458,.48,.515,.61,.74,.90,1.1]),
                   ('HitRecover',[.48,.63,.755,.91,1.04,1.21,1.4])]:
    rig.animation_data.action=bpy.data.actions['A_Harvest_Axe_'+clip]
    rig.animation_data.action_slot=rig.animation_data.action.slots[0]
    for t in times:
        s=(t-.48)*.44/.92 if clip=='HitRecover' else t*.24/.48 if t<=.48 else .24+(t-.48)*.44/.62
        frame=s*300
        scene.frame_set(int(frame),subframe=frame-int(frame))
        bpy.context.view_layer.update()
        pose={b.name:b.matrix.copy() for b in rig.pose.bones}
        upper,fore,hand=[pose[n+'_l'] for n in ('upperarm','lowerarm','hand')]
        axis=(hand.translation-fore.translation).normalized()
        deform=hand.to_quaternion()@rest['hand_l'].to_quaternion().inverted()
        neutral=deform@(rest['hand_l'].translation-rest['lowerarm_l'].translation).normalized()
        frames.append({'clip':clip,'time':t,'wrist_bend_deg':math.degrees(axis.angle(neutral)),
                       'shoulder':list(upper.translation),'elbow':list(fore.translation),
                       'wrist':list(hand.translation),'neutral_forearm':list(neutral),
                       'wrist_local_rotation_deg':math.degrees((fore.inverted()@hand).to_quaternion().rotation_difference(
                           (rest['lowerarm_l'].inverted()@rest['hand_l']).to_quaternion()).angle)})
result={'source':str(source),'left_upper_length':(rest['lowerarm_l'].translation-rest['upperarm_l'].translation).length,
        'left_fore_length':(rest['hand_l'].translation-rest['lowerarm_l'].translation).length,'poses':frames}
(here/'author_inputs.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
