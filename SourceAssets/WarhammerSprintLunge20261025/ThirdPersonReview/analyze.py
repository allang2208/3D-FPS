"""Requested lower-body review: native graph poses plus reconstructed capsule travel."""
import json
from pathlib import Path
import numpy as np

OUT = Path(__file__).resolve().parent
data = json.loads((OUT / 'native-graph.json').read_text(encoding='utf-8-sig'))
report = {'scope': data['scope'], 'cases': []}
for variant in data['variants']:
    for case in variant['cases']:
        rows = case['samples']
        t = np.array([r['time'] for r in rows])
        travel = np.array([r['travel'] for r in rows])
        lift = t < case['lift_seconds']
        item = {'variant': variant['variant'], 'case': case['case'], 'rate': case['rate'],
                'airborne': case['airborne'], 'lift_seconds': case['lift_seconds'],
                'lift_final_progress': float(max(r['progress'] for r in rows if r['phase']=='WarhammerSprintLift')),
                'feet': {}}
        for side in ('l', 'r'):
            foot = np.array([r['bones']['foot_' + side][:3] for r in rows])
            world = foot.copy()
            world[:, 1] += travel
            changes = np.linalg.norm(np.diff(foot, axis=0), axis=1)
            handoff = (t[1:] >= case['lift_seconds'] - .04) & (t[1:] <= case['lift_seconds'] + .14)
            item['feet'][side] = {
                'local_shift_during_lift_cm': float(np.linalg.norm(foot[lift][-1] - foot[lift][0])),
                'world_shift_during_lift_cm': float(np.linalg.norm(world[lift][-1] - world[lift][0])),
                'handoff_max_step_cm_per_60hz_frame': float(changes[handoff].max()),
                'handoff_max_step_time': float(t[1:][handoff][changes[handoff].argmax()]),
                'local_height_range_cm': [float(foot[:,2].min()), float(foot[:,2].max())]}
        item['capsule_travel_during_lift_cm'] = float(travel[lift][-1] - travel[lift][0])
        report['cases'].append(item)
(OUT / 'measurements.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
