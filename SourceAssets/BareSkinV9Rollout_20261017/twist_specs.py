"""Offline: per flagged clip, the forearm axis and bind relations the UE writer needs (no scipy in UE).

Writes Work/<batch>/twist_specs.json: {clip path: {pose_source, mesh, sides: {s: {axis_l, rel_hand, rel_t1, rel_t2}}}}.
"""
import sys, json
import numpy as np
from rollout import R, load_snapshot
from twist_fix import SideTwist, SHARE1, SHARE2

BATCH = sys.argv[1]
plan = json.loads((R / (BATCH + '.json')).read_text())
tp = json.loads((R / 'Work' / BATCH / 'twist_plan.json').read_text())
specs = {}
for ps, clips in tp.items():
    vm = plan['viewmodels'][ps]; ref = load_snapshot(vm)['bones']
    for path, sides in clips.items():
        if path in specs: continue
        row = dict(pose_source=ps, mesh=vm, shares=[SHARE1, SHARE2], sides={})
        for s in sides:
            st = SideTwist(ref, s)
            row['sides'][s] = dict(axis_l=st.axis_l.tolist(), rel_hand=st.rel_ref['hand_' + s].as_quat().tolist(),
                                   rel_t1=st.rel_ref['lowerarm_twist_01_' + s].as_quat().tolist(),
                                   rel_t2=st.rel_ref['lowerarm_twist_02_' + s].as_quat().tolist())
        specs[path] = row
(R / 'Work' / BATCH / 'twist_specs.json').write_text(json.dumps(specs, indent=1))
print(len(specs), 'clips')
