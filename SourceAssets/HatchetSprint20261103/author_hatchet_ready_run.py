"""Dual-hatchet sprint-ready run set "HatchetDualSprintReady" (2026-11-03).

User 2026-11-03 (third request): "双持从普通到触发冲刺攻击的状态按待机状态手势进行，触发冲刺攻击状态时左手按原来弯刀冲刺攻击奔跑
的姿势，右手再往上方举起一些" -- the dual-wield transition from normal to the sprint-ready state starts from the idle hand
gesture; while ready, the left hand follows the original kukri sprint-run arm and the right hand raises a bit higher than
the last version.

Three clips, the sword's sprint pattern (SprintEnter / SprintLoop / SprintExit):
  HatchetDualSprintEnter  0.30 s  dual hold (DualIdle frame 0) -> raised ready; the left arm leaves the hold into the run
  HatchetDualSprintReady  80/120 s loop  right hand holds the hatchet raised (higher than before), edge forward; the left
                                 arm is the dual run's left arm at the same phase (the original kukri sprint carry)
  HatchetDualSprintExit   0.25 s  raised ready + run left arm -> dual hold
The right hand's hold comes from author_dual_sprint_right_arm.RAISE (solved on the combo rig).

User 2026-11-04: "触发冲刺攻击奔跑时右手动画匹配左手的摆动频率和幅度" -- in the ready loop the raised right fist swings
like the left one.  The right swing is the left fist's measured stride in A_Kukri_DualRun (grip offset and rotation from
the stride mean), mirrored onto the right side and half a stride later (the arms alternate as in a run; the twice-per-
stride step bob stays together): the same screen path about the raised grip, so both fists travel as far on screen
(SWING_PHASE, ReadySet.right_swing).
(The sprint before the ready keeps the dual hold/walk carry at runtime -- KukriWeaponComponent::LocomotionClip.)

Run:  python author_hatchet_ready_run.py [--preview] [--header]
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
import author_dual_sprint_right_arm as S  # noqa: E402  (solves the raised right-hand key)
import author_hatchet_chop as C  # noqa: E402
sys.path.insert(0, str(P.parent / 'DualKukriIdle20261025'))
from dual_rig import DualRig, F, ROT_X180  # noqa: E402
from kmath import T, qmat, qfrommat, mesh_to_cam, cam_to_mesh, qslerp  # noqa: E402
from kukri_rig import ndc, TAN, ASPECT  # noqa: E402

FPS = 120
ENTER = 'HatchetDualSprintEnter'
LOOP = 'HatchetDualSprintReady'
EXIT = 'HatchetDualSprintExit'
LENGTH = 80.0 / 120.0                # the dual run's cycle (A_Kukri_DualRun)
ENTER_SECONDS = 0.30
EXIT_SECONDS = 0.25
# The right fist's swing = the dual run's left fist's, half a stride later (alternating arms): the same screen path,
# mirrored (ReadySet.right_swing).
SWING_PHASE = 0.5
OUT = P / 'Clips'
WORK = P / 'WorkReady'
PREVIEWS = P / 'PreviewsReady'
HEADER = P.parents[1] / 'Source' / 'FPSGAME' / 'Weapons' / 'Kukri' / 'HatchetReadyRhythm.h'
DUAL = P.parent / 'DualKukriIdle20261025'


def smooth(a, b, x):
    u = min(max((x - a) / (b - a), 0.0), 1.0)
    return u * u * (3 - 2 * u)


def load_clip(name):
    return json.loads((DUAL / 'Clips' / (name + '.json')).read_text('utf-8'))


def frame_local(data, i):
    fr = data['frames'][i % len(data['frames'])]
    return {b: T(np.array(v[0]), np.array(v[1]), np.array(v[2])) for b, v in fr.items()}


def virtual_hand(D, world):
    """The left fist's grip frame expressed as the virtual right arm's (mirrored space)."""
    hl = world['hand_l']
    hv = T(F @ (hl.p - D.left_shift), qfrommat(ROT_X180 @ qmat(hl.q)), D.R.base['hand_r'].s)
    K = D.R.hand_rel.inverse() * hv
    return T(K.p, K.q, (1, 1, 1))


def blend_local(a, b, w):
    out = {}
    for n in a:
        qa, qb = a[n].q, b[n].q
        qb = qb if np.dot(qa, qb) >= 0 else -qb
        out[n] = T(a[n].p + (b[n].p - a[n].p) * w, qslerp(qa, qb, w), a[n].s + (b[n].s - a[n].s) * w)
    return out


class ReadySet:
    def __init__(self):
        self.K_raise, _ = S.ready_frame()      # the raised right-hand hold (higher than the attack's trigger key)
        self.chop = C.ChopClip()               # stance clavicle + the left idle target
        self.R = self.chop.R
        self.D = DualRig()
        D, R = self.D, self.D.R
        self.R = R
        self.idle_local, idle_world = load_frame = None, None
        self.idle_local, idle_world = self.load('DualIdle', 0)
        self.run_data = load_clip('DualRun')
        self.K_left0 = virtual_hand(D, idle_world)
        self.E_right0 = idle_world['lowerarm_r'].p
        self.E_left0 = F @ (idle_world['lowerarm_l'].p - D.left_shift)
        # the dual hold's right grip (the enter/exit start and end)
        self.K_right0 = T(idle_world['WPN_root'].p, idle_world['WPN_root'].q, (1, 1, 1))
        self.swing, left_depth = self.left_swing_table()
        raised = mesh_to_cam(self.K_raise.p)
        self.raise_ndc, self.raise_depth = np.array(ndc(raised)), float(raised[0])
        self.depth_scale = self.raise_depth / left_depth

    def left_swing_table(self):
        """The dual run's left fist over one stride, one entry per clip frame: (grip screen offset from the stride mean,
        NDC; grip depth offset, cm; grip rotation relative to the mean orientation, mesh matrix).  Also returns the mean
        grip depth (cm)."""
        D = self.D
        ns, ds, ms = [], [], []
        for i in range(int(round(LENGTH * FPS))):
            K = D.left_kukri(virtual_hand(D, self.run_world(i / FPS)))
            c = mesh_to_cam(K.p)
            ns.append(np.array(ndc(c)))
            ds.append(float(c[0]))
            ms.append(qmat(K.q))
        n0, d0 = np.mean(ns, axis=0), float(np.mean(ds))
        u, _, vt = np.linalg.svd(np.sum(ms, axis=0))
        m0 = u @ np.diag([1.0, 1.0, np.linalg.det(u @ vt)]) @ vt
        return [(n - n0, d - d0, m @ m0.T) for n, d, m in zip(ns, ds, ms)], d0

    def right_swing(self, t):
        """The right fist's swing at loop time t: the left fist's, mirrored onto the right side and SWING_PHASE of a
        stride later -- the same screen path (NDC offsets, x mirrored) about the raised grip, the depth pump scaled by the
        grip depth ratio, the rotation mirrored (F).  Returns (grip position, mesh cm; rotation delta quaternion, mesh)."""
        n = len(self.swing)
        x = ((t / LENGTH + SWING_PHASE) % 1.0) * n
        i = int(np.floor(x)) % n
        f = float(x - np.floor(x))
        (na, da, ma), (nb, db, mb) = self.swing[i], self.swing[(i + 1) % n]
        dn = na + (nb - na) * f
        depth = self.raise_depth + (da + (db - da) * f) * self.depth_scale
        sx, sy = self.raise_ndc[0] - dn[0], self.raise_ndc[1] + dn[1]
        p = cam_to_mesh(np.array([depth, sx * depth * TAN * ASPECT, -sy * depth * TAN]))
        qa, qb = qfrommat(F @ ma @ F), qfrommat(F @ mb @ F)
        qb = qb if np.dot(qa, qb) >= 0 else -qb
        return p, qslerp(qa, qb, f)

    def load(self, clip, i):
        data = load_clip(clip)
        local = frame_local(data, i)
        return local, self.D.R.rig.world(local)

    def run_world(self, t):
        data = self.run_data
        n = len(data['frames']) - 1
        x = (t / LENGTH) * n
        i = int(np.floor(x)) % n
        f = x - np.floor(x)
        a, b = frame_local(data, i), frame_local(data, min(i + 1, n))
        return self.D.R.rig.world(blend_local(a, b, float(f)))

    def assemble(self, K_right, w_right, run_t, left_w):
        """Right arm from the raised key (weight w_right, else the dual hold), left arm = dual run at run_t blended with
        the hold by left_w (0 = hold, 1 = run).  Both arms solved together and the left chain mirrored, as in the dual rig."""
        D, R = self.D, self.R
        K = T(self.K_right0.p + (K_right.p - self.K_right0.p) * w_right, qslerp(self.K_right0.q, K_right.q, w_right),
              (1, 1, 1))
        Kl0 = T(self.K_left0.p, self.K_left0.q, (1, 1, 1))
        R.twist_memory = self.mem_right
        world, diag = R.pose(K, left_target_cam=C.IDLE_L, clav_r=self.chop.clav, pole_r=self.E_right0, pole_r_weight=0.0)
        self.right_diag = diag['right']
        self.mem_right = dict(R.twist_memory)
        R.twist_memory = self.mem_left
        world_v, dv = R.pose(Kl0, pole_r=self.E_left0, pole_r_weight=1.0)
        self.mem_left = dict(R.twist_memory)
        local = R.base_local
        for n in D.left_chain:
            src = world_v[n[:-2] + '_r']
            par = D.parent[n]
            world[n] = T(world[par].point(local[n].p), qfrommat(ROT_X180 @ qmat(src.q)), src.s)
        # the left arm: the dual run's own left chain, blended in from the hold.  Start from the SOLVED pose's locals
        # (R.base_local would throw the right arm back to the stance and separate it from the raised hatchet), then
        # overwrite only the left chain.
        if left_w > 1e-4:
            rw = self.run_world(run_t)
            hold = self.idle_local
            runl = R.rig.localize(rw)
            local = R.rig.localize(world)
            for n in D.left_chain:
                if n in runl:
                    a = hold[n]
                    b = runl[n]
                    qb = b.q if np.dot(a.q, b.q) >= 0 else -b.q
                    local[n] = T(a.p + (b.p - a.p) * left_w, qslerp(a.q, qb, left_w), a.s + (b.s - a.s) * left_w)
            world = R.rig.world(local)
            D.set_weapon(world, K)
        b = R.base
        world['ik_hand_l'] = b['ik_hand_l'].relative_to(b['hand_l']) * world['hand_l']
        self.world = world
        return world

    def diag(self, K):
        eye = mesh_to_cam(K.point([0.0, 0.0, 23.5]))
        return dict(eye=[round(float(x), 3) for x in ndc(eye)], grip=[round(float(v), 3) for v in ndc(mesh_to_cam(K.p))])

    # ---------------------------------------------------------------- clips
    def loop_K(self, t):
        p, dq = self.right_swing(t)
        return T(p, qfrommat(qmat(dq) @ qmat(self.K_raise.q)), (1, 1, 1))

    def enter(self):
        """Dual hold (idle hand gesture) -> the ready loop's first frame."""
        frames, diags, prev_q = [], [], None
        n = int(round(ENTER_SECONDS * FPS))
        for i in range(n + 1):
            u = i / n
            w = float(smooth(0.0, 1.0, u))
            world = self.assemble(self.loop_K(0.0), w, 0.0, w)
            frames.append(self.snap(world, prev_q))
            prev_q = {b: v[1] for b, v in self.last.items()}
            diags.append(dict(t=round(i / FPS, 4), w=round(w, 3)))
        return frames, diags

    def loop(self):
        frames, diags, prev_q = [], [], None
        n = int(round(LENGTH * FPS))
        for i in range(n + 1):
            t = 0.0 if i == n else i / FPS
            K = self.loop_K(t)
            world = self.assemble(K, 1.0, t, 1.0)
            frames.append(self.snap(world, prev_q))
            prev_q = {b: v[1] for b, v in self.last.items()}
            dr = self.right_diag
            Kl = self.D.left_kukri(virtual_hand(self.D, world))
            diags.append(dict(t=round(t, 4), eye=[round(float(x), 3) for x in ndc(mesh_to_cam(K.point([0.0, 0.0, 23.5])))],
                              grip=[round(float(x), 3) for x in ndc(mesh_to_cam(K.p))],
                              left_grip=[round(float(x), 3) for x in ndc(mesh_to_cam(Kl.p))],
                              reach=round(float(dr['reach']), 3), twist=round(float(dr['twist_deg']), 1),
                              wrist=round(float(dr['wrist_deg']), 1)))
        return frames, diags

    def exit(self):
        """The ready loop's first frame -> dual hold."""
        frames, diags, prev_q = [], [], None
        n = int(round(EXIT_SECONDS * FPS))
        for i in range(n + 1):
            u = i / n
            w = 1.0 - float(smooth(0.0, 1.0, u))
            world = self.assemble(self.loop_K(0.0), w, 0.0, w)
            frames.append(self.snap(world, prev_q))
            prev_q = {b: v[1] for b, v in self.last.items()}
            diags.append(dict(t=round(i / FPS, 4), w=round(w, 3)))
        return frames, diags

    def snap(self, world, prev_q):
        R = self.R
        local = R.rig.localize(world)
        keys = {}
        for b in R.rig.names:
            tr = local[b]
            q = tr.q.copy()
            if prev_q is not None and np.dot(q, prev_q[b]) < 0:
                q = -q
            keys[b] = (tr.p, q, tr.s)
        self.last = keys
        return {b: [list(map(float, v[0])), list(map(float, v[1])), list(map(float, v[2]))] for b, v in keys.items()}


