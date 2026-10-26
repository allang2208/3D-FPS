"""Preview of the knife hand's lowering arc (OffhandKukriComponent: LowerArcControl/End, LowerHandTurn), used by the
draw entry, the reload lower/raise and consumables. Writes Work/lower/*.npz + strike_keys.json-style tag list for
render_strike.py (run with `-- lower`).  Run:  python -I preview_lower.py
"""
import json, sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
import author_idle as A
import author_strike as S

OUT = P / 'Work' / 'lower'
OUT.mkdir(parents=True, exist_ok=True)
CONTROL = np.array([-6., -7., -10.])
END = np.array([-8., -6., -34.])
TURN = R.from_rotvec(np.array([0, 1., 0]) * np.radians(55.))

rest = S.REST
hold = np.array(rest['l']['hand_l'])
TV = np.tan(np.radians(37.5)); TH = TV * 16 / 9
keys = []
for s in (0.0, 0.25, 0.5, 0.75, 1.0):
    wrist = hold[:3, 3] + 2 * (1 - s) * s * CONTROL + s * s * END
    rot = (R.from_rotvec(TURN.as_rotvec() * s) * R.from_matrix(hold[:3, :3])).as_matrix()
    l, d = A.solve_arm(A.LR, A.FIST[0], A.LP, 'l', A.controls['left_shoulder'], wrist, A.controls['left_pole'], rot)
    pose = dict(rest['pose'])
    for n in pose:
        if A.chain(n, 'clavicle_l', A.LP) and n in l:
            pose[n] = l[n]
    built = dict(G=rest['G'], view=rest['view'], pose=pose, Kc=l['hand_l'] @ rest['kukri_in_hand'])
    tag = 't%03d' % round(s * 1000)
    X = S.write_npz(built, tag) if False else None
    # write into Work/lower
    S_OUT = S.OUT
    S.OUT = OUT
    X = S.write_npz(built, tag)
    S.OUT = S_OUT
    vis = ((X[:, 0] > 8) & (np.abs(X[:, 1]) < X[:, 0] * TH) & (np.abs(X[:, 2]) < X[:, 0] * TV)).sum()
    tip = (built['Kc'] @ np.array([6.18, 0, 26.29, 1.]))[:3]
    print('s=%.2f wrist %s reach %.2f | arm verts on screen %d | blade tip %s' % (s, np.round(wrist, 1), d['reach'], vis, np.round(tip, 1)))
    keys.append(dict(t=s))
(OUT / 'strike_keys.json').write_text(json.dumps(dict(keys=keys)), encoding='utf-8')
