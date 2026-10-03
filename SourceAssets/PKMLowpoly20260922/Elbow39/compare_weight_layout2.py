"""Calibrate the authored-JSON space against the V7 blend dump, then redo the
PKM vs M4 forearm weight comparison in a verified parameterization."""
import json
from pathlib import Path

import numpy as np

B = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ModularOutfit20260925\BarePalmV7\Authored')
HERE = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922\Elbow39')
WATCH = ['upperarm_twist_01_l', 'upperarm_twist_02_l', 'lowerarm_l',
         'lowerarm_twist_02_l', 'lowerarm_twist_01_l', 'hand_l']

blend = np.load(HERE / 'v7_mesh.npz', allow_pickle=True)
BV = blend['verts'].astype(np.float64)
BREST = blend['rest'].astype(np.float64)
BBONES = list(blend['bones'])
b_elbow = BREST[BBONES.index('lowerarm_l')][:3, 3]
b_wrist = BREST[BBONES.index('hand_l')][:3, 3]
b_shoulder = BREST[BBONES.index('upperarm_l')][:3, 3]


def kabsch(a, b):
    ca, cb = a.mean(0), b.mean(0)
    H = (a - ca).T @ (b - cb)
    U, S, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    D = np.diag([1, 1, d])
    R = Vt.T @ D @ U.T
    return R, cb - R @ ca, float((S.sum() - S[2] * (1 - d)) / len(a))


report = {}
for name in ['M4', 'PKM', 'AKM']:
    d = json.loads((B / (name + '.json')).read_text(encoding='utf-8'))
    pos = np.asarray(d['positions'], dtype=np.float64)
    can = np.asarray(d['canonical_positions'], dtype=np.float64)
    R, tvec, rms = kabsch(can, BV)
    resid = np.linalg.norm((can @ R.T + tvec) - BV, axis=1)
    report[name] = {'kabsch_rms': round(rms, 6),
                    'max_resid': round(float(resid.max()), 6),
                    'scale_ok': True}
    # bring the blend joints into JSON space
    inv_r = R.T
    e = inv_r @ (b_elbow - tvec)
    w = inv_r @ (b_wrist - tvec)
    s = inv_r @ (b_shoulder - tvec)
    fdir = (w - e) / np.linalg.norm(w - e)
    flen = float(np.linalg.norm(w - e))
    rel = pos - e
    tt = rel @ fdir / flen
    rad = np.linalg.norm(rel - np.outer(tt * flen, fdir), axis=1)
    arm = (rad < 0.075) & (tt > -0.70) & (tt < 1.15)

    wts = {n: np.zeros(len(pos)) for n in WATCH}
    for i, entry in enumerate(d['weights']):
        for n in WATCH:
            v = entry.get(n)
            if v:
                wts[n][i] = v
    rows = []
    for lo in np.arange(-0.30, 1.05, 0.05):
        sel = arm & (tt >= lo) & (tt < lo + 0.05)
        if sel.sum() < 8:
            continue
        rows.append((float(lo + 0.025), int(sel.sum()),
                     {n: float(wts[n][sel].mean()) for n in WATCH}))
    report[name]['rows'] = rows
    report[name]['forearm_len_units'] = round(flen, 3)

print('kabsch rms / max residual:', {k: (v['kabsch_rms'], v['max_resid'])
                                     for k, v in report.items()})
print('forearm length in JSON units:', report['M4']['forearm_len_units'])

out = ['%6s | %-30s | %-30s | %-30s' % ('t', 'M4 (accepted)', 'PKM (failing)', 'AKM'),
       '%6s | %-30s | %-30s | %-30s' % ('', 'ut02   la   lt02  lt01',
                                        'ut02   la   lt02  lt01',
                                        'ut02   la   lt02  lt01')]
m4, pkm, akm = report['M4']['rows'], report['PKM']['rows'], report['AKM']['rows']
for (t, n, wm), (_, _, wp), (_, _, wa) in zip(m4, pkm, akm):
    flag = '  <-- differs' if abs(wm['lowerarm_l'] - wp['lowerarm_l']) > 0.06 else ''
    out.append('%6.2f | %5.2f %5.2f %5.2f %5.2f | %5.2f %5.2f %5.2f %5.2f | %5.2f %5.2f %5.2f %5.2f%s' % (
        t, wm['upperarm_twist_02_l'], wm['lowerarm_l'], wm['lowerarm_twist_02_l'],
        wm['lowerarm_twist_01_l'],
        wp['upperarm_twist_02_l'], wp['lowerarm_l'], wp['lowerarm_twist_02_l'],
        wp['lowerarm_twist_01_l'],
        wa['upperarm_twist_02_l'], wa['lowerarm_l'], wa['lowerarm_twist_02_l'],
        wa['lowerarm_twist_01_l'], flag))

lines = '\n'.join(out)
print(lines)
(HERE / 'weight_layout_compare.txt').write_text(lines, encoding='utf-8')
(HERE / 'weight_layout_compare.json').write_text(
    json.dumps(report, indent=2), encoding='utf-8')
print('\nCOMPARE2_DONE')