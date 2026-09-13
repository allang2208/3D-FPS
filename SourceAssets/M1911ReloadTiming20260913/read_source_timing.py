"""Read the accepted action poses to locate the reported inactive reload tail."""
import bpy,json,math
from pathlib import Path
O=Path(__file__).parent
try:bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M1911Contact20260913/M1911_Contact_Editable.blend'))
except RuntimeError as exc:
    if 'Missing library override hierarchy root data' not in str(exc) or 'SK_M1911_Manny' not in bpy.data.objects:raise
r=bpy.data.objects['SK_M1911_Manny'];r.data.pose_position='POSE';s=bpy.context.scene
names=['WPN_root','hand_l','hand_r','WPN_SOCKET_Magazine','WPN_Slide']
def pose(kind,t):
    action=bpy.data.actions['M1911_Contact_'+kind];r.animation_data.action=action;r.animation_data.action_slot=action.slots[0]
    f=t*60;s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
    return {n:r.pose.bones[n].matrix.copy() for n in names}
idle=pose('idle',0)
def error(a,b):
    return {'cm':round((a.translation-b.translation).length*100,4),'deg':round(math.degrees(a.to_quaternion().rotation_difference(b.to_quaternion()).angle),3)}
report={}
for kind,end in [('reload',268/120),('reload_empty',328/120)]:
    final=pose(kind,end);rows=[]
    for frame in range(0,round(end*120)+1):
        t=frame/120;p=pose(kind,t);rootinv=p['WPN_root'].inverted()
        row={'frame120':frame,'time':round(t,6),'idle':{n:error(p[n],idle[n]) for n in names[:3]},'final':{n:error(p[n],final[n]) for n in names[:3]},
             'relative_idle':{n:error(rootinv@p[n],idle['WPN_root'].inverted()@idle[n]) for n in names[1:]}}
        rows.append(row)
    report[kind]={'frame_range':list(bpy.data.actions['M1911_Contact_'+kind].frame_range),'end':end,'samples':rows}
    print(kind,json.dumps([x for x in rows if x['time']>=1.1 and (x['frame120']%12==0 or x==rows[-1])]),flush=True)
(O/'source_timing.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M1911_SOURCE_TIMING_READ',flush=True)
