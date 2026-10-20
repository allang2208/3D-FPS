"""Twist specs straight from the audit (Work/<batch>_twist.json): every clip side whose twist_01 strays > 15 deg
from the hand roll or twist_02 > 10 deg from half of it -> Work/<batch>/twist_specs.json (+ twist_plan.json)."""
import sys, json
from rollout import R, load_snapshot
from twist_fix import SideTwist, SHARE1, SHARE2

for batch in sys.argv[1:]:
    plan = json.loads((R / (batch + '.json')).read_text()); audit = json.loads((R / 'Work' / (batch + '_twist.json')).read_text())
    specs, tplan = {}, {}
    for ps, vm in plan['viewmodels'].items():
        ref = load_snapshot(vm)['bones']
        for k, sides in audit.get(ps, {}).items():
            path = k.split(':', 1)[1]
            bad = [s for s, x in sides.items() if x['t1_minus_hand'] > 15 or x['t2_minus_half'] > 10]
            if not bad: continue
            tplan.setdefault(ps, {})[path] = bad
            if path in specs: continue
            row = dict(pose_source=ps, mesh=vm, shares=[SHARE1, SHARE2], sides={})
            for s in bad:
                st = SideTwist(ref, s)
                row['sides'][s] = dict(axis_l=st.axis_l.tolist(), rel_hand=st.rel_ref['hand_' + s].as_quat().tolist(),
                                       rel_t1=st.rel_ref['lowerarm_twist_01_' + s].as_quat().tolist(), rel_t2=st.rel_ref['lowerarm_twist_02_' + s].as_quat().tolist())
            specs[path] = row
    (R / 'Work' / batch).mkdir(exist_ok=True)
    (R / 'Work' / batch / 'twist_specs.json').write_text(json.dumps(specs, indent=1))
    (R / 'Work' / batch / 'twist_plan.json').write_text(json.dumps(tplan, indent=1))
    print(batch, len(specs), 'clips to rewrite')
