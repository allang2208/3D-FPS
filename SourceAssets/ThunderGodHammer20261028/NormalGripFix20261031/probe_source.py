import bpy, json, math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;R=P.parents[2]
bpy.ops.wm.open_mainfile(filepath=str(R/'SourceAssets/SteelWarhammer20261014/NormalComboRhythmV7/Warhammer_Combo_Rhythm_Editable.blend'))
rig=bpy.data.objects['SK_RusticPickaxe_Rig'];scene=bpy.context.scene
out={}
for stage in range(1,4):
    for suffix in ('','Recover'):
        name=f'A_Warhammer_Slash{stage}{suffix}';a=bpy.data.actions[name]
        rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
        rows=[]
        for i in range(121):
            f=float(a.frame_range[1])*i/120;scene.frame_set(int(f),subframe=f-int(f))
            w=rig.pose.bones['WPN_root'].matrix.inverted()
            row={'t':f/300,'hands':{}}
            for s in 'lr':
                hand=w@rig.pose.bones['hand_'+s].matrix
                pt=hand.translation
                row['hands'][s]={'z':pt.z,'r':math.hypot(pt.x+.00045,pt.y+.00105),'p':list(pt),
                    'digits':{d:list(w@rig.pose.bones[d+'_03_'+s].matrix.translation) for d in ('thumb','index','middle','ring','pinky')}}
            rows.append(row)
        out[name]=rows
(P/'source_before.json').write_text(json.dumps(out),encoding='utf-8')
print('GRIP_SOURCE '+json.dumps({n:{s:{'radius_mm':[round(min(x['hands'][s]['r'] for x in a)*1000,2),round(max(x['hands'][s]['r'] for x in a)*1000,2)],'z_mm':[round(min(x['hands'][s]['z'] for x in a)*1000,2),round(max(x['hands'][s]['z'] for x in a)*1000,2)],'peak_time':max(a,key=lambda x:x['hands'][s]['r'])['t']} for s in 'lr'} for n,a in out.items()}))
