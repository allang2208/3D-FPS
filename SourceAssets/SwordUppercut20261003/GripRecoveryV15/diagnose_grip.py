"""User-requested uppercut grip/recovery diagnosis; no game is run."""
from pathlib import Path
P=Path(__file__).resolve().parent
exec(compile((P/'author_common.py').read_text('utf-8'),str(P/'author_common.py'),'exec'))

def pose(rows):
    return {n:canonical(m) for n,m in globalize({n:native(k) for n,k in rows.items()}).items()}

def rigid(m):
    return mat(m.translation,m.to_quaternion())

def deg(q):
    return math.degrees(2*math.acos(min(1.,abs(q.normalized().w))))

report={'parents':{n:PARENTS[n] for n in ('WPN_root','hand_l','hand_r','Blade_Base','Blade_Tip')},'variants':{}}
for variant in ('Standard','LongGrip'):
    data=json.loads((P/'SourceV14'/variant/'editable_keys.json').read_text('utf-8'))
    idle=pose(data['samples'][0]['bones'])
    grips={s:rigid(idle['WPN_root']).inverted()@rigid(idle['hand_'+s]) for s in ('l','r')}
    rows=[]
    for sample in data['samples']:
        t=sample['seconds']; w=pose(sample['bones']); weapon=rigid(w['WPN_root'])
        row={'t':t,'sides':{}}
        for side in ('l','r'):
            hn,ln,un=('hand_'+side,'lowerarm_'+side,'upperarm_'+side)
            grip=weapon.inverted()@rigid(w[hn])
            delta=w[hn].to_quaternion()@idle[hn].to_quaternion().inverted()
            wrist_axis=delta@(idle[hn].translation-idle[ln].translation).normalized()
            lower=(w[hn].translation-w[ln].translation).normalized()
            row['sides'][side]={'grip_position_drift_cm':(grip.translation-grips[side].translation).length*100,
                'grip_angle_drift_deg':deg(grips[side].to_quaternion().rotation_difference(grip.to_quaternion())),
                'wrist_bend_deg':math.degrees(lower.angle(wrist_axis)),
                'upper_length_cm':(w[ln].translation-w[un].translation).length*100,
                'lower_length_cm':(w[hn].translation-w[ln].translation).length*100,
                'hand_cm':list(w[hn].translation*100),'elbow_cm':list(w[ln].translation*100)}
        rows.append(row)
    out={'selected':[min(rows,key=lambda r:abs(r['t']-t)) for t in (0,.5,1.,1.075,1.125,1.267,1.4,1.6,1.8,2.05)],'peaks':{}}
    for side in ('l','r'):
        out['peaks'][side]={}
        for key in ('grip_position_drift_cm','grip_angle_drift_deg','wrist_bend_deg'):
            worst=max(rows,key=lambda r:r['sides'][side][key])
            out['peaks'][side][key]={'t':worst['t'],'value':worst['sides'][side][key]}
    report['variants'][variant]=out
(P/'diagnosis_v14.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'parents':report['parents'],'peaks':{k:v['peaks'] for k,v in report['variants'].items()}}),flush=True)
