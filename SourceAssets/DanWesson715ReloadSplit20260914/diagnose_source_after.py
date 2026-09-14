"""Focused follow-up to the user's loading-hand displacement report."""
import bpy,json,math
from pathlib import Path
O=Path(__file__).parent
try:bpy.ops.wm.open_mainfile(filepath=str(O/'DanWesson715_ReloadSplit_Editable.blend'))
except RuntimeError as error:
    if 'Missing library override hierarchy root data' not in str(error):raise
r=bpy.data.objects['SK_DW715_Manny'];s=bpy.context.scene;report={}
manifest=json.loads((O/'animation.json').read_text())
for kind in ['single_0_6','single_3_3']:
    a=bpy.data.actions['DW715_Split_'+kind];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
    entry=manifest['clips'][kind];duration=entry['duration'];begin=1.5 if entry['empty'] else .6
    end=duration-.7;last={};jumps=[]
    for i in range(round(duration*120)+1):
        f=i*.5;s.frame_set(int(f),subframe=f%1);G=r.pose.bones['WPN_root'].matrix.copy()
        for n in ['hand_l','lowerarm_l','upperarm_l','clavicle_l','thumb_03_l','index_03_l']:
            m=G.inverted()@r.pose.bones[n].matrix
            if n in last:
                angle=math.degrees(m.to_quaternion().rotation_difference(last[n].to_quaternion()).angle)
                jumps.append({'time':i/120,'bone':n,'step_cm':(m.translation-last[n].translation).length*100,'step_degrees':min(angle,360-angle)})
            last[n]=m.copy()
    loading=[x for x in jumps if begin<x['time']<end]
    contacts=[x for x in jumps if any(abs(x['time']-t)<.1 for t in entry['seats'])]
    report[kind]={'duration':duration,'loading_peak_steps':sorted(loading,key=lambda x:x['step_cm'],reverse=True)[:12],
        'contact_peak_steps':sorted(contacts,key=lambda x:x['step_cm'],reverse=True)[:12],
        'whole_action_peak_steps':sorted(jumps,key=lambda x:x['step_cm'],reverse=True)[:12]}
    print('DW715_DISPLACEMENT_AFTER',kind,json.dumps(report[kind]),flush=True)
(O/'diagnosis-source-after.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