def write_clip(name, frames, diags, length, loop):
    OUT.mkdir(parents=True, exist_ok=True)
    data = dict(name=name, fps=FPS, length=length, loop=loop, bones=list(frames[0].keys()), frames=frames, diagnostics=diags)
    (OUT / (name + '.json')).write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
    print('%-26s %.3f s  %d frames  loop=%s' % (name, length, len(frames), loop), flush=True)


def write_header():
    text = f'''#pragma once

#include "CoreMinimal.h"

// GENERATED by SourceAssets/HatchetSprint20261103/author_hatchet_ready_run.py -- do not edit by hand.
/**
 * 双持碳钢战斧「冲刺攻击就绪」奔跑姿势（2026-11-03，11-04 右手摆动）。冲刺未就绪时保持双持待机移动姿态，就绪时：
 *  - {ENTER}（{ENTER_SECONDS:.2f} s）：从双持待机手势起手，右手举斧，左手离开握姿进入跑步摆臂；
 *  - {LOOP}（80/120 s 循环）：右手举斧在准星右上方、刃口向前，左手是原弯刀冲刺跑姿的摆臂，
 *    右手按左手的摆动镜像、错开半步摆动（同频、屏幕上同幅）；
 *  - {EXIT}（{EXIT_SECONDS:.2f} s）：收回双持待机手势。
 * 冲刺攻击本身不变（仍是原来的双手跳劈）。就绪条件与 KukriDashRhythm / DashReadyFraction 相同。
 */
namespace HatchetReadyRhythm
{{
    inline const TCHAR* EnterClip=TEXT("/Game/Weapons/TacticalHatchet20261101/Animations/A_TacticalHatchet_DualSprintEnter.A_TacticalHatchet_DualSprintEnter");
    inline const TCHAR* Clip=TEXT("/Game/Weapons/TacticalHatchet20261101/Animations/A_TacticalHatchet_DualSprintReady.A_TacticalHatchet_DualSprintReady");
    inline const TCHAR* ExitClip=TEXT("/Game/Weapons/TacticalHatchet20261101/Animations/A_TacticalHatchet_DualSprintExit.A_TacticalHatchet_DualSprintExit");
    inline constexpr float EnterSeconds={ENTER_SECONDS:.3f}f;
    inline constexpr float Seconds={LENGTH:.6f}f;
    inline constexpr float ExitSeconds={EXIT_SECONDS:.3f}f;
}}
'''
    HEADER.write_bytes(text.encode('utf-8'))
    print('header ->', HEADER)


