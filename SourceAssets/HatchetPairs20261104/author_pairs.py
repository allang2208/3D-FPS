"""Hatchet pairs (2026-11-04): the dual-hatchet draw and the mixed hatchet + kukri pair clips.

User 2026-11-04: "双持装备斧头时，两只手都替换成现在单持的装备动作；副手装备弯刀或者斧头时，按双持的副手动画，包括装备攻击技能等"
-- clarified: a hatchet + kukri pair plays each hand's own weapon.

Clips (120 fps, Clips/*.json) -> /Game/Weapons/TacticalHatchet20261101/Animations/A_TacticalHatchet_<name>:
  DualEquip       both hands the single hatchet draw (HatchetEquip V2.1, 0.90 s): the right as authored, the left its mirror
                  LEFT_DELAY later (as the kukri pair's DualEquip), each into the dual hold (DualIdle frame 0) after its own
                  catch roll.  Each fist with its hatchet sits SPREAD cm out to its own side from the start (the lift comes
                  from below the frame) and, from just before the catch, the left comes nearer and the right further, so the
                  two heads pass each other where the single draw brings its hatchet to the centre.
  PairEquipHK/KH  right hatchet + left kukri / right kukri + left hatchet: each arm is its weapon's side of DualEquip above or
                  of the kukri pair's DualEquip (DualKukriIdle20261025); the arms are separate chains and both end in the hold.
  PairAttack3HK/KH  combo stage 3 of a mixed pair: the hatchet hand chops (HatchetDualAttack3), the kukri hand thrusts
                  (DualAttack3).  Both are on the double thrust's clock (246/120 s), so the arms are taken frame by frame.
The off-hand hatchet's flight through the left draw is baked at 60 Hz into HatchetPairRhythm.h (relative to hand_l, the same
lock band as author_dual_equip.py's kukri table).  Clearance between the two weapons (real head / blade sample points) is
printed per clip.
Run:  python -I author_pairs.py [--header]
"""
import json
import sys
from pathlib import Path

import numpy as np

P = Path(__file__).resolve().parent
DUAL = P.parent / 'DualKukriIdle20261025'
sys.path.insert(0, str(DUAL))
from author_dual_attack import FPS, smooth, sample_local, frame_local, blend_local  # noqa: E402
from author_dual_equip import shift_arm, mirrored, deviation, blend_t, unit  # noqa: E402
from dual_rig import DualRig, ndc  # noqa: E402
from kmath import T, mesh_to_cam  # noqa: E402
from kukri_rig import TIP, BLADE_BASE, EDGE_SAMPLES  # noqa: E402

HATCHET_EQUIP = P.parent / 'HatchetEquip20261101' / 'Clips' / 'HatchetEquip.json'
HATCHET_DUAL_CHOP = P.parent / 'HatchetChop20261102' / 'Clips' / 'HatchetDualAttack3.json'
OUT = P / 'Clips'
HEADER = P.parents[1] / 'Source' / 'FPSGAME' / 'Weapons' / 'Kukri' / 'HatchetPairRhythm.h'
FOLDER = '/Game/Weapons/TacticalHatchet20261101/Animations/'

SPREAD = 8.0                        # cm out to each side (the hatchet's head is far wider than the kukri's blade)
RIGHT_DEPTH, LEFT_DEPTH = 3.0, -6.0  # cm deeper (+) / toward the lens (-) from just before the catch
LEFT_DELAY = 0.067                  # the kukri pair's DualEquip delay (KukriDualEquipBlade::LeftDelay)
DEPTH_T = (0.30, 0.48)              # own draw time: the catch (0.383) and the pull to the centre
RIGHT_HOLD = (0.66, 0.93)           # into the dual hold once the head has swung over and the edge faces forward
LENGTH = 1.0
LEFT_HOLD = (RIGHT_HOLD[0] + LEFT_DELAY, LENGTH)
TABLE_HZ = 60
HOLD_BAND, RELEASE_BAND = 0.6, 2.5

