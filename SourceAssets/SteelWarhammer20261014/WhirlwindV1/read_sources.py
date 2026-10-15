"""Read the actual editable motion and grip/rest inputs needed for adaptation."""
import bpy,json
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2]
report={}
for key,file,rig_name in (
    ('sword',R/'SourceAssets/Whirlwind20260920/RecoverV6/WhirlwindRecover_Manny_Editable.blend','SK_RuneSword_Rig'),
    ('hammer',P.parent/'NormalComboV4/Warhammer_Combo_Restored_Editable.blend','SK_RusticPickaxe_Rig')):
    bpy.ops.wm.open_mainfile(filepath=str(file));rig=bpy.data.objects[rig_name]
    action=rig.animation_data.action
    if key=='hammer':
        action=bpy.data.actions['A_Warhammer_Slash1'];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    bones=['root','clavicle_l','upperarm_l','lowerarm_l','hand_l','clavicle_r','upperarm_r','lowerarm_r','hand_r','WPN_root']
    data={'file':str(file),'action':action.name,'fps':bpy.context.scene.render.fps,'frame_range':list(action.frame_range),
        'rest':{n:[list(row) for row in rig.data.bones[n].matrix_local] for n in bones if n in rig.data.bones},'samples':{}}
    for seconds in ([0,.5,1.3,1.82] if key=='sword' else [0]):
        f=seconds*bpy.context.scene.render.fps;bpy.context.scene.frame_set(int(f),subframe=f-int(f))
        pose={n:rig.pose.bones[n].matrix.copy() for n in bones if n in rig.pose.bones}
        data['samples'][str(seconds)]={n:[list(row) for row in m] for n,m in pose.items()}
        data['samples'][str(seconds)]['hand_spacing_m']=(pose['hand_l'].translation-pose['hand_r'].translation).length
        data['samples'][str(seconds)]['grips']={s:[list(row) for row in pose['WPN_root'].inverted()@pose['hand_'+s]] for s in ('l','r')}
    report[key]=data
(P/'source_inputs.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:{'action':v['action'],'fps':v['fps'],'frames':v['frame_range'],
    'hand_spacing':{t:p['hand_spacing_m'] for t,p in v['samples'].items()},
    'initial_grips':v['samples']['0']['grips']} for k,v in report.items()}))
