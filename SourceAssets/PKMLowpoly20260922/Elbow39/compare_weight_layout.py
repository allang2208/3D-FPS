"""Is the PKM elbow weight layout an outlier?

Compares the left-forearm weight distribution of the failing PKM profile
against the accepted M4 master, on the shared canonical surface.
"""
import json
from pathlib import Path

import numpy as np

B = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ModularOutfit20260925\BarePalmV7\Authored')
WATCH = ['upperarm_twist_01_l', 'upperarm_twist_02_l', 'lowerarm_l',
         'lowerarm_twist_02_l', 'lowerarm_twist_01_l', 'hand_l']

# native reference joints, cm, same space as the authored positions
ELBOW = np.array([-35.007, -2.570, -41.683])
WRIST = np.array([-47.769, 15.036, -58.109])
SHOULDER = np.array([-19.010, -3.220, -18.992])
FLEN = float(np.linalg.norm(WRIST - ELBOW))
FDIR = (WRIST - ELBOW) / FLEN
UDIR = (ELBOW - SHOULDER) / np.linalg.norm(ELBOW - SHOULDER)

EDGES = np.arange(-0.30, 1.05, 0.05)


def profile(name):
    d = json.loads((B / (name + '.json')).read_text(encoding='utf-8'))
    pos = np.asarray(d['positions'], dtype=np.float64)
    rel = pos - ELBOW
    t = rel @ FDIR / FLEN
    rad = np.linalg.norm(rel - np.outer(t * FLEN, FDIR), axis=1)
    arm = (rad < 8.0) & (t > -0.35) & (t < 1.1)
    w = {n: np.zeros(len(pos)) for n in WATCH}
    for i, entry in enumerate(d['weights']):
        for n in WATCH:
            v = entry.get(n)
            if v:
                w[n][i] = v
    rows = []
    for lo in EDGES[:-1]:
        sel = arm & (t >= lo) & (t < lo + 0.05)
        if sel.sum() < 10:
            continue
        rows.append((round(float(lo + 0.025), 3), int(sel.sum()),
                     {n: round(float(w[n][sel].mean()), 3) for n in WATCH}))
    return rows


m4 = profile('M4')
pkm = profile('PKM')
akm = profile('AKM')

lines = ['%6s | %-28s | %-28s | %-28s' % ('t', 'M4 (accepted)', 'PKM (failing)', 'AKM')]
lines.append('%6s | %-28s | %-28s | %-28s' % ('', 'ut02   la   lt02  lt01',
                                              'ut02   la   lt02  lt01',
                                              'ut02   la   lt02  lt01'))
for (t, n, wm), (_, _, wp), (_, _, wa) in zip(m4, pkm, akm):
    lines.append('%6.2f | %5.2f %5.2f %5.2f %5.2f | %5.2f %5.2f %5.2f %5.2f | %5.2f %5.2f %5.2f %5.2f' % (
        t, wm['upperarm_twist_02_l'], wm['lowerarm_l'], wm['lowerarm_twist_02_l'],
        wm['lowerarm_twist_01_l'],
        wp['upperarm_twist_02_l'], wp['lowerarm_l'], wp['lowerarm_twist_02_l'],
        wp['lowerarm_twist_01_l'],
        wa['upperarm_twist_02_l'], wa['lowerarm_l'], wa['lowerarm_twist_02_l'],
        wa['lowerarm_twist_01_l']))

out = '\n'.join(lines)
print(out)
(Path(__file__).parent / 'weight_layout_compare.txt').write_text(out, encoding='utf-8')
print('\nCOMPARE_DONE')