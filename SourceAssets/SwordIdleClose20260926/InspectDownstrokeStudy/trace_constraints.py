"""Replay the author solver in memory; stop before export/save. No asset edits."""
import json
from pathlib import Path
P=Path(__file__).parent
source=P.parents[1]/'RuneSword20260913/InspectRhythmContactV80/author_inspect_v80.py'
code=source.read_text(encoding='utf-8')
code=code.split('\nfor layer in action.layers:\n    for strip in layer.strips:\n        for bag in strip.channelbags:\n            for curve in bag.fcurves:')[0]
old="        limit_wrist(pose, 'r', WRIST_TWIST_LIM_R, WRIST_BEND_LIM_R)"
new="""        before_cap = pose['hand_r'].to_quaternion().copy()
        desired_bend = wrist_axis_bend_deg(pose, 'r')
        limit_wrist(pose, 'r', WRIST_TWIST_LIM_R, WRIST_BEND_LIM_R)
        if .20 <= seconds <= .53:
            trace.append({'seconds':seconds, 'theta':theta, 'grip':grip,
                'before_final_cap_bend':desired_bend, 'after_final_cap_bend':wrist_axis_bend_deg(pose,'r'),
                'final_cap_rotation_change':math.degrees(before_cap.rotation_difference(pose['hand_r'].to_quaternion()).angle),
                'target_to_final_hand_change':math.degrees(hand_r.to_quaternion().rotation_difference(pose['hand_r'].to_quaternion()).angle),
                'finger_amounts':dict(amount_for_current)})"""
if code.count(old)!=1:raise RuntimeError('Author trace hook changed')
trace=[]
scope={'__file__':str(source),'__name__':'downstroke_diagnostic_replay','trace':trace}
exec(compile(code.replace(old,new),str(source),'exec'),scope)
(P/'constraint_trace.json').write_text(json.dumps(trace,indent=2),encoding='utf-8')
print('DOWNSTROKE_CONSTRAINT_TRACE_COMPLETE_NO_EXPORT_OR_SAVE')
