"""Two-handed sword guard V24, fitted to YouTube NTrzxPIXer4 (Kubold FPP Two Handed Sword) 1:49-1:52.

blender -b --factory-startup --python author_guard_v24.py -- [--long-grip] [--no-export]
Clips: A_RuneSword_Guard (0.46 s raise + 2.05 s breathing hold loop), A_RuneSword_GuardHit (0.75 s), A_RuneSword_GuardBreak
(0.45 s). The sword is placed so its blade base, blade screen angle and crossguard screen angle land where the reference
shows them under the game camera (75 deg vertical FOV, 16:9; viewmodel space = camera at the origin looking +Y, Z up).
Both hands keep the accepted idle grip on the hilt (WristLocked V4 idle, as the V85 inspect); arms use the V85 arm
solver (Arm.solve + roll_humerus) and the V9 forearm twist. Depth is the deepest the right arm reaches with its elbow
still bent: the reference holds a slimmer sword, so ours reads wider on screen at the same place.
Writes Export[/LongGrip]/A_RuneSword_<Clip>.fbx, authoring_v24[_long_grip].json, Work/preview_<variant>.blend.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

HERE = Path(__file__).resolve().parent
V85 = HERE.parent / 'InspectReverseV85'
sys.path.insert(0, str(V85))
import v85_setup  # noqa: E402
import v85_hand as Hd  # noqa: E402
from v85_arm import Arm  # noqa: E402

VARIANT = 'LongGrip' if '--long-grip' in sys.argv else 'Standard'
FPS = 120
K = json.loads((HERE / 'keys_guard_v24.json').read_text(encoding='utf-8'))
TANV, ASPECT = math.tan(math.radians(37.5)), 16.0 / 9.0
BLADE_BASE = Vector((0.0, 0.0, 0.10))     # WPN_root local: top of the 36 cm crossguard
GUARD_HALF = 0.15                         # along local X, for the crossguard screen angle
REACH_MAX = 0.93                          # right arm: elbow keeps a bend (soft clamp starts at 0.96)
ARM_LENGTH = 0.2777 + 0.2725
CLIPS = ('Guard', 'GuardHit', 'GuardBreak')


def ray(px, py):
    return Vector(((px / 960.0 - 1.0) * TANV * ASPECT, 1.0, (1.0 - py / 540.0) * TANV))


def project(p):
    return Vector(((p.x / (p.y * TANV * ASPECT) + 1.0) * 960.0, (1.0 - p.z / (p.y * TANV)) * 540.0))


def screen_angle(a, b):
    pa, pb = project(a), project(b)
    return math.degrees(math.atan2(-(pb.y - pa.y), pb.x - pa.x))


def pchip(ts, ys):
    n = len(ts)
    h = [ts[i + 1] - ts[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    for i in range(1, n - 1):
        if d[i - 1] * d[i] > 0.0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(t):
        if t <= ts[0]:
            return ys[0]
        if t >= ts[-1]:
            return ys[-1]
        i = max(k for k in range(n - 1) if ts[k] <= t)
        s = (t - ts[i]) / h[i]
        return ((2 * s ** 3 - 3 * s ** 2 + 1) * ys[i] + (s ** 3 - 2 * s ** 2 + s) * h[i] * m[i]
                + (-2 * s ** 3 + 3 * s ** 2) * ys[i + 1] + (s ** 3 - s ** 2) * h[i] * m[i + 1])
    return f

c = v85_setup.load(VARIANT)
rig, idle = c.rig, c.idle
SCALE = c.idle_scale['WPN_root']
W_IDLE = idle['WPN_root'].copy()
R_IDLE = W_IDLE.to_quaternion()
GRIP = {s: W_IDLE.inverted() @ idle['hand_' + s] for s in 'rl'}
SHOULDER = {s: idle['upperarm_' + s].translation.copy() for s in 'rl'}
# Local blade width (m) along WPN z, from the probe of the installed sword mesh (Work/probe_sword.json).
WIDTH = [(0.10, 0.104), (0.13, 0.102), (0.18, 0.098), (0.24, 0.097), (0.29, 0.078), (0.35, 0.076), (0.40, 0.074),
         (0.46, 0.071), (0.51, 0.069), (0.57, 0.066), (0.62, 0.063), (0.68, 0.061), (0.73, 0.057), (0.78, 0.037)]


def width_at(z):
    for (z0, w0), (z1, w1) in zip(WIDTH, WIDTH[1:]):
        if z <= z1:
            return w0 + (w1 - w0) * max(0.0, min(1.0, (z - z0) / (z1 - z0)))
    return WIDTH[-1][1]


def weapon(B, d, g):
    z = d.normalized()
    x = (g - z * g.dot(z)).normalized()
    y = z.cross(x)
    q = Matrix((x, y, z)).transposed().to_quaternion()
    loc = B - q @ Vector((BLADE_BASE.x * SCALE.x, BLADE_BASE.y * SCALE.y, BLADE_BASE.z * SCALE.z))
    return Matrix.LocRotScale(loc, q, SCALE)


def guard_axis(W):
    return (W.to_3x3() @ Vector((1.0, 0.0, 0.0))).normalized()


def roll_candidates(B, d, target):
    """Crossguard directions (perpendicular to the blade) whose screen angle matches target (mod 180)."""
    z = d.normalized()
    u = Vector((0.0, 0.0, 1.0)) - z * z.z
    if u.length < 1e-4:
        u = Vector((1.0, 0.0, 0.0)) - z * z.x
    u.normalize()
    v = z.cross(u)
    best = []
    for k in range(720):
        psi = math.radians(k * 0.5)
        g = u * math.cos(psi) + v * math.sin(psi)
        a = screen_angle(B - g * GUARD_HALF, B + g * GUARD_HALF)
        err = abs((a - target + 90.0) % 180.0 - 90.0)
        best.append((err, g))
    best.sort(key=lambda e: e[0])
    first = best[0][1]
    second = next(g for e, g in best if g.dot(first) < -0.5)
    return first, second


def edge_on_candidates(B, d):
    """Roll with the blade's width (and crossguard) along the line of sight at mid-blade: the edge faces the opponent
    and the viewer sees the 3.5 cm back edge. The reference sword is a slim rod; our 7-10 cm flat seen face-on reads
    2.6x wider at the same place, edge-on it reads about the same."""
    z = d.normalized()
    mid = B + z * 0.30
    v = mid.normalized()
    g = v - z * v.dot(z)
    if g.length < 1e-5:
        g = Vector((1.0, 0.0, 0.0)) - z * z.x
    g.normalize()
    return g, -g


def place(Bpx, angle, depth, tilt, guard, g_prev=None):
    """Weapon frame with its blade base on the screen point Bpx at depth (m), blade along the screen angle and
    receding by `tilt` (depth ratio 800 px further along the blade). guard: crossguard screen angle, or 'edge' for the
    edge-on roll."""
    B = ray(*Bpx) * depth
    a = math.radians(angle)
    E = ray(Bpx[0] + 800.0 * math.cos(a), Bpx[1] - 800.0 * math.sin(a)) * (depth * tilt)
    d = (E - B).normalized()
    if guard == 'carry':
        # No roll of its own: the previous key's crossguard carried onto the new blade direction (a knocked blade
        # turns about an axis across the blade, it does not spin in the hands).
        return weapon(B, d, (g_prev - d * g_prev.dot(d)).normalized())
    g1, g2 = edge_on_candidates(B, d) if guard == 'edge' else roll_candidates(B, d, guard)
    if g_prev is None:
        # The hold: the roll whose frame is the smaller turn from the idle grip (the other one flips the hands over).
        q1, q2 = weapon(B, d, g1).to_quaternion(), weapon(B, d, g2).to_quaternion()
        g = g1 if R_IDLE.rotation_difference(q1).angle <= R_IDLE.rotation_difference(q2).angle else g2
    else:
        g = g1 if g1.dot(g_prev) >= g2.dot(g_prev) else g2
    return weapon(B, d, g)


def tip_of(W):
    return (W @ c.rest['WPN_root'].inverted()) @ c.tip_bind


def pommel_of(W):
    return (W @ c.rest['WPN_root'].inverted()) @ c.pommel_bind


def reach(W, s):
    return ((W @ GRIP[s]).translation - SHOULDER[s]).length / ARM_LENGTH


def width_px(W, z):
    P = W @ Vector((0.0, 0.0, z))
    g = guard_axis(W)
    view = P.normalized()
    gp = g - view * g.dot(view)
    return width_at(z) * gp.length / (P.y * TANV) * 540.0


def screen_station(W, s_px):
    """Local z of the blade point s_px screen pixels from the blade base, for width comparisons."""
    B = project(W @ BLADE_BASE)
    for k in range(1, 141):
        z = 0.10 + k * 0.005
        if (project(W @ Vector((0.0, 0.0, z))) - B).length >= s_px:
            return z
    return None


HOLD = K['hold']
ROLL = HOLD.get('roll', HOLD['guard_angle'])
TARGET_RATIO = 85.0 / 60.0           # reference widths at 100 px and 800 px along the hold blade (README.md)


def solve_hold():
    best = None
    for i in range(61):
        depth = 0.20 + i * 0.005
        for j in range(21):
            tilt = 0.80 + j * 0.05
            W = place(HOLD['B'], HOLD['angle'], depth, tilt, ROLL)
            rr, rl = reach(W, 'r'), reach(W, 'l')
            hands = min((W @ GRIP[s]).translation.y for s in 'rl')
            if rr > REACH_MAX or rl > REACH_MAX or hands < 0.12 or pommel_of(W).y < 0.08:
                continue
            z1, z2 = screen_station(W, 100.0), screen_station(W, 800.0)
            if z1 is None or z2 is None:
                continue
            # The reference blade runs out through the top edge of the frame; ours must not end on screen.
            tip = project(tip_of(W))
            if tip.y > -40.0 and tip.x < 1960.0:
                continue
            ratio = width_px(W, z1) / max(1e-6, width_px(W, z2))
            score = depth * 10.0 - abs(ratio - TARGET_RATIO) - 0.01 * abs(width_px(W, z1) - 85.0)
            if best is None or score > best[0]:
                best = (score, depth, tilt, W, rr, rl, ratio, width_px(W, z1))
    if best is None:
        raise SystemExit('No reachable hold pose for the reference screen position')
    return best

score, HOLD_DEPTH, HOLD_TILT, W_HOLD_MEAN, HOLD_RR, HOLD_RL, HOLD_RATIO, HOLD_WIDTH = solve_hold()
G_HOLD = guard_axis(W_HOLD_MEAN)
WRIST_TARGET = 30.0


def grip_at(W, s, alpha):
    """Hand frame on the hilt turned by alpha degrees about the grip axis (WPN local Z): the fist slides round the
    handle, contact and closed fingers unchanged, so the wrist does not have to follow the blade's whole turn."""
    return W @ Matrix.Rotation(math.radians(alpha), 4, 'Z') @ GRIP[s]


