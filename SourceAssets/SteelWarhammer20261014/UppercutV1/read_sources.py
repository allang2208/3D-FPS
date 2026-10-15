"""Read the two native authoring rigs and the current sword uppercut phase poses."""
import bpy,json
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2];report={}
for key,path in (
    ('sword',R/'SourceAssets/SwordUppercut20261003/GripRecoveryV15/LongGrip/Sword_UppercutV15_Editable.blend'),
    ('hammer',P.parent/'NormalComboV4/Warhammer_Combo_Restored_Editable.blend')):
    bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene
    r=next(o for o in s.objects if o.type=='ARMATURE')
    if key=='hammer':
        r.animation_data.action=bpy.data.actions['A_Warhammer_Slash1']
        r.animation_data.action_slot=r.animation_data.action.slots[0]
    data={'path':str(path),'rig':r.name,'fps':s.render.fps,'action':r.animation_data.action.name,
          'rest':{b.name:[list(row) for row in b.matrix_local] for b in r.data.bones},'samples':{}}
    for t in ([0,.5,1.,1.05,1.075,1.125,1.266667,2.05] if key=='sword' else [0]):
        f=t*s.render.fps;s.frame_set(int(f),subframe=f-int(f))
        pose={b.name:b.matrix.copy() for b in r.pose.bones}
        data['samples'][str(t)]={'pose':{n:[list(row) for row in m] for n,m in pose.items()},
            'hand_spacing_m':(pose['hand_l'].translation-pose['hand_r'].translation).length,
            'grips':{side:[list(row) for row in pose['WPN_root'].inverted()@pose['hand_'+side]] for side in ('l','r')}}
    report[key]=data
(P/'source_inputs.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:{'rig':v['rig'],'fps':v['fps'],'action':v['action'],
    'spacing_m':{t:x['hand_spacing_m'] for t,x in v['samples'].items()}} for k,v in report.items()}))
