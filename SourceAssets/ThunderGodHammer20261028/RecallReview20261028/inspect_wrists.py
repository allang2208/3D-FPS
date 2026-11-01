import bpy,json,math,os
from pathlib import Path
P=Path(__file__).resolve().parent;rows={}
for file,clips in [('ThunderThrowV1/ThunderHammer_Throw_Editable.blend',[('A_ThunderHammer_ThrowCharge',2.),('A_ThunderHammer_ThrowRelease',.86)]),('RecallCatchV2/ThunderHammer_RecallCatch_Editable.blend',[('A_ThunderHammer_RecallReady_V2',.32),('A_ThunderHammer_Catch_V2',.60)])]:
    bpy.ops.wm.open_mainfile(filepath=str(P.parent/file));rig=bpy.data.objects['SK_RusticPickaxe_Rig']
    for clip,duration in clips:
        a=bpy.data.actions[clip];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0];worst={};selected=[]
        for i in range(round(duration*240)+1):
            bpy.context.scene.frame_set(i)
            for s in ('l','r'):
                hand=rig.pose.bones['hand_'+s].matrix;elbow=rig.pose.bones['lowerarm_'+s].matrix.translation
                rest=rig.data.bones['hand_'+s].matrix_local;fore=rig.data.bones['lowerarm_'+s].matrix_local
                neutral=hand.to_quaternion()@rest.to_quaternion().inverted()@(rest.translation-fore.translation).normalized()
                angle=math.degrees(neutral.angle((hand.translation-elbow).normalized()))
                if angle>worst.get(s,{}).get('angle',0):worst[s]={'angle':angle,'time':i/240}
                if i in (0,24,58,77,144,312):selected.append({'side':s,'time':i/240,'angle':angle,'hand':list(hand.translation),'elbow':list(elbow)})
        rows[clip]={'worst':worst,'selected':selected}
(P/(os.environ.get('THUNDER_REVIEW_PHASE','before')+'-wrists.json')).write_text(json.dumps(rows,indent=2))
print(json.dumps({k:v['worst'] for k,v in rows.items()}))