def wrist_cost(W, s, alpha):
    arm = Arm(c.rest, c.idle, c.idle_scale)
    part, clamped = arm.solve(grip_at(W, s, alpha), s, key=s)
    return arm.wrist_bend(part, s), clamped


def best_alpha(W, s, ref, steps=25):
    """Grip turn with the least wrist bend, preferring small changes from ref (the previous key); reaction keys search
    only +-48 deg round the previous key so the fist never spins round the handle between two close keys."""
    def cost(a):
        bend, clamped = wrist_cost(W, s, a)
        return max(0.0, bend - WRIST_TARGET) * 4.0 + bend * 0.25 + abs(a - ref) * 0.12 + clamped * 4000.0
    a0 = min((ref + k * 6.0 for k in range(-steps, steps + 1)), key=cost)
    return min((a0 + k * 0.5 for k in range(-12, 13)), key=cost)
BR = HOLD['breath']
OMEGA = 2.0 * math.pi / BR['period']
PHI = math.acos(BR['start_dy_px'] / BR['dy_px'])


def hold_pose(tau):
    """Breathing hold: the blade base bobs on screen like the reference hook (period 2.05 s)."""
    px = (HOLD['B'][0] + BR['dx_px'] * math.sin(OMEGA * tau + PHI), HOLD['B'][1] + BR['dy_px'] * math.cos(OMEGA * tau + PHI))
    return place(px, HOLD['angle'], HOLD_DEPTH, HOLD_TILT, ROLL, G_HOLD)


