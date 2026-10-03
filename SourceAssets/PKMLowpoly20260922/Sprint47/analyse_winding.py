"""Triangle winding vs the authored shading normals.

A triangle whose vertex order winds opposite to its shading normal renders as a dark
sliver - exactly the "dirty streak" look, and the project already carries a
repair_native_skin_winding.py tool, so this has bitten before.  Checks winding per
triangle, and also whether winding is CONSISTENT between neighbouring triangles (an
isolated flipped triangle is far more visible than a whole patch).

Compared across PKM / shared master / AKM for attribution.
"""
import json
from pathlib import Path

import numpy as np

OUTFIT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ModularOutfit20260925\BarePalmV7')
FOREARM_BONES = ('lowerarm_l', 'lowerarm_r', 'lowerarm_twist_01_l', 'lowerarm_twist_01_r',
                 'lowerarm_twist_02_l', 'lowerarm_twist_02_r', 'upperarm_l', 'upperarm_r',
                 'upperarm_twist_01_l', 'upperarm_twist_01_r', 'upperarm_twist_02_l',
                 'upperarm_twist_02_r')


def analyse(tag, path):
    d = json.loads(path.read_text(encoding='utf-8'))
    P = np.array(d['positions'], dtype=np.float64)
    T = np.array(d['triangles'], dtype=np.int64)
    N = np.array(d['normals'], dtype=np.float64)
    fore = np.array([sum(e.get(b, 0.0) for b in FOREARM_BONES) for e in d['weights']]) > 0.5
    tf = fore[T].all(axis=1)

    A, B, C = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    geo = np.cross(B - A, C - A)
    gn = np.linalg.norm(geo, axis=1)
    geo = geo / np.maximum(gn, 1e-12)[:, None]
    shade = N.mean(axis=1)
    shade = shade / np.maximum(np.linalg.norm(shade, axis=1), 1e-12)[:, None]
    dot = (geo * shade).sum(axis=1)

    flip = dot < 0.0
    print('\n=== %s ===' % tag)
    print('  triangles %d' % len(T))
    print('  winding opposite to shading normal: %d (%.3f%%)  |  of which forearm: %d'
          % (flip.sum(), 100.0 * flip.mean(), (flip & tf).sum()))
    print('  dot: median %+.3f  p1 %+.3f  min %+.3f  |  below 0.5: %d  below 0: %d'
          % (np.median(dot), np.percentile(dot, 1), dot.min(),
             (dot < 0.5).sum(), flip.sum()))
    for thr in (-0.5, -0.9, -0.99):
        print('     dot < %+.2f : %5d tris (%5.3f%%)'
              % (thr, (dot < thr).sum(), 100.0 * (dot < thr).mean()))

    # neighbour consistency: for each shared edge, do the two triangles wind the same way
    # relative to the edge?  Consistent orientation => opposite directed edges.
    edges = {}
    for t in range(len(T)):
        a, b, c = T[t]
        for u, v in ((a, b), (b, c), (c, a)):
            edges.setdefault((min(u, v), max(u, v)), []).append((u, v, t))
    same, opp, pairs = 0, 0, 0
    for k, lst in edges.items():
        if len(lst) != 2:
            continue
        pairs += 1
        (u1, v1, _), (u2, v2, _) = lst
        if (u1, v1) == (v2, u2):
            opp += 1
        else:
            same += 1
    print('  shared edges %d : consistent %d (%.3f%%)  INCONSISTENT %d (%.3f%%)'
          % (pairs, opp, 100.0 * opp / max(pairs, 1), same, 100.0 * same / max(pairs, 1)))
    return {'tris': int(len(T)), 'flipped': int(flip.sum()),
            'flipped_forearm': int((flip & tf).sum()),
            'min_dot': float(dot.min()), 'below_half': int((dot < 0.5).sum()),
            'edges': pairs, 'inconsistent_edges': same}


R = {}
R['PKM'] = analyse('PKM', OUTFIT / 'Authored' / 'PKM.json')
R['MASTER'] = analyse('M4_original.json (master)', OUTFIT / 'M4_original.json')
R['AKM'] = analyse('AKM', OUTFIT / 'Authored' / 'AKM.json')
print('\n=== comparison ===')
print('  %-8s %8s %10s %10s %10s %10s' %
      ('profile', 'tris', 'flipped', 'flip_fore', 'min_dot', 'incons_edges'))
for p in ('PKM', 'MASTER', 'AKM'):
    v = R[p]
    print('  %-8s %8d %10d %10d %10.3f %10d'
          % (p, v['tris'], v['flipped'], v['flipped_forearm'], v['min_dot'],
             v['inconsistent_edges']))

out = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922\Sprint47')
out.mkdir(parents=True, exist_ok=True)
(out / 'winding.json').write_text(json.dumps(R, indent=2), encoding='utf-8')
print('\nWINDING_DONE')