import json
import sys
from pathlib import Path

import numpy as np

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding='utf-8-sig'))
rows = []
for case in data['cases']:
    pose = np.asarray(case['samples'], dtype=float)
    step = np.linalg.norm(np.diff(pose[:, :, :3], axis=0), axis=2)
    highpass = np.linalg.norm(pose[1:-1, :, :3] - (pose[:-2, :, :3] + pose[2:, :, :3]) * .5, axis=2)
    dots = np.abs(np.sum(pose[1:, :, 3:] * pose[:-1, :, 3:], axis=2))
    angles = np.rad2deg(2 * np.arccos(np.clip(dots, 0, 1)))
    row = {k: case[k] for k in ('action', 'speed', 'direction', 'post_process')}
    row['bones'] = {
        name: {
            'step_max_cm': float(step[:, i].max()),
            'step_p95_cm': float(np.percentile(step[:, i], 95)),
            'highpass_p95_cm': float(np.percentile(highpass[:, i], 95)),
            'angle_max_deg': float(angles[:, i].max()),
            'angle_p95_deg': float(np.percentile(angles[:, i], 95)),
            'range_cm': np.ptp(pose[:, i, :3], axis=0).tolist(),
        } for i, name in enumerate(data['bones'])
    }
    rows.append(row)
report = dict(scope=data['scope'], fps=data['fps'], rendered=False, cases=rows)
path.with_name('metrics.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
for row in rows:
    if not row['post_process']:
        continue
    a = row['bones']['head']
    b = row['bones']['spine_03']
    print(f"{row['action']:20s} speed={row['speed']:3.0f} direction={row['direction']:3.0f} "
          f"head_step={a['step_max_cm']:.3f} highpass95={a['highpass_p95_cm']:.3f} "
          f"chest_angle={b['angle_max_deg']:.3f} range={a['range_cm']}")