HEAD_SAMPLE = [np.array(v) for v in ([4.0, 0.0, 30.9], [16.35, 0.0, 27.0], [16.0, 0.0, 19.0], [-4.5, 0.0, 30.0],
                                     [-4.5, 0.0, 22.0], [6.0, 0.0, 16.5], [8.0, 0.0, 23.0], [0.0, 0.0, 12.0])]
BLADE_SAMPLE = [np.asarray(v, float) for v in [BLADE_BASE, TIP] + list(EDGE_SAMPLES)]


def load(path):
    return json.loads(Path(path).read_text('utf-8'))


def offset(t, depth, delay=0.0):
    """Camera-space shift of a fist at clip time t (the left's in its mirrored virtual-right space, + y outward)."""
    return np.array([depth * smooth(*DEPTH_T, t - delay), SPREAD, 0.0])


def left_grip():
    g = load(DUAL / 'left_kukri.json')['rel_to_hand_l']
    return T(g['location'], g['rotation_wxyz'], (1, 1, 1))


def table_sample(table, t):
    """A 60 Hz (t, q wxyz, p cm) relative table at time t (clamped)."""
    x = min(max(t * TABLE_HZ, 0.0), len(table) - 1.0)
    i = min(int(x), len(table) - 2)
    f = x - i
    a, b = table[i], table[i + 1]
    return blend_t(T(a[2], a[1], (1, 1, 1)), T(b[2], b[1], (1, 1, 1)), f)


def gap(Kr, Kl, right_pts, left_pts):
    pr = [Kr.point(v) for v in right_pts]
    pl = [Kl.point(v) for v in left_pts]
    return min(float(np.linalg.norm(a - c)) for a in pr for c in pl)


# ---------------------------------------------------------------- the dual hatchet draw
def author_dual_equip(D):
    R = D.R
    rig = R.rig
    single = load(HATCHET_EQUIP)
    hold = frame_local(load(DUAL / 'Clips' / 'DualIdle.json'), 0)
    right_chain = [k for k in rig.names if k in R.right_chain]
    GRIP = left_grip()
    b = R.base
    n = int(round(LENGTH * FPS))
    frames, diags, table, prev = [], [], [], None
    for i in range(n + 1):
        t = i / FPS
        w_r = rig.world(sample_local(single, min(t, single['length'])))
        tl = min(max(t - LEFT_DELAY, 0.0), single['length'])
        src = rig.world(sample_local(single, tl))
        rel_r = unit(w_r['WPN_root']).relative_to(unit(R.hand_rel.inverse() * w_r['hand_r']))
        rel_l = D.left_kukri(unit(src['WPN_root'])).relative_to(unit(mirrored(D, w_r, src)['hand_l']))
        shift_arm(R, w_r, offset(t, RIGHT_DEPTH))
        shift_arm(R, src, offset(t, LEFT_DEPTH, LEFT_DELAY))
        world = mirrored(D, w_r, src)
        pose = rig.localize(world)
        pose = blend_local(pose, hold, smooth(*RIGHT_HOLD, t), right_chain)
        pose = blend_local(pose, hold, smooth(*LEFT_HOLD, t), D.left_chain)
        if i == n:
            pose = dict(hold)
        world = rig.world(pose)
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
        dev = deviation(rel_l, GRIP)
        free = float(smooth(HOLD_BAND, RELEASE_BAND, dev)) * (1.0 - smooth(LEFT_HOLD[1] - 0.05, LEFT_HOLD[1], t))
        rel = blend_t(GRIP, rel_l, free)
        if i % (FPS // TABLE_HZ) == 0:
            q = rel.q if not table or np.dot(rel.q, table[-1][1]) >= 0 else -rel.q
            table.append((t, np.array(q, float), np.array(rel.p, float)))
        lk = R.local_keys(world, prev)
        prev = {k: v[1] for k, v in lk.items()}
        frames.append({k: [list(map(float, v[0])), list(map(float, v[1])), list(map(float, v[2]))] for k, v in lk.items()})
        Kr = unit(world['WPN_root'])
        Kl = rel * unit(world['hand_l'])
        diags.append(dict(t=round(t, 4), left_free=round(free, 3),
                          gap=round(gap(Kr, Kl, HEAD_SAMPLE, HEAD_SAMPLE), 2),
                          head_r=[round(v, 3) for v in ndc(mesh_to_cam(Kr.point([0.0, 0.0, 23.5])))],
                          head_l=[round(v, 3) for v in ndc(mesh_to_cam(Kl.point([0.0, 0.0, 23.5])))]))
    data = dict(name='HatchetDualEquip', fps=FPS, length=LENGTH, loop=False, bones=rig.names, frames=frames,
                diagnostics=diags, release=single.get('release'), catch=single.get('catch'), left_delay=LEFT_DELAY)
    return data, table


# ---------------------------------------------------------------- arm composition (mixed pairs)
def compose(D, name, right, left, length=None):
    """Right arm (and every non-left bone) from `right`, the left chain and ik_hand_l from `left`, frame by frame; the
    shorter clip holds its last frame (both end on the same pose)."""
    lefts = set(D.left_chain) | {'ik_hand_l'}
    nr, nl = len(right['frames']), len(left['frames'])
    n = max(nr, nl)
    frames = []
    for i in range(n):
        fr, fl = right['frames'][min(i, nr - 1)], left['frames'][min(i, nl - 1)]
        frames.append({b: (fl[b] if b in lefts else fr[b]) for b in right['bones']})
    return dict(name=name, fps=FPS, length=length if length is not None else (n - 1) / FPS, loop=False,
                bones=right['bones'], frames=frames)


def clearance(D, clip, right_pts, left_pts, left_rel, window):
    """Min distance between the right weapon (WPN_root) and the left one (left_rel(t) * hand_l) within window."""
    rig = D.R.rig
    best = (1e9, 0.0)
    for i, fr in enumerate(clip['frames']):
        t = i / FPS
        if not window[0] <= t <= window[1]:
            continue
        world = rig.world({b: T(v[0], v[1], v[2]) for b, v in fr.items()})
        g = gap(unit(world['WPN_root']), left_rel(t) * unit(world['hand_l']), right_pts, left_pts)
        if g < best[0]:
            best = (g, t)
    return round(best[0], 2), round(best[1], 3)


def write_clip(data):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / (data['name'] + '.json')).write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
    print('%-24s %.3f s  %d frames' % (data['name'], data['length'], len(data['frames'])), flush=True)


