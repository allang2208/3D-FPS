"""Author the kukri sprint-attack clip "SprintAttack" (two-handed overhead chop, 40/30 s).

V2 (2026-10-22, user: "the two-handed chop is not in the centre of the screen, it sits to the right"): the raise, the
overhead hold and the chop follow the two-handed sword's sprint chop (A_RuneSword_Overhead on the same shared arms
rig, dumped by dump_sword_overhead.py), retimed to the reference jump chop (BV1CeYUeSE7b 112.47-113.80 s, 近战动作（跳跃）
#11 跳劈): both hands stacked on the handle come straight down the centre line (right fist x ~0.07, left ~-0.12 NDC),
arms reaching ~55 cm forward at the strike.  The sword's left hand sits 10 cm down the handle from the right fist, which
on the kukri is the pommel end, so the sword's two-hand relation is kept as it is.  Both arms are re-solved with the
kukri rig (V9 twist split, bone lengths), elbows pinned to the sword's.  The tail -- arms below the frame, re-raise into
the stance -- keeps the V1 frame fit (sprint_keys.json, fit_sprint.py).

Time map (kukri author s -> sword clip s, monotone cubic): 0 -> 0 (sword stance, blended in from the kukri stance by
0.10), 0.10 -> 0.33 (hands meet at the top centre), 0.13 -> 0.45 (above the frame), 0.333 -> 1.20 (end of the hold),
0.40 -> 1.30 (strike at the bottom centre), 0.433 -> 1.36, then blended into the V1 tail by 0.52 (the arms drop out of
the frame).  The left hand comes up from its lowered rest onto the handle 0.02-0.10 and lets go 0.45-0.54 (below the
frame).

Run:  python author_kukri_sprint.py [--preview] [--compare]
Output: Clips/SprintAttack.json + its summary in clips.json; --compare renders the 30 Hz frames under the reference
frames (Work/sprint/cmp_sprint_*.jpg).
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.interpolate import PchipInterpolator

import author_kukri_clips as AC
from kmath import T, mesh_to_cam, qslerp
from kukri_rig import KukriRig, ndc, TIP, POMMEL

P = Path(__file__).resolve().parent
WORK = P / 'Work' / 'sprint'
FPS = 120
LENGTH = 40 / 30
REF_START = 3374                       # reference frame at t = 0
SWORD = WORK / 'sword_overhead_dump.json'
SWORD_CLIP = 'Overhead'
TIME_MAP = [(0.0, 0.0), (0.10, 0.33), (0.13, 0.45), (0.333, 1.20), (0.40, 1.30), (0.433, 1.36), (0.60, 1.52)]
ENTRY = (0.0, 0.10)                    # kukri stance -> sword pose (the forearm rolls ~125 deg here, spread to 0.1 s)
EXIT = (0.433, 0.52)                   # sword impact pose -> V1 tail: the arms drop out of the frame like the reference
LEFT_ON = (0.02, 0.10)                 # left hand from its lowered rest onto the handle
LEFT_OFF = (0.45, 0.54)                # and back down (below the frame)
# Overhead hold: the sword keeps the left elbow and both upper arms in the top of the frame, the reference view is empty
# 0.17-0.33 s.  Both arm chains are swung back about the clavicle heads (camera-right axis) while the hands are up.
HOLD_LIFT_DEG = 22.0
HOLD_LIFT = (0.10, 0.16, 0.31, 0.352)  # ease in, full, ease out (back to the sword pose as the chop starts)
CONTACT = (0.367, 0.467)


def smooth(a, b, x):
    u = min(max((x - a) / (b - a), 0.0), 1.0)
    return u * u * (3 - 2 * u)


def blend_t(a, b, w):
    return T(a.p + (b.p - a.p) * w, qslerp(a.q, b.q, w), a.s + (b.s - a.s) * w)


class SprintClip:
    def __init__(self):
        self.R = R = KukriRig()
        from fit_reference import Fitter       # the V1 tail keys use the fitter's arm parametrisation
        self.F = Fitter(R)
        d = json.loads(SWORD.read_text('utf-8'))
        assert d['names'] == R.rig.names, 'sword dump bone order differs from the kukri rig'
        self.sword = d['clips'][SWORD_CLIP]
        self.rate = self.sword['rate']
        self.warp = PchipInterpolator([a for a, _ in TIME_MAP], [b for _, b in TIME_MAP])
        data = json.loads((P / 'sprint_keys.json').read_text('utf-8'))
        self.keys = [dict(t=k['t'], hold=(i == 0), x=np.array(k['x'], float)) for i, k in enumerate(data['keys'])]
        stance = json.loads((P / 'attack_keys.json').read_text('utf-8'))['keys'][0]['x']
        self.keys.append(dict(t=LENGTH, hold=True, x=np.array(stance, float)))
        self.arm_bones = R.right_chain | R.left_chain
        self.body_bones = [n for n in R.rig.names if n not in self.arm_bones and not n.startswith('WPN') and not n.startswith('Blade')]

    def sword_local(self, s):
        fr = self.sword['frames']
        x = min(max(s * self.rate, 0.0), len(fr) - 1.0)
        i = min(int(x), len(fr) - 2)
        f = x - i
        out = {}
        for j, n in enumerate(self.R.rig.names):
            a, b = fr[i][j], fr[i + 1][j]
            out[n] = blend_t(T(a[0:3], a[3:7], a[7:10]), T(b[0:3], b[3:7], b[7:10]), f)
        return out

    def sword_state(self, s):
        local = self.sword_local(s)
        w = self.R.rig.world(local)
        K = self.R.hand_rel.inverse() * w['hand_r']
        K = T(K.p, K.q, (1, 1, 1))
        left_rel = w['hand_l'].relative_to(T(K.p, K.q, (1, 1, 1)))      # left hand in the kukri grip frame
        return dict(local=local, K=K, elbow_r=w['lowerarm_r'].p, elbow_l=w['lowerarm_l'].p, left_rel=left_rel, hand_l=w['hand_l'])

    def tail_state(self, t):
        x = AC.spline(self.keys, t, ('x',))['x']
        W, phi, psi, du, de, C = self.F.unpack(x)
        K, E = self.R.arm_to_kukri(W, self.F.hint(W, phi, C), psi, de, du, C)
        return dict(K=K, elbow_r=E, C=C)

    def sample(self, t):
        R = self.R
        s = float(self.warp(min(t, TIME_MAP[-1][0])))
        sw = self.sword_state(s)
        # the kukri pose this blends with: the V1 tail spline (stance at 0, arms below the frame after the chop)
        tail = self.tail_state(t)
        R.twist_memory = {}
        tail_world, _ = R.pose(tail['K'], left_target_cam=AC.IDLE['L'], clav_r=tuple(tail['C']), pole_r=tail['elbow_r'], pole_r_weight=1.0)
        tail_local = R.rig.localize(tail_world)
        w_sword = smooth(*ENTRY, t) * (1.0 - smooth(*EXIT, t))
        w_l = smooth(*LEFT_ON, t) * (1.0 - smooth(*LEFT_OFF, t))
        # The sword's accepted arms are used as they are (bone locals, its own V9 twist split) and blended in local space
        # like the runtime entry blend: body and right arm with w_sword, left arm with w_l.  Only the knife follows.
        local = {}
        for n in R.rig.names:
            w = w_l if n in R.left_chain else w_sword
            local[n] = blend_t(tail_local[n], sw['local'][n], w) if w > 0.0 else tail_local[n]
        world = R.rig.world(local)
        a, b, c, d = HOLD_LIFT
        lift = smooth(a, b, t) * (1.0 - smooth(c, d, t))
        if lift > 1e-4:
            from kmath import qaxis, cam_to_mesh
            rot = qaxis(cam_to_mesh((0.0, 1.0, 0.0)), math.radians(-HOLD_LIFT_DEG * lift))   # pitch the arms up and back
            for side in 'rl':
                R.rotate_chain(world, 'clavicle_' + side, rot, world['clavicle_' + side].p.copy())
        K = R.hand_rel.inverse() * world['hand_r']
        K = T(K.p, K.q, (1, 1, 1))
        b = R.base
        world['WPN_root'] = T(K.p, K.q, b['WPN_root'].s)
        for n in R.wpn_desc:
            if n != 'WPN_root':
                world[n] = R.base_local[n] * world[R.rig.parents[R.rig.index[n]]]
        world['Blade_Base'] = T(K.point(np.array([0.0, 0.0, 7.5])), K.q, b['Blade_Base'].s)
        world['Blade_Tip'] = T(K.point(TIP), K.q, b['Blade_Tip'].s)
        diag = dict(right=self.arm_diag(world, 'r'), left=self.arm_diag(world, 'l'))
        diag['grip_ndc'] = ndc(mesh_to_cam(K.p))
        diag['tip_ndc'] = ndc(mesh_to_cam(K.point(TIP)))
        diag['elbow_ndc'] = ndc(mesh_to_cam(world['lowerarm_r'].p))
        diag['left_hand_ndc'] = ndc(mesh_to_cam(world['hand_l'].p))
        diag['w'] = (round(w_sword, 3), round(w_l, 3), round(s, 3))
        diag['arm_in_view'] = self.arm_in_view(world)
        return world, K, diag

    def arm_in_view(self, world):
        """Fraction of points along both arms (upper arm, forearm, hand; 5 cm skin pulled towards the view axis)
        that land inside the frame."""
        pts = []
        for side in 'rl':
            S, E, W = world['upperarm_' + side].p, world['lowerarm_' + side].p, world['hand_' + side].p
            pts += [S + (E - S) * f for f in (0.4, 0.7, 1.0)] + [E + (W - E) * f for f in (0.33, 0.66, 1.0)]
        inside = 0
        for p in pts:
            q = mesh_to_cam(p)
            lat = np.array([0.0, q[1], q[2]]); n = float(np.linalg.norm(lat))
            q = q - lat / n * min(5.0, n) if n > 1e-6 else q
            if q[0] > 2.0:
                x, y = ndc(q)
                inside += abs(x) < 1.0 and abs(y) < 1.0
        return inside / len(pts)

    def arm_diag(self, world, side):
        """Forearm twist vs bind (the skin's zero), wrist extension/deviation, reach -- same measures as kukri_rig."""
        from kmath import qmul, qconj, qrot
        from kukri_rig import twist_angle
        R = self.R
        up, lo, ha = world['upperarm_' + side], world['lowerarm_' + side], world['hand_' + side]
        rel = qmul(qconj(lo.q), ha.q)
        rel_ref = qmul(qconj(R.ref_world['lowerarm_' + side].q), R.ref_world['hand_' + side].q)
        fwd = (ha.p - lo.p) / np.linalg.norm(ha.p - lo.p)
        theta = twist_angle(qmul(rel, qconj(rel_ref)), qrot(qconj(lo.q), fwd))
        f = qrot(qconj(ha.q), fwd)
        Lu, Ll = R.lengths[side]
        return dict(theta=theta, twist_deg=math.degrees(theta), ext=math.degrees(math.atan2(f[1], -f[0])),
                    uln=math.degrees(math.atan2(f[2], -f[0])), reach=float(np.linalg.norm(ha.p - up.p)) / (Lu + Ll))


def author(preview=False):
    clip = SprintClip()
    R = clip.R
    R.reset_twist_memory()
    n = int(round(LENGTH * FPS))
    frames, diags, previews, prev_q = [], [], {}, None
    for i in range(n + 1):
        t = i / FPS
        world, K, d = clip.sample(t)
        keys = R.local_keys(world, prev_q)
        prev_q = {b: v[1] for b, v in keys.items()}
        frames.append({b: [list(map(float, v[0])), list(map(float, v[1])), list(map(float, v[2]))] for b, v in keys.items()})
        r, l = d['right'], d['left']
        diags.append(dict(t=round(t, 4), w=d['w'], reach=round(r['reach'], 3), twist=round(math.degrees(r['theta']), 1),
                          ext=round(r['ext'], 1), uln=round(r['uln'], 1), grip=[round(v, 3) for v in d['grip_ndc']],
                          tip=[round(v, 3) for v in d['tip_ndc']], elbow=[round(v, 2) for v in d['elbow_ndc']],
                          left=[round(v, 2) for v in d['left_hand_ndc']], left_twist=round(l['twist_deg'], 1),
                          left_ext=round(l['ext'], 1), left_uln=round(l['uln'], 1), depth=round(float(mesh_to_cam(K.p)[0]), 1),
                          arm_in_view=round(d['arm_in_view'], 2)))
        if preview and i % (FPS // 30) == 0:
            previews['SprintAttack_%04d' % int(round(t * 1000))] = (world, K)
    data = dict(name='SprintAttack', fps=FPS, length=LENGTH, loop=False, contact=list(CONTACT), bones=R.rig.names, frames=frames,
                diagnostics=diags, source='author_kukri_sprint.py V2 (sword overhead base)')
    (P / 'Clips' / 'SprintAttack.json').write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
    worst = dict(max_reach=max(x['reach'] for x in diags), twist=[min(x['twist'] for x in diags), max(x['twist'] for x in diags)],
                 twist_rate=max(abs(diags[i + 1]['twist'] - diags[i]['twist']) * FPS for i in range(len(diags) - 1)),
                 ext=[min(x['ext'] for x in diags), max(x['ext'] for x in diags)], uln=[min(x['uln'] for x in diags), max(x['uln'] for x in diags)])
    clips_path = P / 'clips.json'
    meta = json.loads(clips_path.read_text('utf-8'))
    meta.setdefault('clips', {})['SprintAttack'] = dict(length=LENGTH, loop=False, frames=n + 1, contact=list(CONTACT),
                                                         source='author_kukri_sprint.py V2', ranges=worst)
    clips_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    print('SprintAttack', json.dumps(worst))
    return diags, previews


def compare(names, out_dir):
    import cv2
    ref_dir = Path(r"D:\FPS3D\FPSGAME\Saved\Reference\KukriBV1CeYUeSE7b20261020\sprint_frames")
    cells = []
    for name in names:
        t = int(name.split('_')[1]) / 1000.0
        ref = cv2.imread(str(ref_dir / ('f%05d.png' % (REF_START + int(round(t * 30))))))
        ours = cv2.imread(str(out_dir / (name + '.png')))
        if ref is None or ours is None:
            continue
        w = ours.shape[1]
        ref = cv2.resize(ref, (w, w * 9 // 16))
        for im in (ref, ours):
            h = im.shape[0]
            for k in range(1, 4):
                cv2.line(im, (k * w // 4, 0), (k * w // 4, h), (90, 90, 90), 1)
                cv2.line(im, (0, k * h // 4), (w, k * h // 4), (90, 90, 90), 1)
        cv2.putText(ref, 'ref t=%.3f' % t, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, .7, (0, 0, 255), 2)
        cv2.putText(ours, 'ours', (8, 24), cv2.FONT_HERSHEY_SIMPLEX, .7, (0, 255, 255), 2)
        cells.append(np.vstack([ref, ours]))
    for s in range(0, len(cells), 6):
        chunk = cells[s:s + 6]
        while len(chunk) % 3:
            chunk.append(np.zeros_like(chunk[0]))
        cv2.imwrite(str(WORK / ('cmp_sprint_%d.jpg' % (s // 6))),
                    np.vstack([np.hstack(chunk[r:r + 3]) for r in range(0, len(chunk), 3)]), [cv2.IMWRITE_JPEG_QUALITY, 82])


if __name__ == '__main__':
    diags, previews = author('--preview' in sys.argv or '--compare' in sys.argv)
    if previews:
        from preview_tools import write_poses, render
        WORK.mkdir(parents=True, exist_ok=True)
        write_poses(previews, WORK / 'sprint_previews.json')
        for line in render(WORK / 'sprint_previews.json', WORK / 'previews', 480):
            if 'KUKRI_PREVIEW' not in line:
                print(line)
        if '--compare' in sys.argv:
            compare(sorted(previews, key=lambda n: int(n.split('_')[1])), WORK / 'previews')