W_HOLD0 = hold_pose(0.0)
R_HOLD0 = W_HOLD0.to_quaternion()
ALPHA_HOLD = {s: best_alpha(W_HOLD0, s, 0.0) for s in 'rl'}


def ndc_depth(p):
    q = project(p)
    return q.x, q.y, p.y


def frame_from(Bpx, depth, q):
    """Weapon frame from a blade-base screen point, its depth and an orientation."""
    B = ray(*Bpx) * depth
    return Matrix.LocRotScale(B - q @ Vector((BLADE_BASE.x * SCALE.x, BLADE_BASE.y * SCALE.y, BLADE_BASE.z * SCALE.z)),
                              q, SCALE)


def raise_pose(t):
    r = K['raise']
    ix, iy, idep = ndc_depth(W_IDLE @ BLADE_BASE)
    hx, hy, hdep = ndc_depth(W_HOLD0 @ BLADE_BASE)
    px_x, px_y = list(r['pos_x']), list(r['pos_y'])
    px_x[-1], px_y[-1] = 1.0, 1.0           # the raise ends exactly on the first hold frame
    fx, fy, fr = pchip(r['t'], px_x), pchip(r['t'], px_y), pchip(r['t'], [v if k < len(r['rot']) - 1 else 1.0
                                                                          for k, v in enumerate(r['rot'])])
    Bpx = (ix + (hx - ix) * fx(t), iy + (hy - iy) * fy(t))
    depth = idep + (hdep - idep) * fx(t)
    rel = R_IDLE.inverted() @ R_HOLD0
    if rel.w < 0.0:
        rel.negate()
    axis, angle = rel.to_axis_angle()
    q = R_IDLE @ Quaternion(axis, angle * fr(t))
    return frame_from(Bpx, depth, q)


