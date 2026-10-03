"""Why does the PKM forearm shade with dirty streaks?

Checks the authored surface for the defects that actually produce streaky shading:
degenerate (zero-length) normals - the engine logged exactly that warning during the
Sprint46 bake - sliver triangles, duplicated/overlapping geometry, and hard normals
that break smoothing across the arm.

Every metric is computed for the PKM profile AND for the shared surface master
M4_original.json, so "is this the original hand model's problem" is answered by
comparison rather than opinion.
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
    N = np.array(d['normals'], dtype=np.float64)          # (ntri, 3 corners, 3)
    M = np.array(d['triangle_materials'], dtype=np.int64)
    nv, nt = len(P), len(T)

    # skin region: vertices mostly on the forearm/upper arm
    w = d['weights']
    fore = np.array([sum(e.get(b, 0.0) for b in FOREARM_BONES) for e in w])
    vert_fore = fore > 0.5
    tri_fore = vert_fore[T].all(axis=1)

    print('\n=== %s ===' % tag)
    print('  verts %d  tris %d  material sections %d  forearm verts %d (%.1f%%)  '
          'forearm tris %d' % (nv, nt, len(np.unique(M)), vert_fore.sum(),
                               100.0 * vert_fore.mean(), tri_fore.sum()))

    # 1. degenerate normals
    nl = np.linalg.norm(N, axis=2)
    zero = nl < 1e-3
    nan = ~np.isfinite(N).all(axis=2)
    bad_tri = (zero | nan).any(axis=1)
    print('  zero-length normals: %d corners (%.4f%%) in %d tris ; non-finite: %d'
          % (zero.sum(), 100.0 * zero.mean(), bad_tri.sum(), nan.sum()))
    print('     of which on the forearm: %d corners in %d tris'
          % ((zero & tri_fore[:, None]).sum(), (bad_tri & tri_fore).sum()))

    # 2. sliver triangles: area vs longest edge
    A, B, C = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    e = np.stack([np.linalg.norm(B - A, axis=1), np.linalg.norm(C - B, axis=1),
                  np.linalg.norm(A - C, axis=1)], axis=1)
    longest, shortest = e.max(axis=1), e.min(axis=1)
    area = 0.5 * np.linalg.norm(np.cross(B - A, C - A), axis=1)
    qual = 4.0 * np.sqrt(3.0) * area / np.maximum(longest ** 2, 1e-12)  # 1 = equilateral
    sliver = qual < 0.05
    degenerate = area < 1e-9
    print('  triangle quality: median %.3f  p1 %.3f  below 0.05: %d (%.2f%%)  '
          'zero-area: %d'
          % (np.median(qual), np.percentile(qual, 1), sliver.sum(),
             100.0 * sliver.mean(), degenerate.sum()))
    if tri_fore.any():
        print('     forearm: median %.3f  below 0.05: %d (%.2f%%)  zero-area: %d'
              % (np.median(qual[tri_fore]), (sliver & tri_fore).sum(),
                 100.0 * sliver[tri_fore].mean(), (degenerate & tri_fore).sum()))
    print('     longest edge: median %.4f m  p99 %.4f m  max %.4f m'
          % (np.median(longest), np.percentile(longest, 99), longest.max()))

    # 3. duplicated / overlapping geometry
    key = np.round(P, 5)
    _, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    dup_v = int((cnt[inv] > 1).sum())
    print('  duplicate positions (1e-5): %d verts in %d groups  (a second shell shows here)'
          % (dup_v, int((cnt > 1).sum())))
    if dup_v:
        worst = np.argsort(-cnt)[:3]
        for wi in worst:
            if cnt[wi] > 1:
                p = np.unique(key, axis=0)[wi]
                print('     %d copies at %s' % (cnt[wi], np.round(p, 3).tolist()))

    # 4. smoothing: spread of corner normals around each shared vertex
    acc = {}
    for t in range(nt):
        for c in range(3):
            acc.setdefault(T[t, c], []).append(N[t, c])
    spread = np.zeros(nv)
    for vi, lst in acc.items():
        if len(lst) < 2:
            continue
        a = np.array(lst)
        a = a / np.maximum(np.linalg.norm(a, axis=1, keepdims=True), 1e-12)
        cos = np.clip(a @ a.T, -1, 1)
        spread[vi] = np.degrees(np.arccos(cos.min()))
    hard = spread > 30.0
    print('  normals per vertex: mean corners %.2f ; hard (spread>30deg) %d verts (%.2f%%)'
          % (np.mean([len(v) for v in acc.values()]), hard.sum(),
             100.0 * hard.mean()))
    print('     forearm hard verts: %d (%.2f%%)' % ((hard & vert_fore).sum(),
                                                    100.0 * hard[vert_fore].mean()))
    print('     split verts (same position, different corners) imply seams; '
          'verts %d vs unique positions %d' % (nv, len(np.unique(key, axis=0))))
    return {'verts': nv, 'tris': nt, 'zero_normals': int(zero.sum()),
            'bad_norm_tris': int(bad_tri.sum()), 'slivers': int(sliver.sum()),
            'zero_area': int(degenerate.sum()), 'dup_verts': dup_v,
            'hard_verts': int(hard.sum()), 'median_quality': float(np.median(qual)),
            'forearm_verts': int(vert_fore.sum()),
            'forearm_slivers': int((sliver & tri_fore).sum()),
            'forearm_hard': int((hard & vert_fore).sum())}


R = {}
R['PKM'] = analyse('PKM (Authored/PKM.json)', OUTFIT / 'Authored' / 'PKM.json')
R['MASTER'] = analyse('M4_original.json (shared surface master)',
                      OUTFIT / 'M4_original.json')
R['AKM'] = analyse('AKM (another profile, for reference)',
                   OUTFIT / 'Authored' / 'AKM.json')

print('\n=== comparison: is the defect inherited from the master? ===')
keys = ('zero_normals', 'bad_norm_tris', 'slivers', 'zero_area', 'dup_verts',
        'hard_verts', 'forearm_slivers', 'forearm_hard')
print('  %-18s %10s %10s %10s' % ('metric', 'PKM', 'MASTER', 'AKM'))
for k in keys:
    print('  %-18s %10d %10d %10d' % (k, R['PKM'][k], R['MASTER'][k], R['AKM'][k]))

out = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922\Sprint47')
out.mkdir(parents=True, exist_ok=True)
(out / 'surface_diagnosis.json').write_text(json.dumps(R, indent=2), encoding='utf-8')
print('\nSURFACE_DIAGNOSIS_DONE')