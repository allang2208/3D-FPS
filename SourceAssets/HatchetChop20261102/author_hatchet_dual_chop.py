"""Dual hatchet combo stage 3 "HatchetDualAttack3": both hatchets chop down together (2026-11-02).

User 2026-11-02: with two hatchets, the last combo hit follows the single-hatchet chop -- both hands at once, from above
down.  It replaces the kukri pair's double thrust (DualAttack3) for a hatchet pair only.

Gameplay clock: the double thrust's, unchanged (KukriRhythm::DualThrust*: 246/120 s, no tempo curve, contact 0.54-0.72,
impact 0.60, click buffer 0.84, the forward stride 0.24-0.60), so the server's paired receipts and windows stay valid.
Motion: the single chop (author_hatchet_chop.py keys, solved frames) retimed so it plays in the same real time up to the
impact (its stab tempo integrated at the base attack speed, the impact on 0.60), the recovery stretched to the longer
clip.  Right hand = the single chop; left hand = the same chop solved as a virtual right arm in mirrored space
(DualKukriIdle20261025/dual_rig.py: left bones = ROT_X180 x the virtual right's, the off-hand hatchet the mirror on
hand_l).  Per key the fists sit SPREAD_KEYS cm to their own sides (a little inside the single chop through the raise, so
both stay in the top corners; SPREAD out from the blow on, so the heads land side by side ~10 cm apart) and the left one
LEFT_* nearer and lower.  The clip starts and ends on the dual hold (DualIdle frame 0, the heads crossed 3.5 cm apart),
blended in local space; leaving and re-entering it the heads are kept apart in depth (UNCROSS, probe_*cross.py).
Head/handle clearance is printed (min_gap_cm).

Run:  python author_hatchet_dual_chop.py [--preview] [--header]
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

P = Path(__file__).resolve().parent
DUAL = P.parent / 'DualKukriIdle20261025'
sys.path.insert(0, str(P))
import author_hatchet_chop as C  # noqa: E402  (puts Kukri20261020 and HatchetEquip20261101 on the path)
sys.path.insert(0, str(DUAL))
from dual_rig import DualRig, F, ROT_X180  # noqa: E402
from kukri_rig import ndc, TIP, BLADE_BASE  # noqa: E402
from kmath import T, mesh_to_cam, cam_to_mesh, qmat, qfrommat, qslerp  # noqa: E402
from author_hatchet_equip import smoothness, smooth  # noqa: E402

FPS = 120
CLIP = 'HatchetDualAttack3'
LENGTH = 246.0 / 120.0               # KukriRhythm::DualThrustSeconds
STRIKE_AT = 0.60                     # KukriRhythm::DualThrustStrikeAt
CONTACT = (0.54, 0.72)
OUT = P / 'Clips'
WORK = P / 'WorkDual'
PREVIEWS = P / 'PreviewsDual'
HEADER = P.parents[1] / 'Source' / 'FPSGAME' / 'Weapons' / 'Kukri' / 'HatchetDualChopRhythm.h'
SPREAD = 9.0                         # cm: each fist further out to its own side through the chop
# Per single-chop key (author s): the raise keeps the fists a little inside the single chop's (it already sits in the
# top corner -- further out both fists leave the frame), the blow fans them out so the heads land side by side.
SPREAD_KEYS = {0.080: 4.5, 0.160: -1.0, 0.250: -2.5, 0.300: -2.5, 0.335: 1.0, 0.352: 5.5}   # 0.08: uncross the hold's heads wide
LEFT_NEAR, LEFT_LOW = 1.0, 1.0       # cm: the left fist a touch nearer and lower (two hands, not a mirror image)
UNCROSS = 3.0                        # cm: the hold crosses the heads (left one nearer); leaving and re-entering it the
                                     # left fist comes this much nearer, the right this much further (WorkDual/probe_uncross.py)
BLEND_IN = (0.0, 0.14)               # local-space blend from the dual hold (author s)
BLEND_OUT = (LENGTH - 0.30, LENGTH - 0.06)
END_KEY = LENGTH - 0.10              # the chop's own stance key lands here (then the hold blend finishes it)
CAMERA_GAIN = 1.15                   # two hatchets land: a little heavier than the single chop
HEAD_SAMPLE = [np.array(v) for v in ([4.0, 0.0, 30.9], [16.35, 0.0, 27.0], [16.0, 0.0, 19.0], [-4.5, 0.0, 30.0],
                                     [-4.5, 0.0, 22.0], [6.0, 0.0, 16.5], [8.0, 0.0, 23.0], [0.0, 0.0, 12.0])]

# FStrike for the pair: At = the double thrust's; a miss stops 0.05 s, the accent nods down harder than the single chop,
# a hit presses both down.  Hit-stop x2.6 / jolt x1.6 / roll rattle 1.8 (double thrust x2.4 / x1.6 / 2.0).
STRIKE = ('.60f', '.050f', '2.2f', '2.5f', '-2.0f', '0.f', '.6f', '0.f', '-1.8f', 'true')
HIT_STOP_SCALE, IMPACT_SCALE, HIT_ROLL = 2.6, 1.6, 1.8
RIFT_STRENGTH, RIFT_DISSOLVE, RIFT_DRIFT = 0.120, 0.22, 70.0

# ---------------------------------------------------------------- clock: single chop author time -> dual author time
def _single_real():
    ts = np.linspace(0.0, C.LENGTH, 4001)
    real = np.zeros_like(ts)
    for i in range(1, len(ts)):
        mid = 0.5 * (ts[i] + ts[i - 1])
        real[i] = real[i - 1] + (ts[i] - ts[i - 1]) / (C.PLAY_RATE * C.tempo(mid))
    return ts, real


_TS, _REAL = _single_real()
_R_AT = float(np.interp(C.STAGE_AT, _TS, _REAL))
SHIFT = STRIKE_AT - _R_AT * C.PLAY_RATE                          # the impacts coincide
K_POST = (END_KEY - STRIKE_AT) / ((_REAL[-1] - _R_AT) * C.PLAY_RATE)   # the recovery stretched to the dual clip


def u_of_t(t):
    r = float(np.interp(t, _TS, _REAL))
    if t <= C.STAGE_AT:
        return max(0.0, r * C.PLAY_RATE + SHIFT)
    return STRIKE_AT + (r - _R_AT) * C.PLAY_RATE * K_POST


_U = np.array([u_of_t(t) for t in _TS])


def t_of_u(u):
    return float(np.interp(u, _U, _TS))


# ---------------------------------------------------------------- the dual hold (DualIdle frame 0)
def load_frame(clip, i, R):
    data = json.loads((DUAL / 'Clips' / (clip + '.json')).read_text('utf-8'))
    fr = data['frames'][i if i >= 0 else len(data['frames']) + i]
    local = {b: T(np.array(v[0]), np.array(v[1]), np.array(v[2])) for b, v in fr.items()}
    return local, R.rig.world(local)


def virtual_hand(D, world):
    """The left fist's grip frame expressed as the virtual right arm's (mirrored space)."""
    hl = world['hand_l']
    hv = T(F @ (hl.p - D.left_shift), qfrommat(ROT_X180 @ qmat(hl.q)), D.R.base['hand_r'].s)
    K = D.R.hand_rel.inverse() * hv
    return T(K.p, K.q, (1, 1, 1))


def shifted(K, dy=0.0, dx=0.0, dz=0.0):
    return T(K.p + cam_to_mesh(np.array([dx, dy, dz])), K.q, (1, 1, 1))


class DualChopClip:
    def __init__(self):
        self.chop = C.ChopClip()
        self.D = DualRig()
        D, R = self.D, self.D.R
        self.R = R
        self.idle_local, idle_world = load_frame('DualIdle', 0, R)
        K_right0 = T(idle_world['WPN_root'].p, idle_world['WPN_root'].q, (1, 1, 1))
        K_left0 = virtual_hand(D, idle_world)
        self.E_right0 = idle_world['lowerarm_r'].p
        self.E_left0 = F @ (idle_world['lowerarm_l'].p - D.left_shift)
        ch = self.chop
        us, right, left, holds = [0.0], [K_right0], [K_left0], [True]
        n = len(ch.key_times)
        for i in range(1, n - 2):                   # the chop's own keys between its stance ends
            t, K, hold = ch.key_times[i], ch.key_frames[i], ch.key_holds[i]
            if ch.key_times[i] >= 1.10:             # 'blend' / stance: replaced by the dual hold below
                continue
            us.append(u_of_t(t))
            s = SPREAD_KEYS.get(round(t, 3), SPREAD)
            x = UNCROSS if i == 1 else 0.0                        # leaving the hold
            right.append(shifted(K, dy=s, dx=x))
            left.append(shifted(K, dy=s, dx=-LEFT_NEAR - x, dz=-LEFT_LOW))
            holds.append(hold)
        # back into the crossed hold from below: the right head comes in nearer, the left further and under it, then both
        # settle (WorkDual/probe_recross.py: min gap 2.9 cm vs the hold's own 3.5)
        for u, kr, kl in ((END_KEY - 0.14, shifted(K_right0, dx=-UNCROSS), shifted(K_left0, dx=UNCROSS, dz=-4.0)),
                          (END_KEY, K_right0, K_left0), (LENGTH, K_right0, K_left0)):
            us.append(u); right.append(kr); left.append(kl); holds.append(False)
        holds[-1] = True
        self.keys_u, self.hold_flags = us, holds
        self.mem_left, self.mem_right = {}, {}
        self.right = C.HoldTrack(us, right, holds)
        self.left = C.HoldTrack(us, left, holds)
        print('  dual keys (u): %s' % ', '.join('%.3f' % u for u in us))

    def pole(self, u):
        a = 1.0 - smooth((u - 0.02) / 0.16)
        b = smooth((u - (END_KEY - 0.30)) / 0.25)
        return max(a, b)

    def sample(self, u):
        D, R = self.D, self.R
        Kr, Kv = self.right(u), self.left(u)
        w = self.pole(u)
        # each arm keeps its own forearm-twist unwrap memory (kukri_rig unwraps against the previous solve)
        R.twist_memory = self.mem_left
        world_v, dv = R.pose(Kv, pole_r=self.E_left0, pole_r_weight=w)
        self.mem_left = dict(R.twist_memory)
        R.twist_memory = self.mem_right
        world, dr = R.pose(Kr, pole_r=self.E_right0, pole_r_weight=w)
        self.mem_right = dict(R.twist_memory)
        D.set_weapon(world, Kr)
        local = R.base_local
        for n in D.left_chain:
            src = world_v[n[:-2] + '_r']
            par = D.parent[n]
            world[n] = T(world[par].point(local[n].p), qfrommat(ROT_X180 @ qmat(src.q)), src.s)
        b = R.base
        world['ik_hand_l'] = b['ik_hand_l'].relative_to(b['hand_l']) * world['hand_l']
        K_l = D.left_kukri(Kv)
        # clearance between the two hatchets (head and upper handle points)
        pr = [Kr.point(v) for v in HEAD_SAMPLE]
        pl = [K_l.point(v) for v in HEAD_SAMPLE]
        gap = min(float(np.linalg.norm(a - c)) for a in pr for c in pl)
        r, lv = dr['right'], dv['right']
        eye = mesh_to_cam(Kr.point([0.0, 0.0, 23.5]))
        d = dict(t=round(u, 4), twist=round(r['twist_deg'], 1), ext=round(r['ext'], 1), uln=round(r['uln'], 1),
                 wrist=round(r['wrist_deg'], 1), reach=round(r['reach'], 3), ltwist=round(lv['twist_deg'], 1),
                 lwrist=round(lv['wrist_deg'], 1), grip=[round(float(x), 3) for x in dr['grip_ndc']],
                 lgrip=[round(float(x), 3) for x in ndc(mesh_to_cam(K_l.p))], gap=round(gap, 1),
                 eye=[round(float(x), 3) for x in ndc(eye)], eye_cam=[float(x) for x in eye],
                 leye=[round(float(x), 3) for x in ndc(mesh_to_cam(K_l.point([0.0, 0.0, 23.5])))],
                 fist_cam=[float(x) for x in mesh_to_cam(Kr.p)], axe_q=[float(x) for x in Kr.q])
        return world, Kr, K_l, d


def blend_local(a, b, w):
    out = {}
    for n in a:
        qa, qb = a[n].q, b[n].q
        qb = qb if np.dot(qa, qb) >= 0 else -qb
        out[n] = T(a[n].p + (b[n].p - a[n].p) * w, qslerp(qa, qb, w), a[n].s + (b[n].s - a[n].s) * w)
    return out


# ---------------------------------------------------------------- presentation
def camera(u):
    """The single chop's curve on this clock (sampled at the matching single time), a touch heavier.  The pair is
    symmetric, so the single chop's lean with the right arm (yaw, roll) is dropped: pitch, FOV and push only."""
    if u >= LENGTH:
        return (0.0,) * 5
    v = np.array(C.camera(t_of_u(u))) * CAMERA_GAIN * np.array([1.0, 0.0, 0.0, 1.0, 1.0])
    return tuple(float(x) for x in v * (1.0 - smooth((u - (LENGTH - 0.25)) / 0.2)))