def place_reachable(k, g_prev):
    """A reaction key: reference screen point and angle exactly; depth/recession as close to the requested ones as
    the arms allow (right elbow still bent, hands at least 14 cm in front of the eye)."""
    want = HOLD_DEPTH * k['depth']
    best = None
    for i in range(-20, 31):
        depth = want * (1.0 + i * 0.02)
        for tilt in (HOLD_TILT, 1.2, 1.0, 1.6):
            W = place(k['B'], k['angle'], depth, tilt, k.get('guard', ROLL), g_prev)
            rr, rl = reach(W, 'r'), reach(W, 'l')
            hands = min((W @ GRIP[s]).translation.y for s in 'rl')
            if rr > REACH_MAX or rl > REACH_MAX or hands < 0.14 or tip_of(W).y < 0.15:
                continue
            cost = abs(depth - want) / want + abs(tilt - HOLD_TILT) * 0.2
            if best is None or cost < best[0]:
                best = (cost, W, depth)
    if best is None:
        raise SystemExit('Reaction key unreachable: %s' % k)
    return best[1], best[2]


def key_track(spec):
    """Reference keys -> weapon frames, interpolated as blade-base screen path, depth and orientation offsets."""
    keys, frames, g_prev = spec['keys'], [], G_HOLD
    alphas, solved = {'r': [], 'l': []}, []
    for k in keys:
        if k.get('hold'):
            W, depth = W_HOLD0, HOLD_DEPTH
            for s in 'rl':
                alphas[s].append(ALPHA_HOLD[s])
        else:
            W, depth = place_reachable(k, g_prev)
            for s in 'rl':
                fixed = k.get('alpha', {}).get(s)
                alphas[s].append(float(fixed) if fixed is not None else best_alpha(W, s, alphas[s][-1], steps=8))
        solved.append({'t': k['t'], 'depth_m': round(depth, 3), 'alpha_r': round(alphas['r'][-1], 1),
                       'alpha_l': round(alphas['l'][-1], 1)})
        g_prev = guard_axis(W)
        frames.append(W)
    ts = [k['t'] for k in keys]
    spec['solved'] = solved
    fa = {s: pchip(ts, alphas[s]) for s in 'rl'}
    bx, by, dep, rots = [], [], [], []
    for W in frames:
        x, y, d = ndc_depth(W @ BLADE_BASE)
        bx.append(x)
        by.append(y)
        dep.append(d)
        rel = R_HOLD0.inverted() @ W.to_quaternion()
        if rel.w < 0.0:
            rel.negate()
        axis, angle = rel.to_axis_angle()
        rots.append(axis * angle)
    fx, fy, fd = pchip(ts, bx), pchip(ts, by), pchip(ts, dep)
    fr = [pchip(ts, [r[i] for r in rots]) for i in range(3)]

    def pose(t):
        v = Vector((fr[0](t), fr[1](t), fr[2](t)))
        q = R_HOLD0 @ (Quaternion(v.normalized(), v.length) if v.length > 1e-9 else Quaternion())
        return frame_from((fx(t), fy(t)), fd(t), q), {s: fa[s](t) for s in 'rl'}
    return pose, frames


