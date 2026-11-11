"""Dual sprint attack "DualSprintAttack" (2026-11-04): both hands chop down together.

User 2026-11-04: "双持冲刺攻击，左手的动作，弯刀和斧子都做成双手向下劈砍的动作，可以参考斧子双持三连击的最后一击".
The single sprint attack (Kukri20261020 SprintAttack, 40/30 s, KukriDashRhythm) is a two-handed jump chop: at 0.10 s both
hands close on ONE handle.  With a weapon in each hand that grip does not exist, so the pair's version is built like the
dual hatchet's stage 3 (HatchetDualAttack3): the right arm is the single chop as authored, the left arm is its mirror image
at the same time (dual_rig: left bone = ROT_X180 @ right world rotation, positions from the left bones' own locals), each
fist SPREAD cm out to its own side through the chop so the two weapons come down side by side instead of into one another,
and the left a little nearer the lens (LEFT_NEAR) where they pass the centre.
  in   from the dual hold (DualIdle frame 0) over BLEND_IN, the weapons kept apart in depth (UNCROSS) while they leave the
       hold's crossed heads
  out  back into the dual hold over BLEND_OUT (the single's own return to its stance is below the frame)
One clip for every pair (kukri, hatchet or mixed): the sprint attack is the kukri family's shared chop.  Same clock as the
single: contact 0.367-0.467, rift 0.345-0.410, 1.333 s (static_assert in KukriDualDashRhythm.h); gameplay is unchanged.
The off-hand weapon keeps its constant grip on hand_l.  Clearance is measured on the real sample points of both weapon kinds
(hatchet head, kukri edge) for all four pairings.
Run:  python -I author_dual_sprint_attack.py [--header]
"""
import json
import sys
from pathlib import Path

import numpy as np

P = Path(__file__).resolve().parent
DUAL = P.parent / 'DualKukriIdle20261025'
PAIRS = P.parent / 'HatchetPairs20261104'
KUKRI = P.parent / 'Kukri20261020'
for d in (DUAL, PAIRS):
    sys.path.insert(0, str(d))
from author_dual_attack import FPS, smooth, sample_local, frame_local, blend_local  # noqa: E402
from author_dual_equip import shift_arm, mirrored, unit  # noqa: E402
from dual_rig import DualRig, ndc  # noqa: E402
from kmath import T, mesh_to_cam  # noqa: E402
import author_pairs as AP  # noqa: E402
sys.path.insert(0, str(KUKRI))
from author_kukri_rift import crescent, fmt, STATIONS  # noqa: E402

NAME = 'DualSprintAttack'
SINGLE = KUKRI / 'Clips' / 'SprintAttack.json'
OUT = P / 'Clips'
HEADER = P.parents[1] / 'Source' / 'FPSGAME' / 'Weapons' / 'Kukri' / 'KukriDualDashRhythm.h'
LENGTH = 40.0 / 30.0                  # KukriDashRhythm::Seconds
RIFT = (0.345, 0.410)                 # KukriDashRhythm::RiftStart / RiftEnd
SPREAD = 9.0                          # cm out to each side through the chop (the dual hatchet chop's 9 cm)
SPREAD_T = (0.02, 0.09, 1.05, 1.25)   # ramp in (before the fists meet at the top, 0.10) / out with the hold blend, after
                                      # the arms have come back up from under the frame
LEFT_NEAR = 2.5                       # cm: the left fist nearer the lens where the weapons pass the centre
UNCROSS = 4.0                         # cm: leaving / re-entering the crossed hold, left nearer, right further
BLEND_IN = (0.0, 0.10)
BLEND_OUT = (1.02, 1.30)


def spread(t):
    a, b, c, d = SPREAD_T
    return SPREAD * smooth(a, b, t) * (1.0 - smooth(c, d, t))


RECROSS_LOW = 4.0                     # cm: re-entering the hold the left fist also comes in under the right one


