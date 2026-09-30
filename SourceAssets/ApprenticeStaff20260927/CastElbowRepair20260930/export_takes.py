"""Bake the same cast-only sampler into editable 120 Hz camera-space takes."""
import json
import numpy as np
from author_pose import P, SOURCE
from diagnose import read, sample, motion

data, original = read(P/'full-pose.json'), read(SOURCE)
output = dict(fps=120, rest=data['rest'], parent=data['parent'], takes=[])
for variant in data['poses']:
    for phase, duration in [('raise', .95), ('charge_recover', .42), ('ready', .2), ('release', .38), ('recover', .42)]:
        frames = []
        times = np.unique(np.r_[np.arange(0, duration, 1/120), duration])
        for t in times:
            state = motion(original, variant, phase, float(t))
            world = sample(data, variant, state)
            world['staff_grip'] = state[3]
            frames.append(dict(frame=float(t*120), world={n:m.tolist() for n,m in world.items()}))
        output['takes'].append(dict(name='A_Staff_'+phase+'_'+variant+'_Elbow20260930', frames=frames))
(P/'editable-takes.json').write_text(json.dumps(output, separators=(',', ':')), encoding='utf-8')
print('Saved 20 editable takes, 120 Hz; default stationary cast phases.')