HIT_POSE, HIT_KEYS = key_track(K['hit'])
BREAK_POSE, BREAK_KEYS = key_track(K['break'])
RAISE_END = K['raise']['duration']
RAISE_ROT = pchip(K['raise']['t'], [v if k < len(K['raise']['rot']) - 1 else 1.0 for k, v in enumerate(K['raise']['rot'])])


def guard_pose(t):
    if t >= RAISE_END:
        return hold_pose(t - RAISE_END), dict(ALPHA_HOLD)
    # The fist turns round the handle with the blade's turn (no extrapolation past the hold for the grip).
    p = max(0.0, min(1.0, RAISE_ROT(t)))
    return raise_pose(t), {s: ALPHA_HOLD[s] * p for s in 'rl'}


SEQUENCES = {
    'Guard': (RAISE_END + BR['period'], guard_pose),
    'GuardHit': (K['hit']['duration'], HIT_POSE),
    'GuardBreak': (K['break']['duration'], BREAK_POSE),
}

order, pending = [], set(c.names)
while pending:
    for n in list(pending):
        if c.parent[n] is None or c.parent[n] not in pending:
            order.append(n)
            pending.remove(n)

c.source_action.name = 'RETAINED_V4_Idle'
c.source_action.use_fake_user = True


def author_clip(name, duration, pose_at):
    # The idle source blend still carries the V18-V21 guard actions under the same names; keep them, renamed.
    old = bpy.data.actions.get('A_RuneSword_' + name)
    if old is not None:
        old.name = 'RETAINED_PRE_V24_A_RuneSword_' + name
    action = c.source_action.copy()
    action.name = 'A_RuneSword_' + name
    if action.name != 'A_RuneSword_' + name:
        raise SystemExit('Action name collision: ' + action.name)
    action.use_fake_user = True
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in list(bag.fcurves):
                    bag.fcurves.remove(curve)
    arm = Arm(c.rest, c.idle, c.idle_scale)
    twist = {s: Hd.Twist(c.rest, s) for s in 'rl'}
    humerus = {'r': None, 'l': None}
    prev_q, rows = {}, []
    end_frame = int(round(duration * FPS))
    for frame in range(end_frame + 1):
        t = frame / FPS
        W, alpha = pose_at(t)
        explicit = {'WPN_root': W}
        row = {'frame': frame, 't': round(t, 4), 'alpha_r': round(alpha['r'], 1), 'alpha_l': round(alpha['l'], 1)}
        for s in 'rl':
            target = grip_at(W, s, alpha[s])
            part, clamped = arm.solve(target, s, key=s)
            explicit.update(part)
            humerus[s] = arm.roll_humerus(explicit, s, humerus[s])
            row['reach_' + s] = round(reach(W, s), 3)
            row['clamp_%s_mm' % s] = round(clamped * 1000, 2)
            row['grip_err_%s_mm' % s] = round((explicit['hand_' + s].translation - target.translation).length * 1000, 2)
        pose = {}
        for n in order:
            if n in explicit:
                pose[n] = explicit[n]
            elif c.parent[n] is None:
                pose[n] = idle[n]
            else:
                p = c.parent[n]
                pose[n] = pose[p] @ idle[p].inverted() @ idle[n]
        for s in 'rl':
            up = 'upperarm_' + s
            for k in ('01', '02'):
                n = 'upperarm_twist_%s_%s' % (k, s)
                if n in pose:
                    pose[n] = pose[up] @ idle[up].inverted() @ idle[n]
            row['twist_' + s] = round(twist[s].apply(pose, c.idle_scale), 1)
            row['wrist_' + s] = round(arm.wrist_bend(pose, s), 1)
        for n in order:
            p = c.parent[n]
            if p and n not in explicit and not n.startswith(('upperarm_twist', 'lowerarm_twist')) and \
                    (p.startswith(('upperarm_twist', 'lowerarm_twist')) or p in explicit):
                pose[n] = pose[p] @ idle[p].inverted() @ idle[n]
        base = project(W @ BLADE_BASE)
        row['base_px'] = [round(base.x, 1), round(base.y, 1)]
        row['angle'] = round(screen_angle(W @ BLADE_BASE, W @ Vector((0.0, 0.0, 0.45))), 2)
        row['guard'] = round(screen_angle(W @ Vector((-0.15, 0.0, 0.03)), W @ Vector((0.15, 0.0, 0.03))) % 180.0, 1)
        row['tip_depth'] = round(tip_of(W).y, 3)
        row['hand_depth'] = round(min(pose['hand_' + s].translation.y for s in 'rl'), 3)
        world = {}
        for n in order:
            b = rig.pose.bones[n]
            b.rotation_mode = 'QUATERNION'
            pm = world.get(c.parent[n], Matrix.Identity(4))
            loc, q, sc = (c.local_rest[n].inverted() @ (pm.inverted() @ pose[n])).decompose()
            if n in prev_q and q.dot(prev_q[n]) < 0.0:
                q.negate()
            prev_q[n] = q.copy()
            b.location, b.rotation_quaternion, b.scale = loc, q, c.idle_local[n][2]
            world[n] = pm @ c.local_rest[n] @ Matrix.LocRotScale(loc, q, sc)
            for ch in ('location', 'rotation_quaternion', 'scale'):
                b.keyframe_insert(ch, frame=frame, group=n)
        rows.append(row)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:
                        key.interpolation = 'LINEAR'
    return action, end_frame, rows