def offsets(t):
    """Camera offsets (fwd, out, up) per arm (the left's in its mirrored space).  Leaving the crossed hold the left
    weapon goes in front; coming back into it from below the right one passes in front and the left behind and under it
    (the dual hatchet chop's order, author_hatchet_dual_chop.UNCROSS)."""
    near = LEFT_NEAR * smooth(0.25, 0.36, t) * (1.0 - smooth(0.55, 0.75, t))
    leave = UNCROSS * (1.0 - smooth(0.04, 0.12, t))
    back = UNCROSS * smooth(0.88, 0.98, t) * (1.0 - smooth(BLEND_OUT[1] - 0.10, BLEND_OUT[1], t))
    s = spread(t)
    return (np.array([leave * 0.5 - back, s, 0.0]),
            np.array([-(leave + near) + back, s, -RECROSS_LOW * back / UNCROSS]))


def author():
    D = DualRig()
    R = D.R
    rig = R.rig
    single = AP.load(SINGLE)
    hold = frame_local(AP.load(DUAL / 'Clips' / 'DualIdle.json'), 0)
    right_chain = [k for k in rig.names if k in R.right_chain]
    grip = AP.left_grip()
    b = R.base
    n = int(round(LENGTH * FPS))
    frames, diags, prev, worlds = [], [], None, []
    for i in range(n + 1):
        t = i / FPS
        w_r = rig.world(sample_local(single, min(t, single['length'])))
        src = rig.world(sample_local(single, min(t, single['length'])))
        rel_r = unit(w_r['WPN_root']).relative_to(unit(R.hand_rel.inverse() * w_r['hand_r']))
        o_r, o_l = offsets(t)
        shift_arm(R, w_r, o_r)
        shift_arm(R, src, o_l)
        world = mirrored(D, w_r, src)
        pose = rig.localize(world)
        w_in = 1.0 - smooth(*BLEND_IN, t)
        w_out = smooth(*BLEND_OUT, t)
        pose = blend_local(pose, hold, max(w_in, w_out), right_chain)
        pose = blend_local(pose, hold, max(w_in, w_out), D.left_chain)
        if i in (0, n):
            pose = dict(hold)
        world = rig.world(pose)
        K = rel_r * unit(R.hand_rel.inverse() * world['hand_r'])
        if i in (0, n):
            K = unit(world['WPN_root'])
        world['WPN_root'] = T(K.p, K.q, b['WPN_root'].s)
        for k in rig.names:
            if k in R.wpn_desc and k != 'WPN_root':
                world[k] = R.base_local[k] * world[D.parent[k]]
        for s_ in 'lr':
            ik = 'ik_hand_' + s_
            if ik in world:
                world[ik] = b[ik].relative_to(b['hand_' + s_]) * world['hand_' + s_]
        lk = R.local_keys(world, prev)
        prev = {k: v[1] for k, v in lk.items()}
        frames.append({k: [list(map(float, v[0])), list(map(float, v[1])), list(map(float, v[2]))] for k, v in lk.items()})
        Kr, Kl = unit(world['WPN_root']), grip * unit(world['hand_l'])
        worlds.append((world, Kr, Kl))
        reach = {s: float(np.linalg.norm(world['hand_' + s].p - world['upperarm_' + s].p)) / sum(R.lengths[s]) for s in 'rl'}
        diags.append(dict(t=round(t, 4), reach_r=round(reach['r'], 3), reach_l=round(reach['l'], 3),
                          grip_r=[round(v, 3) for v in ndc(mesh_to_cam(Kr.p))], grip_l=[round(v, 3) for v in ndc(mesh_to_cam(Kl.p))]))
    clip = dict(name=NAME, fps=FPS, length=LENGTH, loop=False, bones=rig.names, frames=frames, diagnostics=diags)
    return D, clip, worlds


def on_screen(K, pts):
    for v in pts:
        c = mesh_to_cam(K.point(v))
        if c[0] > 1.0:
            x, y = ndc(c)
            if abs(x) < 1.05 and abs(y) < 1.05:
                return True
    return False


