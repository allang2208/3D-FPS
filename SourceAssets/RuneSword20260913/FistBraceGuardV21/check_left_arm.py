"""Focused V20/V21 pose preservation and between-keyframe continuity checks."""
import bpy,json,math
from pathlib import Path

P=Path(__file__).parent
changed={'clavicle_l','upperarm_l','upperarm_twist_01_l','upperarm_twist_02_l'}
sources={}
for version in ('FistBraceGuardV20','FistBraceGuardV21'):
    bpy.ops.wm.open_mainfile(filepath=str(P.parent/version/'AzureRunesword_Manny_Editable.blend'))
    r=bpy.data.objects['SK_RuneSword_Rig'];s=bpy.context.scene
    records={}
    for clip in ('Guard','GuardHit','GuardBreak'):
        a=bpy.data.actions['A_RuneSword_'+clip]
        r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
        start,end=map(int,a.frame_range)
        frames=[]
        for sample in range(start*2,end*2+1):
            f=sample/2;s.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update()
            frames.append({b.name:b.matrix.copy() for b in r.pose.bones})
        records[clip]=frames
    sources[version]=records

report=[]
for clip,before in sources['FistBraceGuardV20'].items():
    after=sources['FistBraceGuardV21'][clip]
    max_position=max_rotation=max_length=0.
    max_upper_step=0.
    for i,(a,b) in enumerate(zip(before,after)):
        for n in a:
            if n in changed:continue
            max_position=max(max_position,(a[n].translation-b[n].translation).length*1000)
            q=a[n].to_quaternion().rotation_difference(b[n].to_quaternion())
            angle=2*math.atan2(math.sqrt(q.x*q.x+q.y*q.y+q.z*q.z),abs(q.w))
            max_rotation=max(max_rotation,math.degrees(angle))
        for root,tip in [('upperarm_l','lowerarm_l'),('lowerarm_l','hand_l')]:
            al=(a[tip].translation-a[root].translation).length
            bl=(b[tip].translation-b[root].translation).length
            max_length=max(max_length,abs(al-bl)*1000)
        if i:
            q=after[i-1]['upperarm_l'].to_quaternion().rotation_difference(b['upperarm_l'].to_quaternion())
            angle=2*math.atan2(math.sqrt(q.x*q.x+q.y*q.y+q.z*q.z),abs(q.w))
            max_upper_step=max(max_upper_step,math.degrees(angle))
    report.append({'clip':clip,'samples_at_960_hz':len(after),'frame_count_unchanged':len(before)==len(after),
        'max_retained_bone_position_delta_mm':max_position,'max_retained_rotation_delta_deg':max_rotation,
        'max_arm_segment_length_delta_mm':max_length,'max_upper_rotation_step_deg_at_960_hz':max_upper_step})
(P/'source_preservation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