def write_header(table, length):
    rows = ',\n        '.join('{%s}' % ','.join('%.7ff' % v for v in (q[1], q[2], q[3], q[0], p[0] / 100, p[1] / 100, p[2] / 100))
                               for _, q, p in table)
    path = lambda n: 'TEXT("%sA_TacticalHatchet_%s.A_TacticalHatchet_%s")' % (FOLDER, n, n)
    HEADER.write_bytes(f"""#pragma once

#include "CoreMinimal.h"
#include "KukriRhythm.h"

// GENERATED by SourceAssets/HatchetPairs20261104/author_pairs.py -- do not edit by hand.
/**
 * 斧头组合的双持动作（2026-11-04）。每只手按自己的武器播：
 *  - 双斧装备（DualEquip，{length:.2f} s）：两手都是单持斧头的竖直抛接，左手镜像、晚 {LEFT_DELAY:.3f} s，各自接住后收进双持待机；
 *  - 斧+弯刀装备（PairEquipHK / KH）：斧头那只手是斧头抛接，弯刀那只手是双弯刀装备里同侧的那一半；
 *  - 斧+弯刀第三段（PairAttack3HK / KH）：斧头那只手劈砍（HatchetDualAttack3 同侧），弯刀那只手双刺（DualAttack3 同侧），同一双刺时钟。
 * HK = 主手斧头、副手弯刀；KH = 主手弯刀、副手斧头。LeftHatchet 是副手斧在左手抛接期间相对 hand_l 的变换（{TABLE_HZ} Hz，
 * {{qx, qy, qz, qw, x, y, z}}，OffhandHandToBlade() 的单位），抛接以外为固定握持。
 */
namespace HatchetPairRhythm
{{
    inline const TCHAR* DualEquipClip={path('DualEquip')};
    inline const TCHAR* EquipHKClip={path('PairEquipHK')};
    inline const TCHAR* EquipKHClip={path('PairEquipKH')};
    inline const TCHAR* Attack3HKClip={path('PairAttack3HK')};
    inline const TCHAR* Attack3KHClip={path('PairAttack3KH')};
    inline constexpr float DualEquipSeconds={length:.4f}f, LeftDelay={LEFT_DELAY:.4f}f, Hz={TABLE_HZ}.f;
    inline constexpr float Attack3Seconds=246.f/120.f;
    static_assert(Attack3Seconds==KukriRhythm::DualThrustSeconds,"mixed stage 3 runs on the double thrust's clock");
    inline constexpr int32 Samples={len(table)};
    inline constexpr float LeftHatchet[Samples][7]={{
        {rows}}};

    inline FTransform SampleLeftHatchet(float Time)
    {{
        const float X=FMath::Clamp(Time*Hz,0.f,float(Samples-1));
        const int32 I=FMath::Min(int32(X),Samples-2);
        const float* A=LeftHatchet[I];const float* B=LeftHatchet[I+1];
        const FQuat Q=FQuat::Slerp(FQuat(A[0],A[1],A[2],A[3]),FQuat(B[0],B[1],B[2],B[3]),X-I).GetNormalized();
        return FTransform(Q,FMath::Lerp(FVector(A[4],A[5],A[6]),FVector(B[4],B[5],B[6]),X-I),FVector(.01f));
    }}
}}
""".encode('utf-8'))
    print('header ->', HEADER)