RIFT_U = (u_of_t(C.RIFT[0]), u_of_t(C.RIFT[1]))
SWING_SOUND = u_of_t(0.328)          # HatchetChopRhythm::Swing.SwingSound on this clock: the whoosh with the drive


def ribbons(clip):
    rows_r, rows_l = [], []
    for i in range(C.STATIONS):
        u = RIFT_U[0] + (RIFT_U[1] - RIFT_U[0]) * i / (C.STATIONS - 1)
        Kr, Kv = clip.right(u), clip.left(u)
        Kl = clip.D.left_kukri(Kv)
        rows_r.append([C.clamp_lens(Kr.point(C.RIBBON[0])), C.clamp_lens(Kr.point(C.RIBBON[1]))])
        rows_l.append([C.clamp_lens(Kl.point(C.RIBBON[0])), C.clamp_lens(Kl.point(C.RIBBON[1]))])
    return rows_r, rows_l


def write_header(clip):
    n = 62                                             # KukriRhythm::DualThrustSamples (30 Hz)
    rows = [camera(i / 30.0) for i in range(n)]
    arr = lambda k: ','.join('%.2ff' % (r[k] + 0.0) for r in rows).replace('-0.00f', '0.00f')
    fmt = lambda rr: ',\n        '.join('{%s}' % ','.join('{%.2ff,%.2ff,%.2ff}' % tuple(float(v) for v in p) for p in row)
                                       for row in rr)
    rr, rl = ribbons(clip)
    text = f'''#pragma once

#include "CoreMinimal.h"
#include "KukriRhythm.h"

// GENERATED by SourceAssets/HatchetChop20261102/author_hatchet_dual_chop.py -- do not edit by hand.
/**
 * 双持碳钢战斧三连击第三段：双手同时从上往下劈砍（clip "HatchetDualAttack3"，246/120 s，2026-11-02）。只替换双斧的第三段，
 * 双弯刀仍是双刺。时间轴与双刺完全一致（命中窗 0.54-0.72、打击时刻 0.60、缓冲 0.84、0.24-0.60 前冲 100 cm），服务端回执、
 * 命中校验沿用 KukriRhythm::DualThrust*；这里只换表现。
 * 动作 = 单持劈砍按真实时间对齐打击时刻（0.60），收势拉长到双刺时长；左手为右手在镜像空间的同一劈砍。举斧时两拳比单持略靠内，
 * 劈下时各向外 {SPREAD:.0f} cm，左拳再近 {LEFT_NEAR:.0f} cm、低 {LEFT_LOW:.0f} cm，两把斧并排落在准星两侧。首尾在局部空间衔接
 * 双持待机第 0 帧（两斧头交叉），离开和回到待机时两斧头前后错开 {UNCROSS:.0f} cm。
 * 镜头：单持劈砍曲线换到本时钟、×{CAMERA_GAIN:.2f}，左右对称所以只留俯仰、视场和前冲（去掉单持跟右臂的偏航和滚转）。
 * 挥砍音在 {SWING_SOUND:.3f}（斧头越过头顶）。打击时刻：挥空停 0.05 s、低头 2°、视场 +2.2°；命中顿帧 ×{HIT_STOP_SCALE:.1f}、
 * 冲击 ×{IMPACT_SCALE:.1f}、滚转抖动 {HIT_ROLL:.1f}，视模向下压 1.8 cm、整体往上顶；两把斧各一道剑气。
 */
namespace HatchetDualChopRhythm
{{
    inline const TCHAR* Clip=TEXT("/Game/Weapons/TacticalHatchet20261101/Animations/A_TacticalHatchet_DualAttack3.A_TacticalHatchet_DualAttack3");
    inline constexpr float Seconds=KukriRhythm::DualThrustSeconds;
    inline constexpr KukriRhythm::FStrike Strike={{{','.join(STRIKE)}}};
    static_assert(Strike.At==KukriRhythm::DualThrustStrikeAt&&Seconds==KukriRhythm::DualThrustSeconds,
        "the dual chop keeps the double thrust's gameplay clock (server receipts and windows)");
    inline constexpr float HitStopScale={HIT_STOP_SCALE:.2f}f, ImpactScale={IMPACT_SCALE:.2f}f, HitRoll={HIT_ROLL:.2f}f;
    inline constexpr float SwingSound={SWING_SOUND:.3f}f;     // local cue only: the whoosh as the heads come over the top
    inline constexpr KukriRhythm::FRift Rift={{{RIFT_U[0]:.3f}f,{RIFT_U[1]:.3f}f,{RIFT_STRENGTH:.3f}f,{RIFT_DISSOLVE:.2f}f,{RIFT_DRIFT:.1f}f}};

    inline constexpr int32 CameraSamples={n};
    inline constexpr float ChopPitch[CameraSamples]={{{arr(0)}}};
    inline constexpr float ChopYaw[CameraSamples]={{{arr(1)}}};
    inline constexpr float ChopRoll[CameraSamples]={{{arr(2)}}};
    inline constexpr float ChopFov[CameraSamples]={{{arr(3)}}};
    inline constexpr float ChopPush[CameraSamples]={{{arr(4)}}};
    inline float SampleChop(const float (&Curve)[CameraSamples],float Time)
    {{
        const float X=FMath::Clamp(Time*30.f,0.f,float(CameraSamples-1));
        const int32 I=FMath::Min(int32(X),CameraSamples-2);
        return FMath::Lerp(Curve[I],Curve[I+1],X-I);
    }}
    inline void Camera(float T,FRotator& Rotation,float& Fov,FVector* Location=nullptr)
    {{
        Rotation=FRotator(SampleChop(ChopPitch,T),SampleChop(ChopYaw,T),SampleChop(ChopRoll,T))*KukriRhythm::CameraScale;
        Fov=SampleChop(ChopFov,T)*KukriRhythm::CameraScale;
        if(Location)*Location=FVector(SampleChop(ChopPush,T)*KukriRhythm::CameraScale,0.f,0.f);
    }}

    /** Rift ribbons swept by the two heads over Rift.Start-Rift.End (viewmodel mesh space cm). */
    inline constexpr int32 Stations={C.STATIONS};
    inline constexpr float RibbonRight[Stations][2][3]={{
        {fmt(rr)}}};
    inline constexpr float RibbonLeft[Stations][2][3]={{
        {fmt(rl)}}};
}}
'''
    HEADER.write_bytes(text.encode('utf-8'))
    print('header ->', HEADER)