def author(preview=False):
    clip = ReadySet()
    clip.mem_left, clip.mem_right = {}, {}
    fe, de = clip.enter()
    clip.mem_left, clip.mem_right = {}, {}
    fl, dl = clip.loop()
    clip.mem_left, clip.mem_right = {}, {}
    fx, dx = clip.exit()
    write_clip(ENTER, fe, de, ENTER_SECONDS, False)
    write_clip(LOOP, fl, dl, LENGTH, True)
    write_clip(EXIT, fx, dx, EXIT_SECONDS, False)
    span = lambda k, j: round(max(d[k][j] for d in dl) - min(d[k][j] for d in dl), 3)
    summary = dict(loop=LOOP, enter=ENTER, exit=EXIT, seconds=[ENTER_SECONDS, LENGTH, EXIT_SECONDS],
                   head_eye=dl[len(dl) // 2]['eye'] if dl else None,
                   swing=dict(phase=SWING_PHASE, depth_scale=round(clip.depth_scale, 3),
                              right_grip_ndc_span=[span('grip', 0), span('grip', 1)],
                              left_grip_ndc_span=[span('left_grip', 0), span('left_grip', 1)],
                              head_ndc_y=[min(d['eye'][1] for d in dl), max(d['eye'][1] for d in dl)],
                              reach=[min(d['reach'] for d in dl), max(d['reach'] for d in dl)],
                              twist=[min(d['twist'] for d in dl), max(d['twist'] for d in dl)],
                              wrist_max=max(d['wrist'] for d in dl)))
    print('ready set', json.dumps(summary), flush=True)
    (P / 'clips.json').write_text(json.dumps({'clips': {LOOP: dict(summary, source='author_hatchet_ready_run.py')}},
                                             ensure_ascii=False, indent=2), encoding='utf-8')
    previews = {}
    if preview:
        clip.mem_left, clip.mem_right = {}, {}
        for k in range(int(round(LENGTH * 30))):
            t = k / 30.0
            K = clip.loop_K(t)
            world = clip.assemble(K, 1.0, t, 1.0)
            # the off-hand hatchet on the swinging left fist (the runtime's constant grip on hand_l), not a fixed pose
            previews['%s_%04d' % (LOOP, k)] = (world, K, clip.D.left_kukri(virtual_hand(clip.D, world)))
    return clip, previews


BLENDER = r"E:\Program Files\Blender Foundation\Blender 5.1\blender.exe"


def render_previews(previews, width=960):
    import cv2
    frames_dir = WORK / 'frames'
    frames_dir.mkdir(parents=True, exist_ok=True)
    for old in frames_dir.glob('*.png'):
        old.unlink()
    poses = {'poses': {name: {'bones': {b: t.pack() for b, t in world.items()}, 'kukri': K.pack(), 'kukri_left': Kl.pack()}
                       for name, (world, K, Kl) in previews.items()}}
    (WORK / 'previews.json').write_text(json.dumps(poses), encoding='utf-8')
    res = subprocess.run([BLENDER, '-b', '--factory-startup', '--python', str(P.parent / 'HatchetEquip20261101' / 'render_hatchet_preview.py'),
                          '--', str(WORK / 'previews.json'), str(frames_dir), str(width)],
                         capture_output=True, text=True, encoding='utf-8', errors='replace')
    if res.returncode != 0 or 'Traceback' in res.stdout:
        print(res.stdout[-3000:], res.stderr[-3000:])
        raise RuntimeError('preview render failed')
    imgs = [cv2.imread(str(frames_dir / (name + '.png'))) for name in sorted(previews)]
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    cells = [cv2.resize(im, (480, 270), interpolation=cv2.INTER_AREA) for im in imgs]
    while len(cells) % 4:
        cells.append(np.zeros_like(cells[0]))
    rows = [np.hstack(cells[k:k + 4]) for k in range(0, len(cells), 4)]
    for s in range(0, len(rows), 4):
        cv2.imwrite(str(PREVIEWS / ('sheet_%d.jpg' % (s // 4))), np.vstack(rows[s:s + 4]), [cv2.IMWRITE_JPEG_QUALITY, 82])
    print('previews ->', PREVIEWS)


if __name__ == '__main__':
    clip, previews = author(preview='--preview' in sys.argv)
    if '--header' in sys.argv:
        write_header()
    if previews:
        render_previews(previews)
