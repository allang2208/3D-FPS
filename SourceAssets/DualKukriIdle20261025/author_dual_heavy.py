"""Dual kukri heavy strike clips (Clips/DualHeavyCharge.json 2.0 s, Clips/DualHeavyRelease.json 1.0 s, 120 fps) from
heavy_keys.json (fit_dual_heavy.py).  Reference BV19dUqBJECT 近战动作 #3「X」, file 78.20-79.30 s (t = 0 at frame 2345).

Charge (the runtime's KukriHeavyRhythm::ChargePoseTime: 0-0.40 the raise on the martial clock, 0.40-2.00 the load
stretched over the rest of the charge; same lengths as the single kukri's HeavyCharge):
  0.00-0.10 the X opens: both fists out to their own sides, each blade turned up and OUT (ref 0.033-0.133)
  0.10-0.20 up the sides, blades upright; 0.20-0.40 the wrists cock back like hammers, the blades laid back over the
  shoulders, the pommels forward, fists high at both edges (the reference's hidden wind-up, ref 0.17-0.30)
  0.40-2.00 the fists draw a little further back and up (the load); the runtime adds the full-charge tremble
Release (the runtime's dual heavy tables, KukriRhythm::DualHeavy*), R12: a left/right CROSSING X slash:
  0.000 loaded; 0.033 both fists high in front, the blades back over the shoulders (ref 0.333)
  0.067 the right fist on the crosshair, the left lower on its own side, each blade trailing up toward its own side
        (ref 0.367); the strike moment 0.083
  0.100 the arms crossed: the right fist at the lower left, the left at the lower right, the trailing blades crossing in an X
        above them (ref 0.400)
  R14 (user: "the crossing is right but not wide enough; both hands and blades should end below the bottom of the
  screen, then back to the idle"): the right fist reaches the far lower left (-0.57, 0.71), the left past the centre to
  the lower right (+0.34, 0.86) at 0.100, both carry on out of the bottom of the frame crossed (0.133 / 0.200);
  below it the right tucks in (0.27), the left goes back to its own side first (0.27-0.40), then the right (0.36-0.50),
  into the hanging rests; 0.70-1.00 up from below into the dual hold (ref 1.00-1.13).
  (R13 held the crossed finish in view; R12 crossed less.)
The keys interpolate in the fitted arm parameters (PCHIP, elbow swivel / forearm roll unwrapped); the left is the mirror of
its own virtual-right keys (fitted against the right key with an arm clearance term, fit_dual_heavy.fit_pair).
Run:  python -I author_dual_heavy.py [--preview]   (keys: python -I Work/r4/heavy_assemble.py)
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.interpolate import CubicSpline, PchipInterpolator

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
from author_dual_attack import FPS, SINGLE_DIR, smooth, frame_local, blend_local  # noqa: E402
from dual_rig import DualRig, ROT_X180, ndc  # noqa: E402
from kmath import T, qmat, qfrommat, mesh_to_cam  # noqa: E402

CHARGE = dict(length=2.0, t_in=(0.0, 0.10), keys=('open', 'up', 'load', 'deep'))
# R16 (the 猎手刀身 long blade, tip 36 cm): the trailing long blades cut into each other as they cross and turn down to
# leave the frame (-0.5 cm at 0.15 s on the hunter envelope, kukri_sdf KUKRI_SDF_VARIANT=hunter).  The left's release
# keys from 'cross' on (half at 'over') shift by LEFT_OFFSET, camera cm: 2 deeper, 4 to its own side, 1 up -> >= 1.1 cm
# on the hunter envelope (scanned in DUAL_HEAVY_LEFT_OFFSET: a pure drop or depth shift kept the 0.15 s clash).
import os as _os
LEFT_OFFSET = tuple(float(v) for v in _os.environ.get('DUAL_HEAVY_LEFT_OFFSET', '2,-4,1').split(','))
RELEASE = dict(length=1.0, keys=('deep', 'over', 'cross', 'x', 'low', 'end'), hang_r=(0.26, 0.40), hang_l=(0.19, 0.33),
               rise=(0.70, 1.00), contact=(0.033, 0.133), strike=0.083)
CHARGE_T = {'open': 0.10, 'up': 0.20, 'load': 0.40, 'deep': 2.00}
RELEASE_T = {'deep': 0.0, 'over': 0.037, 'cross': 0.068, 'x': 0.109, 'low': 0.136, 'end': 0.158}


def unwrap(rows):
    """Elbow swivel / forearm roll of consecutive keys onto the same turn."""
    rows = np.array(rows, float)
    for i in range(1, len(rows)):
        rows[i, :, 3:5] -= 360.0 * np.round((rows[i, :, 3:5] - rows[i - 1, :, 3:5]) / 360.0)
    return rows


def main():
    D = DualRig()
    R = D.R
    rig = R.rig
    import fit_dual_thrust as M
    F = M.FR.Fitter(R)
    keys = json.loads((P / 'heavy_keys.json').read_text('utf-8'))
    hold = frame_local(json.loads((P / 'Clips' / 'DualIdle.json').read_text('utf-8')), 0)
    single = json.loads((SINGLE_DIR / 'Attack3.json').read_text('utf-8'))
    right_chain = [k for k in rig.names if k in R.right_chain or k in R.wpn_desc]
    left_chain = D.left_chain
    chains = right_chain + left_chain
    # Hanging rests below the frame (as the dual combo): the single clip's lowered left arm and its mirror for the right.
    w0 = rig.world(frame_local(single, 0))
    world = rig.world(dict(hold))
    for k in rig.names:
        if k in R.right_chain:
            src = w0[k[:-2] + '_l']
            world[k] = T(world[D.parent[k]].point(R.base_local[k].p), qfrommat(ROT_X180 @ qmat(src.q)), src.s)
    hang = rig.localize(world)
    hang.update({k: v for k, v in frame_local(single, 0).items() if k in left_chain})
    left_rel = json.loads((P / 'left_kukri.json').read_text('utf-8'))['rel_to_hand_l']
    LREL = T(left_rel['location'], left_rel['rotation_wxyz'], (1, 1, 1))

    def arms_local(x):
        world = dict(F.evaluate(x[0], full=True)['world'])
        virtual = F.evaluate(x[1], full=True)['world']
        for k in left_chain:
            src = virtual[k[:-2] + '_r']
            world[k] = T(world[D.parent[k]].point(R.base_local[k].p), qfrommat(ROT_X180 @ qmat(src.q)), src.s)
        return rig.localize(world)

    def track(names, times, smooth_c2=False):
        ts = [times[n] for n in names]
        rows = unwrap([[keys['right'][n]['x'], keys['left'][n]['x']] for n in names])
        if smooth_c2:                      # the release: the left's keys offset (R16)
            for i, n in enumerate(names):
                f = 0.0 if n == 'deep' else 0.5 if n == 'over' else 1.0
                rows[i, 1, 0:3] += np.asarray(LEFT_OFFSET) * f
        rows = rows.reshape(len(ts), -1)
        if smooth_c2:
            # R15 (user: the cut stutters): one C2 curve through the whole cut, at rest on the loaded pose, running on
            # through the last key below the frame -- PCHIP flattened every key the path turns at (the fists slowed at each).
            z = np.zeros(rows.shape[1])
            return CubicSpline(ts, rows, axis=0, bc_type=((1, z), (2, z))), ts[0], ts[-1]
        return PchipInterpolator(ts, rows, axis=0), ts[0], ts[-1]

    def bake(name, length, pose_at, contact, preview, tag):
        n = int(round(length * FPS))
        frames, diags, prev, previews = [], [], None, {}
        for i in range(n + 1):
            t = i / FPS
            pose = pose_at(t, i == n)
            world = rig.world(pose)
            b = R.base
            K = R.hand_rel.inverse() * world['hand_r']
            world['WPN_root'] = T(K.p, K.q, b['WPN_root'].s)
            for k in rig.names:
                if k in R.wpn_desc and k != 'WPN_root':
                    world[k] = R.base_local[k] * world[D.parent[k]]
            for s in 'lr':
                ik = 'ik_hand_' + s
                if ik in world:
                    world[ik] = b[ik].relative_to(b['hand_' + s]) * world['hand_' + s]
            lk = R.local_keys(world, prev)
            prev = {k: v[1] for k, v in lk.items()}
            frames.append({k: [list(map(float, v[0])), list(map(float, v[1])), list(map(float, v[2]))] for k, v in lk.items()})
            hr, hl = mesh_to_cam(world['hand_r'].p), mesh_to_cam(world['hand_l'].p)
            diags.append(dict(t=round(t, 4), hand_r=[round(v, 3) for v in ndc(hr)], hand_l=[round(v, 3) for v in ndc(hl)]))
            if preview and (i % 6 == 0 or (name.endswith('Release') and i <= 30 and i % 2 == 0)):
                K = world['WPN_root']
                hl_ = world['hand_l']
                previews['%s_%04d' % (tag, int(round(t * 1000)))] = dict(
                    bones={k: x.pack() for k, x in world.items()}, kukri_r=T(K.p, K.q, (1, 1, 1)).pack(),
                    kukri_l=(LREL * T(hl_.p, hl_.q, (1, 1, 1))).pack())
        data = dict(name=name, fps=FPS, length=length, loop=False, bones=rig.names, frames=frames, diagnostics=diags)
        if contact:
            data['contact'] = list(contact)
        (P / 'Clips' / (name + '.json')).write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
        print('%s %.4f s, %d frames' % (name, length, len(frames)))
        if previews:
            out = P / 'Work' / 'render'
            out.mkdir(parents=True, exist_ok=True)
            (out / (tag + '.json')).write_text(json.dumps(dict(poses=previews)), encoding='utf-8')

    preview = '--preview' in sys.argv
    c = CHARGE
    charge_x, c0, c1 = track(c['keys'], CHARGE_T)

    def charge_pose(t, last):
        x = charge_x(min(max(t, c0), c1)).reshape(2, 9)
        return blend_local(dict(hold), arms_local(x), smooth(*c['t_in'], t), chains)
    bake('DualHeavyCharge', c['length'], charge_pose, None, preview, 'dualheavycharge')

    r = RELEASE
    release_x, r0, r1 = track(r['keys'], RELEASE_T, smooth_c2=True)

    def release_pose(t, last):
        if last:
            return dict(hold)
        x = release_x(min(max(t, r0), r1)).reshape(2, 9)
        # The arms end crossed below the frame and hold there; the left (behind) goes back to its own side first, then the
        # right, into the hanging rests (all below the frame); both rise from there into the hold.
        pose = blend_local(arms_local(x), hang, smooth(*r['hang_r'], t), right_chain)
        pose = blend_local(pose, hang, smooth(*r['hang_l'], t), left_chain)
        return blend_local(pose, hold, smooth(*r['rise'], t), chains)
    bake('DualHeavyRelease', r['length'], release_pose, r['contact'], preview, 'dualheavyrelease')


if __name__ == '__main__':
    main()