def main():
    D = DualRig()
    dual, table = author_dual_equip(D)
    dual['name'] = 'DualEquip'
    write_clip(dual)
    gaps = [d['gap'] for d in dual['diagnostics'] if 0.05 <= d['t'] <= LENGTH]
    worst = min(dual['diagnostics'], key=lambda d: d['gap'])
    kk = load(DUAL / 'Clips' / 'DualEquip.json')
    hh = dual
    kukri_rows = load(DUAL / 'Work' / 'dual_equip_left.json')['rows']
    rel_k = lambda t: table_sample(kukri_rows, t)
    rel_h = lambda t: table_sample([(t_, q, p) for t_, q, p in table], t)
    grip = left_grip()
    hk = compose(D, 'PairEquipHK', hh, kk)
    kh = compose(D, 'PairEquipKH', kk, hh)
    thrust = load(DUAL / 'Clips' / 'DualAttack3.json')
    chop = load(HATCHET_DUAL_CHOP)
    ahk = compose(D, 'PairAttack3HK', chop, thrust, chop['length'])
    akh = compose(D, 'PairAttack3KH', thrust, chop, chop['length'])
    for c in (hk, kh, ahk, akh):
        write_clip(c)
    report = dict(
        DualEquip=dict(min_gap_cm=min(gaps), at=worst['t'], hold_gap_cm=dual['diagnostics'][-1]['gap']),
        PairEquipHK=clearance(D, hk, HEAD_SAMPLE, BLADE_SAMPLE, rel_k, (0.05, 1.0)),
        PairEquipKH=clearance(D, kh, BLADE_SAMPLE, HEAD_SAMPLE, rel_h, (0.05, 1.0)),
        PairAttack3HK=clearance(D, ahk, HEAD_SAMPLE, BLADE_SAMPLE, lambda t: grip, (0.2, 1.8)),
        PairAttack3KH=clearance(D, akh, BLADE_SAMPLE, HEAD_SAMPLE, lambda t: grip, (0.2, 1.8)),
        DualAttack3_reference=clearance(D, thrust, BLADE_SAMPLE, BLADE_SAMPLE, lambda t: grip, (0.2, 1.8)),
        HatchetDualAttack3_reference=clearance(D, chop, HEAD_SAMPLE, HEAD_SAMPLE, lambda t: grip, (0.2, 1.8)))
    print(json.dumps(report), flush=True)
    (P / 'clips.json').write_text(json.dumps(dict(clearance_cm=report, spread=SPREAD, depth=[RIGHT_DEPTH, LEFT_DEPTH],
                                                  left_delay=LEFT_DELAY, length=LENGTH,
                                                  source='author_pairs.py'), indent=2), encoding='utf-8')
    if '--header' in sys.argv:
        write_header(table, LENGTH)


if __name__ == '__main__':
    main()
