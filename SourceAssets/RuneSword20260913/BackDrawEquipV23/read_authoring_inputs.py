"""Read existing equip/idle source data needed to author the requested redraw."""
import bpy,json
from pathlib import Path
P=Path(__file__).parent
def read_pose(r):return {b.name:[list(row) for row in b.matrix] for b in r.pose.bones}
source=P.parent/'WeightLeftV5/AzureRunesword_Manny_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(source));s=bpy.context.scene;r=bpy.data.objects['SK_RuneSword_Rig']
old=bpy.data.actions['A_RuneSword_Equip'];r.animation_data.action=old;r.animation_data.action_slot=old.slots[0]
old_frames=[]
for f in (0,66,132):
    s.frame_set(f);bpy.context.view_layer.update()
    old_frames.append({'frame':f,'seconds':f/240,'weapon':list(r.pose.bones['WPN_root'].matrix.translation),
                       'left':list(r.pose.bones['hand_l'].matrix.translation),'right':list(r.pose.bones['hand_r'].matrix.translation)})
old_meta={'source':str(source),'fps':240,'frame_range':list(old.frame_range),'seconds':.55,'loop':False,
          'motion':'Both hands already hold the sword; raise together from 35 cm below idle, pitch -42 degrees to idle',
          'samples':old_frames}
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'ChargedArmV22/AzureRunesword_Manny_Editable.blend'))
s=bpy.context.scene;r=bpy.data.objects['SK_RuneSword_Rig'];a=bpy.data.actions['A_RuneSword_HeavyCharge']
r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0);bpy.context.view_layer.update()
data={'previous_equip':old_meta,'end_pose':read_pose(r),'source':'ChargedArmV22/AzureRunesword_Manny_Editable.blend'}
(P/'authoring_inputs.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
print(json.dumps(old_meta,indent=2))
print('IDLE_CONTACTS',[(n,list(r.pose.bones[n].matrix.translation)) for n in ('upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r','WPN_root')])
