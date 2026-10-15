"""Speed/acceleration profile of the three normal hammer cuts (analysis for suggestions only)."""
import json,math
from pathlib import Path
import bpy
from mathutils import Vector

P=Path(__file__).resolve().parent;ROOT=P.parents[3]
FPS=300
def load(path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    return bpy.context.scene,bpy.data.objects['SK_RusticPickaxe_Rig']
def profile(scene,rig,action,seconds):
    rig.animation_data.action=bpy.data.actions[action];rig.animation_data.action_slot=rig.animation_data.action.slots[0]
    rest=rig.data.bones['WPN_root'].matrix_local;head_local=rest.inverted()@Vector((0,0,0))
    hammer=bpy.data.objects['SM_SteelWarhammer'];inv=rest.inverted()
    pts=[inv@v.co for v in hammer.data.vertices];head=[p for p in pts if p.z>.875];hc=sum(head,Vector())/len(head)
    samples=[]
    for i in range(round(seconds*FPS)+1):
        scene.frame_set(i);pb=rig.pose.bones
        samples.append((pb['WPN_root'].matrix@hc,pb['hand_r'].matrix.translation.copy(),pb['lowerarm_l'].matrix.translation.copy(),pb['lowerarm_r'].matrix.translation.copy()))
    speed=[(b[0]-a[0]).length*FPS for a,b in zip(samples,samples[1:])]
    accel=[(b-a)*FPS for a,b in zip(speed,speed[1:])]
    win=lambda a,b:speed[round(a*FPS):round(b*FPS)]
    holds=[];start=None
    for i,s in enumerate(speed):
        if s<.25 and start is None:start=i
        if (s>=.25 or i==len(speed)-1) and start is not None:
            if i-start>=12:holds.append([round(start/FPS,3),round(i/FPS,3)])
            start=None
    peak=max(range(len(speed)),key=lambda i:speed[i])
    return {'head_speed_m_s_at':{f'{t:.2f}':round(speed[min(len(speed)-1,round(t*FPS))],2) for t in (.2,.4,.6,.75,.85,.9,.95,.97,1.0,1.05,1.1,1.2,1.3,1.4,1.5,1.6,1.7)},
        'peak_head_speed':[round(speed[peak],2),round(peak/FPS,3)],'holds_below_0_25_m_s':holds,
        'max_head_accel_m_s2':round(max(abs(a) for a in accel),1),
        'load_mean_speed_0_0_85':round(sum(win(0,.85))/len(win(0,.85)),2),'return_mean_speed_1_3_1_75':round(sum(win(1.3,1.75))/len(win(1.3,1.75)),2)}
report={}
scene,rig=load(ROOT/'SourceAssets/SteelWarhammer20261014/NormalComboV4/Warhammer_Combo_Restored_Editable.blend')
for a in ('A_Warhammer_Slash1','A_Warhammer_Slash3'):report[a]=profile(scene,rig,a,1.75)
report['A_Warhammer_Slash2_V4_old']=profile(scene,rig,'A_Warhammer_Slash2',1.75)
scene,rig=load(P.parent/'Warhammer_Combo_Swap_Editable.blend')
report['A_Warhammer_Slash2_V5_swap']=profile(scene,rig,'A_Warhammer_Slash2',1.75)
(P/'combo_rhythm.json').write_text(json.dumps(report,indent=1),encoding='utf-8')
print('COMBO_RHYTHM '+json.dumps(report))
