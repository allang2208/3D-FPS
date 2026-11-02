"""Measure V82's open-palm spin as V85 key channels (R6).

blender -b --factory-startup --python fit_v82_keys.py -- <phi,phi,...> [--roll=1.0]
For each V85 sword phase: pick the V82 frame whose sword orientation is closest to V85's sword at that phase, carry
V82's hand-relative-to-sword rotation onto V85's sword, and fit V85's hand_turn / supinate / extend to it; read the
finger curls (fraction of the idle fist per joint, spread, thumb oppose) and the hilt placement on the palm.
Writes Work/fit_v82_keys.json.
"""
import json
import math
import sys
from pathlib import Path

import bpy  # noqa: F401  (Blender context for v85_setup)
import numpy as np
from mathutils import Matrix, Quaternion, Vector

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import v85_setup  # noqa: E402
import v85_hand as Hd  # noqa: E402
from v85_setup import WPN  # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:]
PHIS = [float(p) for p in argv[0].split(',')]
ROLL = float(next((a.split('=')[1] for a in argv if a.startswith('--roll=')), '1.0'))
c = v85_setup.load('Standard')
D = np.load(HERE / 'Work' / 'v82_poses_Standard.npz')
idx = {str(n): i for i, n in enumerate(D['names'])}
P = D['pose']
idle = c.idle
fore_local = idle['hand_r'].to_quaternion().inverted() @ (
    idle['hand_r'].translation - idle['lowerarm_r'].translation).normalized()


def mat(f, n):
    return Matrix(P[f, idx[n]].tolist())


def sword85(phi):
    q = Quaternion(c.spin_axis, math.radians(phi)) @ c.flatten_q @ idle[WPN].to_quaternion()
    return q @ Quaternion((0.0, 0.0, 1.0), math.radians(ROLL * c.roll_inplane_deg))


def hand85(ht, sup, ext):
    local = Quaternion(fore_local, math.radians(sup)) @ Quaternion((0.0, 0.0, 1.0), math.radians(ext))
    return Quaternion(c.spin_axis, math.radians(ht)) @ c.flatten_q @ idle['hand_r'].to_quaternion() @ local


def ang(a, b):
    d = math.degrees(a.rotation_difference(b).angle)
    return min(d, 360.0 - d)


def fit(fn, ranges, coarse, target):
    best = None
    grids = [np.arange(lo, hi + 1e-9, coarse) for lo, hi in ranges]
    for x in np.array(np.meshgrid(*grids, indexing='ij')).reshape(len(ranges), -1).T:
        e = ang(fn(*x), target)
        if best is None or e < best[0]:
            best = (e, list(x))
    step = coarse / 2.0
    while step > 0.05:
        moved = False
        for i in range(len(ranges)):
            for s in (-step, step):
                x = list(best[1])
                x[i] += s
                e = ang(fn(*x), target)
                if e < best[0] - 1e-6:
                    best, moved = (e, x), True
        if not moved:
            step /= 2.0
    return best


def finger_fields(f):
    out = {}
    for finger in Hd.FINGERS:
        vals = {}
        for joint in ('01', '02', '03'):
            n = '%s_%s_r' % (finger, joint)
            par = c.parent[n]
            local = c.local_rest[n].inverted() @ (mat(f, par).inverted() @ mat(f, n))
            q = local.to_quaternion()
            base = (Hd.IDLE_CURL_THUMB if finger == 'thumb' else Hd.IDLE_CURL)[joint]
            if joint == '01':
                if finger == 'thumb':
                    e, (sp, op) = fit(lambda s_, o_: Quaternion((0, 0, 1), math.radians(o_)) @ Quaternion((0, 1, 0), math.radians(s_)),
                                      [(-60, 60), (-60, 60)], 5.0, q)
                    vals.update({'01': 1.0, 'spread': round(sp, 1), 'oppose': round(op, 1), 'err01': round(e, 1)})
                else:
                    e, (cu, sp) = fit(lambda c_, s_: Quaternion((0, 1, 0), math.radians(s_)) @ Quaternion((0, 0, 1), math.radians(c_ * base)),
                                      [(-0.6, 1.4), (-30, 30)], 0.1, q)
                    vals.update({'01': round(cu, 3), 'spread': round(sp, 1), 'err01': round(e, 1)})
            else:
                vals[joint] = round(math.degrees(2.0 * math.atan2(q.z, q.w)) / base, 3)
        out[finger] = vals
    return out


rows = []
for phi in PHIS:
    s85 = sword85(phi)
    f = min(range(30, P.shape[0] - 30), key=lambda k: ang(mat(k, WPN).to_quaternion(), s85))
    s82, h82 = mat(f, WPN), mat(f, 'hand_r')
    rel = s82.to_quaternion().inverted() @ h82.to_quaternion()
    target = s85 @ rel
    e, (ht, sup, ext) = fit(hand85, [(-180, 180), (-180, 180), (-60, 60)], 15.0, target)
    # Hilt on the palm in V85's terms (as v85_solve reports it): side along the back of the hand, station of the
    # palm centre along the hilt axis (WPN local z).
    palm = 0.5 * (mat(f, 'middle_01_r').translation + h82.translation)
    back = h82.to_quaternion() @ Vector((0.0, 1.0, 0.0))
    lz = (s82.inverted() @ palm).z
    foot = s82 @ Vector((0.0, 0.0, lz))
    hp = h82.translation
    rows.append({'phi': phi, 'v82_frame': f, 'v82_t': round(f / 120.0, 4),
                 'sword_match_deg': round(ang(s82.to_quaternion(), s85), 1),
                 'hand_turn': round(ht, 1), 'supinate': round(sup, 1), 'extend': round(ext, 1), 'fit_err_deg': round(e, 2),
                 'hilt_side_m': round((foot - palm).dot(back), 4), 'palm_station_z_m': round(lz, 4),
                 'dorsum_to_camera': round(back.dot(-hp.normalized()), 3),
                 'fingers': finger_fields(f)})
    print('FIT', json.dumps(rows[-1]))
(HERE / 'Work' / 'fit_v82_keys.json').write_text(json.dumps(rows, indent=1), encoding='utf-8')
contacts = {k: round(v['z'], 4) for k, v in c.contacts.items() if 'z' in v}
print('V85_CONTACT_Z', contacts)
