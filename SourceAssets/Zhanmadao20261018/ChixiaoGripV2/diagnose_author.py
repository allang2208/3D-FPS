import json,math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;V1=P.parent/'ChixiaoDoubleHeavyV1'
env={'__file__':str(V1/'author_motion.py')}
exec(compile((V1/'author_motion.py').read_text('utf-8').split('receipt=')[0],str(V1/'author_motion.py'),'exec'),env)
A=env['A'];pose_at=env['pose_at'];rigid=env['grip_frame']
report={}
for variant in ('Standard','LongGrip'):
    clip=json.loads((V1/variant/'editable_keys.json').read_text('utf-8'))
    idle=pose_at(clip,1.);grip0={s:rigid(idle['WPN_root']).inverted()@rigid(idle['hand_'+s]) for s in ('l','r')}
    rows=[]
    for sample in clip['samples']:
        w=A.pose_from_rows(sample['bones']);inv=rigid(w['WPN_root']).inverted();row={'t':sample['seconds']}
        for s in ('l','r'):
            hand,elbow,shoulder=[w[n+'_'+s] for n in ('hand','lowerarm','upperarm')]
            delta=hand.to_quaternion()@idle['hand_'+s].to_quaternion().inverted()
            axis=delta@(idle['hand_'+s].translation-idle['lowerarm_'+s].translation).normalized()
            forearm=(hand.translation-elbow.translation).normalized();g=inv@rigid(hand)
            relative=rigid(hand).inverted()
            finger_error=max(((relative@w[n].translation)-(rigid(idle['hand_'+s]).inverted()@idle[n].translation)).length*100 for n in A.HANDS[s])
            row[s]={'grip_cm':list(g.translation*100),'grip_angle_deg':math.degrees(grip0[s].to_quaternion().rotation_difference(g.to_quaternion()).angle),
                'wrist_bend_deg':math.degrees(axis.angle(forearm)),
                'finger_shape_drift_cm':finger_error,'forearm_cm':(hand.translation-elbow.translation).length*100,
                'upperarm_cm':(elbow.translation-shoulder.translation).length*100,
                'hand_cm':list(hand.translation*100),'elbow_cm':list(elbow.translation*100)}
        rows.append(row)
    selected=[min(rows,key=lambda r:abs(r['t']-t)) for t in (0,.12,.15,.18,.21,.24,.27,.30,.38,.5,.75,1.)]
    report[variant]={'selected':selected,'peaks':{s:{k:max((r for r in rows if r['t']>=.12),key=lambda r:r[s][k]) for k in ('wrist_bend_deg','finger_shape_drift_cm')} for s in ('l','r')}}
(P/'author-diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
for v,d in report.items():
    for s,peaks in d['peaks'].items():print(v,s,{k:(r['t'],round(r[s][k],2)) for k,r in peaks.items()},flush=True)
