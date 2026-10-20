"""Author inputs only: hand/pusher travel, stops and joint timing of the installed clips."""
import json, sys
import numpy as np
from scipy.spatial.transform import Rotation as R
from r26_core import *

roles = sys.argv[1:] or ['normal_7', 'empty_7']
report = {}
for role in roles:
    W = [world(row) for row in posed_local(role)]
    n = len(W)
    gun = [np.linalg.inv(w[GUN]) for w in W]
    hand = np.array([(g @ w['hand_l'])[:3, 3] for g, w in zip(gun, W)])
    post = np.array([(g @ w[POST])[:3, 3] for g, w in zip(gun, W)])
    inpost = [np.linalg.inv(w[POST]) @ w['hand_l'] for w in W]
    axis = post[110] - post[86]
    stroke = (post - post[86]) @ axis / (axis @ axis)
    hv = np.linalg.norm(np.gradient(hand, axis=0), axis=1) * FPS
    hq = [R.from_matrix((g @ w['hand_l'])[:3, :3]) for g, w in zip(gun, W)]
    hw = np.r_[0, [np.degrees((hq[i] * hq[i - 1].inv()).magnitude()) * FPS for i in range(1, n)]]
    fq = [R.from_matrix(w['lowerarm_l'][:3, :3]) for w in W]
    wrist = [np.degrees((R.from_matrix(w['hand_l'][:3, :3]) * f.inv()).magnitude()) for w, f in zip(W, fq)]
    weld = [float(np.linalg.norm((inpost[i] @ np.linalg.inv(inpost[100]))[:3, 3]) * 1000) for i in range(n)]
    weld_deg = [float(np.degrees(R.from_matrix((inpost[i] @ np.linalg.inv(inpost[100]))[:3, :3]).magnitude())) for i in range(n)]
    rows = []
    for f in range(70, min(n, 160)):
        rows.append(dict(f=f, stroke=round(float(stroke[f]), 4), hand_mps=round(float(hv[f]), 3),
                         hand_dps=round(float(hw[f]), 1), wrist_deg=round(wrist[f], 1),
                         hand_post_mm=round(weld[f], 2), hand_post_deg=round(weld_deg[f], 2)))
    report[role] = dict(frames=n - 1, stroke_axis_m=axis.tolist(), stroke_len_m=float(np.linalg.norm(axis)), rows=rows)
    print('==', role, 'frames', n - 1, 'stroke', round(float(np.linalg.norm(axis)), 4))
    for r in rows:
        print(' {f:4d} s={stroke:7.4f} v={hand_mps:6.3f}m/s w={hand_dps:7.1f}d/s wrist={wrist_deg:6.1f} weld={hand_post_mm:6.2f}mm/{hand_post_deg:5.2f}d'.format(**r))
(O / 'measure.json').write_text(json.dumps(report, indent=1))
