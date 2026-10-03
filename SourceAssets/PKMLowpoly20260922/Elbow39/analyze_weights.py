"""Check the armature-space transform between the authoring rig and the V7
native rig, and report the real skinning stations along the left forearm."""
import json
from pathlib import Path

import numpy as np

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922\Elbow39')

v7 = np.load(ROOT / 'v7_mesh.npz', allow_pickle=True)
au = np.load(ROOT / 'author_rig.npz', allow_pickle=True)
v7b = list(v7['bones'])
aub = list(au['bones'])
rest_v7 = v7['rest']
rest_au = au['rest']

CHAIN = ['clavicle_l', 'upperarm_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l',
         'lowerarm_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l', 'hand_l']

out = {}

# --- similarity between armature spaces, using each chain bone ------------
ref = None
T_all = {}
for n in CHAIN:
    i, j = v7b.index(n), aub.index(n)
    T = rest_au[j] @ np.linalg.inv(rest_v7[i])
    T_all[n] = T
    if ref is None:
        ref = T
    out.setdefault('T_vs_upperarm_l', {})[n] = float(np.abs(T - ref).max())

# decompose the reference transform: rotation + uniform scale + translation
R = ref[:3, :3]
scale = float(np.cbrt(abs(np.linalg.det(R))))
rot = R / scale
out['space_transform'] = {
    'scale': scale,
    'orthonormal_error': float(np.abs(rot @ rot.T - np.eye(3)).max()),
    'translation': [float(x) for x in ref[:3, 3]],
}

# --- skinning stations along the left forearm ----------------------------
bones = v7b
verts = v7['verts']
w_idx = v7['w_idx']
w_val = v7['w_val']

# use the native rest pose: elbow -> wrist axis
elbow = rest_v7[bones.index('lowerarm_l')][:3, 3]
wrist = rest_v7[bones.index('hand_l')][:3, 3]
axis = wrist - elbow
length = float(np.linalg.norm(axis))
axis = axis / length

rel = verts - elbow
t = rel @ axis / length                     # 0 at elbow, 1 at wrist
radial = rel - np.outer(t * length, axis)
radius = np.linalg.norm(radial, axis=1)

WATCH = ['upperarm_l', 'upperarm_twist_02_l', 'upperarm_twist_01_l',
         'lowerarm_l', 'lowerarm_twist_02_l', 'lowerarm_twist_01_l', 'hand_l']
wi = {n: bones.index(n) for n in WATCH}
wmap = np.zeros((len(verts), len(WATCH)), dtype=np.float64)
for k, n in enumerate(WATCH):
    wmap[:, k] = np.where(w_idx == wi[n], w_val, 0.0).sum(axis=1)
total = wmap.sum(axis=1)

band = (t > -0.35) & (t < 1.35)
out['forearm_length_m'] = length
out['band_verts'] = int(band.sum())

rows = []
for lo in np.arange(-0.30, 1.30, 0.05):
    sel = band & (t >= lo) & (t < lo + 0.05)
    if sel.sum() == 0:
        continue
    mean = wmap[sel].mean(axis=0)
    rows.append({
        't': round(float(lo + 0.025), 3),
        'n': int(sel.sum()),
        'radius_mm': round(float(radius[sel].mean() * 1000), 2),
        'radius_min_mm': round(float(radius[sel].min() * 1000), 2),
        'radius_max_mm': round(float(radius[sel].max() * 1000), 2),
        'w': {n: round(float(m), 3) for n, m in zip(WATCH, mean)},
        'weight_sum': round(float(total[sel].mean()), 3),
    })
out['stations'] = rows

# dominant-bone centroid along the forearm: where each helper actually lives
out['dominant_station'] = {}
for n in WATCH:
    k = WATCH.index(n)
    sel = band & (wmap[:, k] > 0.5)
    if sel.sum() == 0:
        out['dominant_station'][n] = None
        continue
    out['dominant_station'][n] = {
        't_mean': round(float(t[sel].mean()), 4),
        't_min': round(float(t[sel].min()), 4),
        't_max': round(float(t[sel].max()), 4),
        'n': int(sel.sum()),
    }

(ROOT / 'weight_report.json').write_text(
    json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')

print('SPACE scale=%.6f ortho_err=%.2e  T_spread=%.2e' % (
    out['space_transform']['scale'],
    out['space_transform']['orthonormal_error'],
    max(out['T_vs_upperarm_l'].values())))
print('forearm_length_m=%.4f band_verts=%d' % (length, out['band_verts']))
print('t      n   r(mm)  ' + '  '.join('%-6s' % n[:6] for n in WATCH))
for r in rows:
    print('%6.3f %4d %6.2f  ' % (r['t'], r['n'], r['radius_mm'])
          + '  '.join('%6.3f' % r['w'][n] for n in WATCH))
print('dominant stations:')
for n, v in out['dominant_station'].items():
    print('  %-22s %s' % (n, v))