# ---------------------------------------------------------------- outputs
def author(preview=False):
    clip = DualChopClip()
    R = clip.R
    n = int(round(LENGTH * FPS))
    frames, diags, prev_q = [], [], None
    previews = {}
    real_us = set()
    if preview:
        u, k = 0.0, 0
        stopped = 0.0
        while u < LENGTH:
            real_us.add(round(u, 6))
            step = 1.0 / 60.0
            if u >= STRIKE_AT and stopped < 0.05:
                stopped += step
            else:
                u = min(LENGTH, u + step * C.PLAY_RATE)
        real_us.add(LENGTH)
    for i in range(n + 1):
        u = i / FPS
        world, Kr, Kl, d = clip.sample(u)
        local = R.rig.localize(world)
        if u < BLEND_IN[1]:
            local = blend_local(clip.idle_local, local, smooth((u - BLEND_IN[0]) / (BLEND_IN[1] - BLEND_IN[0])))
        elif u > BLEND_OUT[0]:
            local = blend_local(local, clip.idle_local, smooth((u - BLEND_OUT[0]) / (BLEND_OUT[1] - BLEND_OUT[0])))
        keys = {}
        for b in R.rig.names:
            t = local[b]
            q = t.q.copy()
            if prev_q is not None and np.dot(q, prev_q[b]) < 0:
                q = -q
            keys[b] = (t.p, q, t.s)
        prev_q = {b: v[1] for b, v in keys.items()}
        frames.append({b: [list(map(float, v[0])), list(map(float, v[1])), list(map(float, v[2]))] for b, v in keys.items()})
        diags.append(d)
    if preview:
        clip.mem_left, clip.mem_right = {}, {}
        for k, u in enumerate(sorted(real_us)):
            world, Kr, Kl, _ = clip.sample(u)
            local = R.rig.localize(world)
            if u < BLEND_IN[1]:
                local = blend_local(clip.idle_local, local, smooth((u - BLEND_IN[0]) / (BLEND_IN[1] - BLEND_IN[0])))
            elif u > BLEND_OUT[0]:
                local = blend_local(local, clip.idle_local, smooth((u - BLEND_OUT[0]) / (BLEND_OUT[1] - BLEND_OUT[0])))
            world = R.rig.world(local)
            K = T(world['WPN_root'].p, world['WPN_root'].q, (1, 1, 1))
            Kl = left_from_world(clip, world)
            previews['%s_%04d' % (CLIP, k)] = (world, K, Kl, camera(u))
    OUT.mkdir(parents=True, exist_ok=True)
    data = dict(name=CLIP, fps=FPS, length=n / FPS, loop=False, contact=list(CONTACT), strike=STRIKE_AT, bones=R.rig.names,
                frames=frames, diagnostics=diags)
    (OUT / (CLIP + '.json')).write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
    summary = dict(length=round(n / FPS, 4), frames=n + 1, max_reach=max(x['reach'] for x in diags),
                   twist=[min(x['twist'] for x in diags), max(x['twist'] for x in diags)],
                   ltwist=[min(x['ltwist'] for x in diags), max(x['ltwist'] for x in diags)],
                   wrist_max=max(x['wrist'] for x in diags), lwrist_max=max(x['lwrist'] for x in diags),
                   min_gap_cm=min(x['gap'] for x in diags if 0.3 < x['t'] < LENGTH - 0.3),
                   impact_eye=next(x['eye'] for x in diags if abs(x['t'] - STRIKE_AT) < 0.005),
                   impact_left_eye=next(x['leye'] for x in diags if abs(x['t'] - STRIKE_AT) < 0.005),
                   swing_sound=round(SWING_SOUND, 3), rift=[round(RIFT_U[0], 3), round(RIFT_U[1], 3)])
    print(CLIP, json.dumps(summary), flush=True)
    meta = json.loads((P / 'clips.json').read_text('utf-8')) if (P / 'clips.json').exists() else {'clips': {}}
    meta.setdefault('clips', {})[CLIP] = dict(summary, source='author_hatchet_dual_chop.py')
    (P / 'clips.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    for d in diags[::8]:
        print('  %.3f R twist %6.1f wrist %4.1f reach %.2f fist %-16s | L twist %6.1f wrist %4.1f fist %-16s | gap %5.1f eye %s' % (
            d['t'], d['twist'], d['wrist'], d['reach'], d['grip'], d['ltwist'], d['lwrist'], d['lgrip'], d['gap'], d['eye']))
    smoothness(diags)
    return clip, previews


def left_from_world(clip, world):
    """The off-hand hatchet as the game puts it: the mirror of the virtual right grip read back from hand_l."""
    Kv = virtual_hand(clip.D, world)
    return clip.D.left_kukri(Kv)


BLENDER = r"E:\Program Files\Blender Foundation\Blender 5.1\blender.exe"


def render_previews(previews, width=960):
    import cv2
    frames_dir = WORK / 'frames'
    frames_dir.mkdir(parents=True, exist_ok=True)
    for old in frames_dir.glob('*.png'):
        old.unlink()
    poses = {'poses': {name: {'bones': {b: t.pack() for b, t in world.items()}, 'kukri': K.pack(), 'kukri_left': Kl.pack(),
                              'camera': list(cam[:4])} for name, (world, K, Kl, cam) in previews.items()}}
    (WORK / 'previews.json').write_text(json.dumps(poses), encoding='utf-8')
    res = subprocess.run([BLENDER, '-b', '--factory-startup', '--python', str(C.EQUIP / 'render_hatchet_preview.py'), '--',
                          str(WORK / 'previews.json'), str(frames_dir), str(width)],
                         capture_output=True, text=True, encoding='utf-8', errors='replace')
    if res.returncode != 0 or 'Traceback' in res.stdout:
        print(res.stdout[-3000:], res.stderr[-3000:])
        raise RuntimeError('preview render failed')
    imgs = []
    for k, name in enumerate(sorted(previews)):
        im = cv2.imread(str(frames_dir / (name + '.png')))
        cv2.putText(im, '%.3f s' % (k / 60.0), (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        imgs.append(im)
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    h, w = imgs[0].shape[:2]
    for path, fps in ((PREVIEWS / 'hatchet_dual_chop_realtime.mp4', 60), (PREVIEWS / 'hatchet_dual_chop_slow4x.mp4', 15)):
        raw = WORK / ('raw_' + path.name)
        vw = cv2.VideoWriter(str(raw), cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
        for im in [imgs[0]] * (fps // 3) + imgs + [imgs[-1]] * (fps // 2):
            vw.write(im)
        vw.release()
        try:
            import imageio_ffmpeg
            subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-loglevel', 'error', '-i', str(raw), '-c:v', 'libx264',
                            '-pix_fmt', 'yuv420p', '-crf', '18', str(path)], check=True)
            raw.unlink()
        except Exception as exc:
            print('H.264 transcode skipped (%s); mp4v kept' % exc)
            raw.replace(path)
    cells = [cv2.resize(im, (480, 270), interpolation=cv2.INTER_AREA) for im in imgs[::2]]
    while len(cells) % 4:
        cells.append(np.zeros_like(cells[0]))
    rows = [np.hstack(cells[k:k + 4]) for k in range(0, len(cells), 4)]
    for s in range(0, len(rows), 4):
        cv2.imwrite(str(PREVIEWS / ('sheet_%d.jpg' % (s // 4))), np.vstack(rows[s:s + 4]), [cv2.IMWRITE_JPEG_QUALITY, 82])
    print('previews ->', PREVIEWS)


if __name__ == '__main__':
    clip, previews = author(preview='--preview' in sys.argv)
    if '--header' in sys.argv:
        write_header(clip)
    if previews:
        render_previews(previews)