c.scene.render.fps, c.scene.render.fps_base = FPS, 1.0
OUT = HERE / 'Export' / ('LongGrip' if VARIANT == 'LongGrip' else '')
report = {'revision': 'GuardKuboldV24', 'variant': VARIANT, 'idle_source': str(c.source),
          'reference': K['reference'], 'camera': K['camera'],
          'hold': {'depth_m': round(HOLD_DEPTH, 3), 'tilt': round(HOLD_TILT, 2), 'reach_r': round(HOLD_RR, 3),
                   'reach_l': round(HOLD_RL, 3), 'width_ratio': round(HOLD_RATIO, 2),
                   'width_px_near': round(HOLD_WIDTH, 1), 'reference_width_px_near': 85.0},
          'grip_turn_hold_deg': {s: round(ALPHA_HOLD[s], 1) for s in 'rl'},
          'hit_keys': K['hit'].get('solved'), 'break_keys': K['break'].get('solved'),
          'clips': {}, 'testing': 'Authoring metrics only; no game or editor test. User tests.'}
for name in CLIPS:
    duration, pose_at = SEQUENCES[name]
    action, end_frame, rows = author_clip(name, duration, pose_at)
    c.scene.frame_start, c.scene.frame_end = 0, end_frame
    c.scene.frame_set(0)
    if '--no-export' not in sys.argv:
        OUT.mkdir(parents=True, exist_ok=True)
        bpy.ops.object.select_all(action='DESELECT')
        rig.hide_set(False)
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        bpy.ops.export_scene.fbx(
            filepath=str(OUT / ('A_RuneSword_%s.fbx' % name)), use_selection=True, object_types={'ARMATURE'},
            axis_forward='-Y', axis_up='Z', add_leaf_bones=False, bake_anim=True,
            bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0)

    def peak(k, fn=max):
        return fn(r[k] for r in rows)
    report['clips'][name] = {
        'seconds': round(end_frame / FPS, 4), 'frames': end_frame,
        'max_reach': {s: peak('reach_' + s) for s in 'rl'}, 'max_clamp_mm': {s: peak('clamp_%s_mm' % s) for s in 'rl'},
        'max_grip_err_mm': {s: peak('grip_err_%s_mm' % s) for s in 'rl'},
        'max_wrist_deg': {s: peak('wrist_' + s) for s in 'rl'},
        'twist_range_deg': {s: [peak('twist_' + s, min), peak('twist_' + s)] for s in 'rl'},
        'min_tip_depth': peak('tip_depth', min), 'min_hand_depth': peak('hand_depth', min), 'samples': rows}
(HERE / ('authoring_v24' + ('_long_grip' if VARIANT == 'LongGrip' else '') + '.json')).write_text(
    json.dumps(report, indent=1, ensure_ascii=False), encoding='utf-8')
(HERE / 'Work').mkdir(exist_ok=True)
rig.animation_data.action = bpy.data.actions['A_RuneSword_Guard']
bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'Work' / ('preview_%s.blend' % VARIANT)))
print('GUARD_V24_AUTHORED', VARIANT, json.dumps({k: v for k, v in report.items() if k != 'clips'}),
      json.dumps({n: {k: v for k, v in r.items() if k != 'samples'} for n, r in report['clips'].items()}))
