"""UV stretch on the bare forearm - the remaining geometry-side cause of dirty streaks.

If the forearm's UV islands are stretched anisotropically, the skin's normal and
roughness detail smears into streaks that run along the arm, which is what the
screenshot shows.  This measures the UV->3D Jacobian per triangle: its singular values
are the texel density along the two principal directions, and their ratio is the
anisotropy (1 = no stretch, high = smeared).

Compared across PKM, the shared master and AKM so the answer is attributable.
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
    UV = np.array(d['uv'], dtype=np.float64)
    w = d['weights']
    fore = np.array([sum(e.get(b, 0.0) for b in FOREARM_BONES) for e in w]) > 0.5
    tf = fore[T].all(axis=1)

    p0, p1, p2 = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    t0, t1, t2 = UV[:, 0], UV[:, 1], UV[:, 2]
    e1, e2 = p1 - p0, p2 - p0
    f1, f2 = t1 - t0, t2 - t0
    det = f1[:, 0] * f2[:, 1] - f2[:, 0] * f1[:, 1]
    ok = np.abs(det) > 1e-12
    # J = [e1 e2] . inv([f1 f2])  -> 3x2, cm of surface per unit UV
    inv = np.zeros((len(T), 2, 2))
    inv[:, 0, 0] = f2[:, 1]
    inv[:, 0, 1] = -f2[:, 0]
    inv[:, 1, 0] = -f1[:, 1]
    inv[:, 1, 1] = f1[:, 0]
    inv /= np.where(ok, det, 1.0)[:, None, None]
    E = np.stack([e1, e2], axis=2)                 # (ntri, 3, 2)
    J = np.einsum('nij,njk->nik', E, inv)          # (ntri, 3, 2)
    G = np.einsum('nik,nil->nkl', J, J)            # metric tensor 2x2
    tr = G[:, 0, 0] + G[:, 1, 1]
    dt = G[:, 0, 0] * G[:, 1, 1] - G[:, 0, 1] * G[:, 1, 0]
    disc = np.sqrt(np.maximum(tr * tr - 4.0 * dt, 0.0))
    s1 = np.sqrt(np.maximum((tr + disc) / 2.0, 0.0))   # cm per UV unit
    s2 = np.sqrt(np.maximum((tr - disc) / 2.0, 0.0))
    aniso = s1 / np.maximum(s2, 1e-9)
    aniso[~ok] = np.nan
    density = s1 * s2                                   # area scale, cm^2 per UV^2

    def rep(mask, label):
        a = aniso[mask & ok]
        dn = density[mask & ok]
        if not len(a):
            print('   %-10s (none)' % label)
            return None
        print('   %-10s tris %6d | anisotropy median %.2f  p90 %.2f  p99 %.2f  max %6.1f'
              ' | texel density median %.4f cm/uv' %
              (label, len(a), np.median(a), np.percentile(a, 90),
               np.percentile(a, 99), a.max(), np.median(dn)))
        for thr in (2, 4, 8, 16):
            print('        aniso > %-4d : %6d tris (%5.2f%%)'
                  % (thr, (a > thr).sum(), 100.0 * (a > thr).mean()))
        return {'median': float(np.median(a)), 'p99': float(np.percentile(a, 99)),
                'max': float(a.max()), 'over4': int((a > 4).sum()),
                'over8': int((a > 8).sum()), 'tris': int(len(a))}

    print('\n=== %s ===' % tag)
    whole = rep(np.ones(len(T), bool), 'whole')
    fm = rep(tf, 'forearm')
    nf = rep(~tf, 'hand/rest')
    return {'whole': whole, 'forearm': fm, 'rest': nf}


R = {}
R['PKM'] = analyse('PKM (Authored/PKM.json)', OUTFIT / 'Authored' / 'PKM.json')
R['MASTER'] = analyse('M4_original.json (shared surface master)', OUTFIT / 'M4_original.json')
R['AKM'] = analyse('AKM (reference profile)', OUTFIT / 'Authored' / 'AKM.json')

print('\n=== comparison ===')
print('  %-8s %-10s %8s %8s %8s %8s %8s' %
      ('profile', 'region', 'median', 'p99', 'max', '>4x', '>8x'))
for p in ('PKM', 'MASTER', 'AKM'):
    for region in ('whole', 'forearm', 'rest'):
        v = R[p][region]
        if v:
            print('  %-8s %-10s %8.2f %8.2f %8.1f %8d %8d'
                  % (p, region, v['median'], v['p99'], v['max'], v['over4'], v['over8']))

out = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922\Sprint47')
out.mkdir(parents=True, exist_ok=True)
(out / 'uv_stretch.json').write_text(json.dumps(R, indent=2), encoding='utf-8')
print('\nUV_STRETCH_DONE')