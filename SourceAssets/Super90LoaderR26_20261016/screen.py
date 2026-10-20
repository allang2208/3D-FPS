"""Author input: how far R26 moves the left hand on screen versus the installed R25 pose.

Uses the Super90LoaderArmRoot first-person framing (same camera estimate as that revision).
Screen units: fraction of the half-width / half-height (1.0 = frame edge)."""
import json, math, sys
import numpy as np
from scipy.spatial.transform import Rotation as R
from r26_core import *

role = sys.argv[1] if len(sys.argv) > 1 else 'normal_7'
family = sys.argv[2] if len(sys.argv) > 2 else 'base'
F = json.loads((O.parent / 'Super90LoaderArmRoot20261012/framing.json').read_text())


def axes(d, up):
    r = matrix(d['WPN_root']); x = np.array(d['WPN_FrontSight'][:3]) - d['WPN_RearSight'][:3]; x /= np.linalg.norm(x)
    z = r[:3, :3] @ up; y = np.cross(z, x); y /= np.linalg.norm(y); z = np.cross(x, y)
    return np.column_stack([x, y, z])


base = R.from_euler('z', 90, degrees=True).as_matrix()
CAM = np.eye(4)
CAM[:3, :3] = base @ axes(F['M4'], [0, 0, 1]) @ axes(F['Super90'], [0, -1, 0]).T
CAM[:3, 3] = np.array([6, 7, -7]) + base @ F['M4']['hand_r'][:3] - CAM[:3, :3] @ F['Super90']['hand_r'][:3]
TH = math.tan(math.radians(56)); TV = TH / (1276 / 837)
P = json.loads((O / 'animation_patch.json').read_text())


def patched(role, family):
    rows = posed_local(role, 'base')
    spec = P['clips'][role]
    for t in spec['tracks']:
        v = np.array(t['values']).reshape(-1, 10)
        for f, r in enumerate(rows):
            r[t['bone']] = (v[f] if len(v) > 1 else v[0]).copy()
    if family != 'base':
        clip = D['clips'][role]
        for t in P['profiles'][family]['clips'][clip['path']]['tracks']:
            n = t['bone']
            for r, d in zip(rows, overlay_samples(t, clip['times'])):
                r[n][:3] += d[:3]; r[n][3:7] = (R.from_quat(d[3:7]) * R.from_quat(r[n][3:7])).as_quat(); r[n][7:] += d[7:]
    return rows


def screen(w, p):
    c = (CAM @ np.r_[p, 1.])[:3]
    return np.array([c[1] / (c[0] * TH), c[2] / (c[0] * TV)])


def points(w):
    a, b = w['middle_02_l'][:3, 3], w['middle_03_l'][:3, 3]
    return dict(wrist=w['hand_l'][:3, 3], knuckle=w['index_01_l'][:3, 3], tip=b + (b - a) * .8)


old = [world(r) for r in posed_local(role, family)]
new = [world(r) for r in patched(role, family)]
peak = {}
lo, hi = 84, min(len(old) - 1, 146)
print('frame  wrist(old->new)            tip(old->new)              |d tip|  screen speed old/new (half-width/s)')
for f in range(lo, hi):
    po, pn = points(old[f]), points(new[f])
    so = {k: screen(old[f], v) for k, v in po.items()}; sn = {k: screen(new[f], v) for k, v in pn.items()}
    for k in so:
        peak[k] = max(peak.get(k, 0.), float(np.linalg.norm(sn[k] - so[k])))
    vo = np.linalg.norm(screen(old[f + 1], points(old[f + 1])['tip']) - screen(old[f - 1], points(old[f - 1])['tip'])) * 30
    vn = np.linalg.norm(screen(new[f + 1], points(new[f + 1])['tip']) - screen(new[f - 1], points(new[f - 1])['tip'])) * 30
    print('%4d   (%5.2f,%5.2f)->(%5.2f,%5.2f)  (%5.2f,%5.2f)->(%5.2f,%5.2f)  %5.3f   %5.2f / %5.2f' % (
        f, *so['wrist'], *sn['wrist'], *so['tip'], *sn['tip'], np.linalg.norm(sn['tip'] - so['tip']), vo, vn))
print('max on-screen difference (half-width units):', {k: round(v, 3) for k, v in peak.items()})
