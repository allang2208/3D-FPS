"""Author-side data consistency of animation_patch.json (no UE, no gameplay test)."""
import json
import numpy as np
from scipy.spatial.transform import Rotation as R
from r26_core import *

P = json.loads((O / 'animation_patch.json').read_text())
A = json.loads((O / 'authoring.json').read_text())
report = {}
for role, spec in P['clips'].items():
    clip = D['clips'][role]
    tracks = {t['bone']: np.array(t['values']).reshape(-1, 10) for t in spec['tracks']}
    rows = [{n: np.array(v, float) for n, v in r.items()} for r in clip['rows']]
    changed = sorted({f for n, v in tracks.items() for f in range(len(rows))
                      if np.max(np.abs((v[f] if len(v) > 1 else v[0]) - rows[f][n])) > 1e-6})
    new_rows = [dict(r) for r in rows]
    for n, v in tracks.items():
        for f in range(len(rows)):
            new_rows[f][n] = v[f] if len(v) > 1 else v[0]
    fam = {}
    for family in FAMILIES:
        layer = P['profiles'][family]['clips'][clip['path']]
        src = D['profiles'][family]['clips'][clip['path']]
        kept_same = all(t in src['tracks'] for t in layer['tracks'] if t['bone'] not in P['write_bones'])
        rebuilt = [{n: v.copy() for n, v in r.items()} for r in new_rows]
        for t in layer['tracks']:
            for r, d in zip(rebuilt, overlay_samples(t, clip['times'])):
                n = t['bone']
                r[n][:3] += d[:3]; r[n][3:7] = (R.from_quat(d[3:7]) * R.from_quat(r[n][3:7])).as_quat(); r[n][7:] += d[7:]
        old = posed_local(role, family)
        drift = []
        for f in (60, 100, 112, 125, 150 if len(old) > 150 else len(old) - 1):
            a, b = world(old[f]), world(rebuilt[f])
            drift.append(float(np.linalg.norm(a['hand_l'][:3, 3] - b['hand_l'][:3, 3]) * 10))
        fam[family] = dict(non_left_tracks_unchanged=kept_same, hand_mm_vs_installed_at=[round(x, 3) for x in drift],
                           metrics=A['clips'][role]['families'][family])
    report[role] = dict(frames=spec['frames'], installed_frames=clip['frames'], changed_frames=[changed[0], changed[-1]] if changed else [],
                        changed_count=len(changed), families=fam)
    print(role, 'frames', spec['frames'], '==', clip['frames'], 'changed', report[role]['changed_frames'], len(changed))
    for family, item in fam.items():
        m = item['metrics']
        print('   %-8s kept=%s hand_mm@[60,100,112,125,end]=%s snap=%.1f roll=[%.1f,%.1f] clear_drop=%.2fmm len_err=%.1e wrist<=%.1fmm' % (
            family, item['non_left_tracks_unchanged'], item['hand_mm_vs_installed_at'], m['snap_deg'], *m['roll_deg'],
            m['clearance_drop_mm'], m['length_err_mm'], m['wrist_shift_mm']))
(O / 'patch_check.json').write_text(json.dumps(report, indent=1))
