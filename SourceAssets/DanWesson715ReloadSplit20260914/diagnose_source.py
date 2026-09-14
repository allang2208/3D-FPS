"""Requested diagnosis: sample the loaded source action at reload contacts."""
import bpy,json,math
from pathlib import Path
O=Path(__file__).parent
try:bpy.ops.wm.open_mainfile(filepath=str(O.parent/'DanWesson715ReloadFlick20260914/DanWesson715_ReloadFlick_Editable.blend'))
except RuntimeError as error:
    if 'Missing library override hierarchy root data' not in str(error):raise
r=bpy.data.objects['SK_DW715_Manny'];s=bpy.context.scene;report={}
for kind in ['single_0_6','single_3_3']:
    a=bpy.data.actions['DW715_Flick_'+kind];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
    duration=float(a.frame_range[1])/60;rows=[];last={};jumps=[]
    for i in range(round(duration*120)+1):
        f=i*.5;s.frame_set(int(f),subframe=f%1);G=r.pose.bones['WPN_root'].matrix.copy();row={}
        for n in ['hand_l','lowerarm_l','upperarm_l','clavicle_l','thumb_03_l','index_03_l']:
            m=G.inverted()@r.pose.bones[n].matrix;row[n]={'position':list(m.translation),'rotation':list(m.to_quaternion())}
            if n in last:
                cm=(m.translation-last[n].translation).length*100
                angle=math.degrees(m.to_quaternion().rotation_difference(last[n].to_quaternion()).angle)
                angle=min(angle,360-angle)
                jumps.append({'time':i/120,'bone':n,'step_cm':cm,'step_degrees':angle})
            last[n]=m.copy()
        rows.append(row)
    contacts=[.55+j*1.15+.91 for j in range(int(kind[-1]))]
    report[kind]={'duration':duration,'peak_steps':sorted(jumps,key=lambda x:x['step_cm'],reverse=True)[:12],
        'contact_peak_steps':sorted([x for x in jumps if any(abs(x['time']-t)<.12 for t in contacts)],key=lambda x:x['step_cm'],reverse=True)[:12], 'samples':rows}
    print('SOURCE_DIAGNOSIS',kind,json.dumps({k:v for k,v in report[kind].items() if k!='samples'}),flush=True)
(O/'diagnosis-source.json').write_text(json.dumps(report),encoding='utf-8')
