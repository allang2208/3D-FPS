"""Dual kukri draw (Clips/DualEquip.json, 120 fps) and the left kukri's flight table
(Source/FPSGAME/Weapons/Kukri/KukriDualEquipBlade.h).

User 2026-10-27: "in the dual stance the left hand also does the right hand's toss-up draw, mirrored, with the details,
connecting naturally".  Source: the single kukri's toss-and-catch draw (Kukri20261020/Clips/Equip.json, 0.80 s,
KukriDrawRhythm: flick off the fist at 10/120 s, ~290 deg of spin up the right edge, caught at 13/30 s, gripped 0.47 s).
  right  the single draw as authored (the WPN_root flight, the open catching hand) up to 0.53 s, then into the dual hold
         (DualIdle frame 0) over 0.53-0.85 s instead of the single's drop back to its stance
  left   the same draw mirrored onto the left chain (dual_rig: left bone = ROT_X180 @ right world rotation, positions from
         the left bones' own locals), LEFT_DELAY later -- two tosses a beat apart read as hands, not a copy -- then into
         the hold over 0.60-0.92 s
  spread the single draw's knife crosses the centre line in the air and lies across it after the catch, so a plain mirror
         meets itself twice (-0.9 cm on the real mesh).  Each fist with its knife sits SPREAD cm further out to its own
         side (done below the frame before the flick: the flight keeps its shape), and from just before the catch the left
         fist comes LEFT_DEPTH toward the lens and the right RIGHT_DEPTH away (about where the dual hold has them).  The
         two-bone solve moves the hand; its rotation, the fingers and the forearm twist keep the draw.  Checked with
         Work/r4/dual_equip_check.py (factory >= 2.59 cm, hunter envelope >= 2.48 cm = the hold's own gap).
  left kukri  on hand_l the off-hand blade normally keeps the constant grip (left_kukri.json); through the flight it is
         the mirror of the right kukri at t - LEFT_DELAY (dual_rig.left_kukri), faded in and out of the grip with the same
         deviation band as the runtime's right-hand grip lock (0.6 / 2.5 cm, KukriArmsMeshComponent).  The relation to
         hand_l is baked at 60 Hz for the runtime (UKukriWeaponComponent drives OffhandBlade from it while DualEquip
         plays).
Run:  python -I author_dual_equip.py [--preview]      (DUAL_EQUIP=spread,right_depth,left_depth,delay overrides the tuning)
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
from author_dual_attack import FPS, SINGLE_DIR, smooth, sample_local, frame_local, blend_local  # noqa: E402
from dual_rig import DualRig, ROT_X180, ndc  # noqa: E402
from kmath import T, qmat, qfrommat, qslerp, mesh_to_cam, cam_to_mesh  # noqa: E402

_TUNE = [float(v) for v in os.environ.get('DUAL_EQUIP', '6,3,-6,0.067').split(',')]
SPREAD, RIGHT_DEPTH, LEFT_DEPTH, LEFT_DELAY = _TUNE   # cm out to each side; cm deeper (+) / toward the lens (-); s
SPREAD_T = (0.0, 0.10)              # own draw time: out while the fist is still below the frame, before the flick
DEPTH_T = (0.40, 0.53)              # own draw time: from just before the catch to the end of the roll
LENGTH = 0.92
RIGHT_HOLD = (0.53, 0.85)           # into the dual hold after the catch has closed and turned the edge
LEFT_HOLD = (0.53 + LEFT_DELAY, LENGTH)
TABLE_HZ = 60
HOLD_BAND, RELEASE_BAND, DEG_TO_CM = 0.6, 2.5, 0.25
HEADER = P.parents[1] / 'Source' / 'FPSGAME' / 'Weapons' / 'Kukri' / 'KukriDualEquipBlade.h'


def unit(x):
    return T(x.p, x.q, (1, 1, 1))


def blend_t(a, b, w):
    qb = b.q if np.dot(a.q, b.q) >= 0 else -b.q
    return T(a.p + (b.p - a.p) * w, qslerp(a.q, qb, w), (1, 1, 1))


def offset(t, depth, delay=0.0):
    """Camera-space shift of a fist at clip time t (the left's in its mirrored virtual-right space, + y outward)."""
    return np.array([depth * smooth(*DEPTH_T, t - delay), SPREAD * smooth(*SPREAD_T, t - delay), 0.0])


def shift_arm(R, world, d_cam, side='r'):
    """Move the hand (and so its knife) by d_cam with the two-bone solve, the elbow carried along, the clavicle fixed;
    the hand's world rotation, the fingers and the forearm twist bones keep the draw's own pose."""
    if not np.any(d_cam):
        return
    local = R.rig.localize(world)
    d = cam_to_mesh(d_cam)
    h = world['hand_' + side]
    memory = dict(R.twist_memory)
    R.solve_arm(world, side, T(h.p + d, h.q, h.s), pole_bias=world['lowerarm_' + side].p + d, pole_weight=1.0)
    R.twist_memory = memory
    fixed = {'upperarm_' + side, 'lowerarm_' + side, 'hand_' + side}
    for n, par in zip(R.rig.names, R.rig.parents):
        if n in R.upper_desc[side] and n not in fixed:
            world[n] = local[n] * world[par]


def mirrored(D, world_r, src):
    """world_r with its left chain replaced by the mirror of src's right chain (dual_rig)."""
    R = D.R
    world = dict(world_r)
    for k in R.rig.names:
        if k in D.left_chain:
            s = src[k[:-2] + '_r']
            world[k] = T(world[D.parent[k]].point(R.base_local[k].p), qfrommat(ROT_X180 @ qmat(s.q)), s.s)
    return world


def deviation(a, b):
    """Grip-lock deviation (cm): distance + 0.25 cm per degree (KukriArmsMeshComponent's measure)."""
    d = float(np.linalg.norm(a.p - b.p))
    dot = min(1.0, abs(float(np.dot(a.q, b.q))))
    return d + np.degrees(2.0 * np.arccos(dot)) * DEG_TO_CM


def main():
    D = DualRig()
    R = D.R
    rig = R.rig
    single = json.loads((SINGLE_DIR / 'Equip.json').read_text('utf-8'))
    hold = frame_local(json.loads((P / 'Clips' / 'DualIdle.json').read_text('utf-8')), 0)
    right_chain = [k for k in rig.names if k in R.right_chain]
    left_chain = D.left_chain
    left = json.loads((P / 'left_kukri.json').read_text('utf-8'))['rel_to_hand_l']
    GRIP = T(left['location'], left['rotation_wxyz'], (1, 1, 1))
    b = R.base
    n = int(round(LENGTH * FPS))
    frames, diags, prev, previews, table = [], [], None, {}, []
    seat_r = seat_l = 0.0
    for i in range(n + 1):
        t = i / FPS
        # Right: the single draw; left: the single draw LEFT_DELAY later, mirrored.
        w_r = rig.world(sample_local(single, min(t, single['length'])))
        tl = min(max(t - LEFT_DELAY, 0.0), single['length'])
        src = rig.world(sample_local(single, tl))
        # The knives relative to their fists in the draw (the flight; ~identity / the left grip once caught and seated).
        # Taken before the spread below: the fist and its knife (in the air or in the hand) move together.
        rel_r = unit(w_r['WPN_root']).relative_to(unit(R.hand_rel.inverse() * w_r['hand_r']))
        rel_l = D.left_kukri(unit(src['WPN_root'])).relative_to(unit(mirrored(D, w_r, src)['hand_l']))
        # Spread: each fist (and its knife) a little out to its own side, and after the catch the left toward the lens
        # and the right away from it, so the two flights and the two catch rolls pass each other (the single draw
        # crosses the centre line in the air and turns its blade across it after the catch).
        shift_arm(R, w_r, offset(t, RIGHT_DEPTH))
        shift_arm(R, src, offset(t, LEFT_DEPTH, LEFT_DELAY))
        world = mirrored(D, w_r, src)
        pose = rig.localize(world)
        pose = blend_local(pose, hold, smooth(*RIGHT_HOLD, t), right_chain)
        pose = blend_local(pose, hold, smooth(*LEFT_HOLD, t), left_chain)
        if i == n:
            pose = dict(hold)
        world = rig.world(pose)
        # Right kukri: the draw's knife-to-fist relation on the blended fist (the flight exactly as the single draw,
        # then carried into the hold by the fist), back to the hold's own grip by the end.
        w_end = smooth(RIGHT_HOLD[1] - 0.05, RIGHT_HOLD[1], t)
        K = blend_t(rel_r, T(), w_end) * unit(R.hand_rel.inverse() * world['hand_r'])
        world['WPN_root'] = T(K.p, K.q, b['WPN_root'].s)
        for k in rig.names:
            if k in R.wpn_desc and k != 'WPN_root':
                world[k] = R.base_local[k] * world[D.parent[k]]
        if i == n:
            world = rig.world(dict(hold))
        for s_ in 'lr':
            ik = 'ik_hand_' + s_
            if ik in world:
                world[ik] = b[ik].relative_to(b['hand_' + s_]) * world['hand_' + s_]
        # Left kukri: the mirror of the delayed draw's knife, shown through the same lock band as the right one at
        # runtime (locked to the grip below 0.6 cm of deviation, free above 2.5 cm), on the grip by the hold.
        dev = deviation(rel_l, GRIP)
        free = float(smooth(HOLD_BAND, RELEASE_BAND, dev)) * (1.0 - smooth(LEFT_HOLD[1] - 0.05, LEFT_HOLD[1], t))
        rel = blend_t(GRIP, rel_l, free)
        if t > 0.6:
            seat_l = max(seat_l, deviation(rel_l, GRIP))
            seat_r = max(seat_r, float(np.linalg.norm(rel_r.p)) + np.degrees(2 * np.arccos(min(1, abs(rel_r.q[0])))) * DEG_TO_CM)
        H = unit(world['hand_l'])
        Kl = rel * H
        if i % (FPS // TABLE_HZ) == 0:
            q = rel.q if not table or np.dot(rel.q, table[-1][1]) >= 0 else -rel.q
            table.append((t, q, rel.p))
        lk = R.local_keys(world, prev)
        prev = {k: v[1] for k, v in lk.items()}
        frames.append({k: [list(map(float, v[0])), list(map(float, v[1])), list(map(float, v[2]))] for k, v in lk.items()})
        diags.append(dict(t=round(t, 4), left_free=round(free, 3), left_dev_cm=round(float(dev), 2),
                          hand_r=[round(v, 3) for v in ndc(mesh_to_cam(world['hand_r'].p))],
                          hand_l=[round(v, 3) for v in ndc(mesh_to_cam(world['hand_l'].p))]))
        if '--preview' in sys.argv and i % 4 == 0:
            K = world['WPN_root']
            previews['dualequip_%04d' % int(round(t * 1000))] = dict(
                bones={k: x.pack() for k, x in world.items()}, kukri_r=T(K.p, K.q, (1, 1, 1)).pack(), kukri_l=Kl.pack())
    data = dict(name='DualEquip', fps=FPS, length=LENGTH, loop=False, bones=rig.names, frames=frames, diagnostics=diags,
                release=single.get('release'), catch=single.get('catch'), left_delay=LEFT_DELAY)
    (P / 'Clips' / 'DualEquip.json').write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
    # FQuat order (x, y, z, w) and the component's units (bone space cm / 100, like OffhandHandToBlade()).
    rows = ',\n        '.join('{%s}' % ','.join('%.7ff' % v for v in (q[1], q[2], q[3], q[0], p[0] / 100, p[1] / 100, p[2] / 100))
                               for _, q, p in table)
    (P / 'Work' / 'dual_equip_left.json').write_text(json.dumps(dict(
        note='DualEquip: off-hand kukri relative to hand_l (cm, wxyz) at %d Hz (author_dual_equip.py)' % TABLE_HZ,
        rows=[[t, list(map(float, q)), list(map(float, p))] for t, q, p in table])), encoding='utf-8')
    free_t = [d['t'] for d in diags if d['left_free'] > 0]
    HEADER.write_text(f"""#pragma once

// GENERATED by SourceAssets/DualKukriIdle20261025/author_dual_equip.py -- do not edit by hand.
// Dual kukri draw (clip "DualEquip", {LENGTH:.2f} s, the single toss-and-catch draw on the right and its mirror on the
// left {LEFT_DELAY:.3f} s later): the off-hand kukri relative to hand_l at {TABLE_HZ} Hz, rows {{qx, qy, qz, qw, x, y, z}} in
// OffhandHandToBlade()'s units -- the constant grip outside the mirrored flight
// ({free_t[0] if free_t else 0:.3f}-{free_t[-1] if free_t else 0:.3f} s), the lock band of the right knife's grip in between.
namespace KukriDualEquipBlade
{{
    inline constexpr float Hz={TABLE_HZ}.f, LeftDelay={LEFT_DELAY:.4f}f;
    inline constexpr int32 Samples={len(table)};
    inline constexpr float Relative[Samples][7]={{
        {rows}}};
}}
""", encoding='utf-8')
    print('DualEquip %.3f s, %d frames; table %d samples; left flight %.3f-%.3f s; seated after 0.6 s: right %.2f, left %.2f cm' % (
        LENGTH, len(frames), len(table), free_t[0] if free_t else 0, free_t[-1] if free_t else 0, seat_r, seat_l))
    if previews:
        out = P / 'Work' / 'render'
        out.mkdir(parents=True, exist_ok=True)
        (out / 'dualequip.json').write_text(json.dumps(dict(poses=previews)), encoding='utf-8')


if __name__ == '__main__':
    main()