def clearance(worlds):
    """Min distance between the weapons for every pairing; 'visible' only over frames where either weapon is on screen
    (the single chop's arms leave the frame over the top and come back up from under the camera)."""
    pts = dict(hatchet=AP.HEAD_SAMPLE, kukri=AP.BLADE_SAMPLE)
    out = {}
    for rk in ('kukri', 'hatchet'):
        for lk in ('kukri', 'hatchet'):
            best, seen = (1e9, 0.0), (1e9, 0.0)
            for i, (_, Kr, Kl) in enumerate(worlds):
                t = i / FPS
                if not BLEND_IN[1] * 0.5 < t < BLEND_OUT[1] - 0.02:   # the hold itself is the accepted dual hold
                    continue
                g = AP.gap(Kr, Kl, pts[rk], pts[lk])
                if g < best[0]:
                    best = (g, t)
                if g < seen[0] and (on_screen(Kr, pts[rk]) or on_screen(Kl, pts[lk])):
                    seen = (g, t)
            out[rk[0].upper() + lk[0].upper()] = dict(visible_min_gap_cm=round(seen[0], 2), at=round(seen[1], 3),
                                                      offscreen_min_gap_cm=round(best[0], 2), offscreen_at=round(best[1], 3))
    return out


def ribbons(worlds):
    rows = []
    for side in (1, 2):
        Ks = []
        for s in range(STATIONS):
            t = RIFT[0] + (RIFT[1] - RIFT[0]) * s / (STATIONS - 1)
            x = t * FPS
            i = min(int(x), len(worlds) - 2)
            f = x - i
            a, b_ = worlds[i][side], worlds[i + 1][side]
            Ks.append(AP.blend_t(a, b_, f))
        rows.append(crescent(Ks))
    return rows


def write_header(rows):
    right, left = rows
    HEADER.write_bytes(f"""#pragma once

#include "CoreMinimal.h"
#include "KukriDashRhythm.h"
#include "KukriSkillRiftRibbons.h"

// GENERATED by SourceAssets/DualSprintAttack20261104/author_dual_sprint_attack.py -- do not edit by hand.
/**
 * 双持冲刺攻击（2026-11-04）：两只手同时向下劈（参考双斧三连击第三段）。右手是单持冲刺攻击的跳劈，左手是它的镜像，
 * 两拳各向外 {SPREAD:.0f} cm，劈过中线时左拳略近；从双持待机起手，收回双持待机。弯刀、斧头和混搭共用这一段。
 * 时钟与单持冲刺攻击相同（命中窗、剑气时刻、时长），只换动作与两道剑气。
 */
namespace KukriDualDashRhythm
{{
    inline const TCHAR* Clip=TEXT("/Game/Weapons/Kukri20261020/Animations/A_Kukri_{NAME}.A_Kukri_{NAME}");
    inline constexpr float Seconds=40.f/30.f;
    static_assert(Seconds==KukriDashRhythm::Seconds,"the pair's sprint attack keeps the single's clock");
    inline constexpr int32 Stations={STATIONS};
    static_assert(Stations==KukriSkillRiftRibbons::Stations,"one station count for the dash rifts");
    /** The two crescents, swept by each blade over KukriDashRhythm::RiftStart-RiftEnd (viewmodel mesh space cm). */
    inline constexpr float RibbonRight[Stations][2][3]={{
        {fmt(right)}}};
    inline constexpr float RibbonLeft[Stations][2][3]={{
        {fmt(left)}}};
}}
""".encode('utf-8'))
    print('header ->', HEADER)


def main():
    D, clip, worlds = author()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / (NAME + '.json')).write_text(json.dumps(clip, separators=(',', ':')), encoding='utf-8')
    gaps = clearance(worlds)
    d = clip['diagnostics']
    summary = dict(clip=NAME, length=LENGTH, frames=len(clip['frames']), clearance=gaps,
                   reach_max=[max(x['reach_r'] for x in d), max(x['reach_l'] for x in d)],
                   strike=[x for x in d if abs(x['t'] - 0.4) < 1e-3][0])
    print(json.dumps(summary), flush=True)
    (P / 'clips.json').write_text(json.dumps(dict(summary, spread=SPREAD, left_near=LEFT_NEAR, uncross=UNCROSS,
                                                  source='author_dual_sprint_attack.py'), indent=2), encoding='utf-8')
    if '--header' in sys.argv:
        write_header(ribbons(worlds))
    return worlds


if __name__ == '__main__':
    main()
