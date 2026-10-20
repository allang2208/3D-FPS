"""R26 left-hand layer for the Super90 loader push and flick (author data only).

Accepted trajectories stay: pusher, tube, gun, right arm, camera, audio and ammo
clock are untouched; only the left arm chain and left fingers are rewritten.

1. Push: the fist rocks about the knob's own axis (pivot = knob centre, so the
   palm keeps its contact) - a dock catch, alignment pre-load with one settle,
   drive follow-through and a seat throw - plus a small dock / effort squeeze.
2. Flick: the wrist leads the throw (snap about the wrist), fingers trail
   proximal -> distal once clear of the knob, and the dead stop between the
   flick and the return swing is removed by retiming the wrist along its path.

Layers are designed in perceived R26 pace time and sampled on the 60 Hz source
clock that every consumer shares. Gun-relative wrist targets re-solve the arm
with the installed shoulder and bone lengths (Super90LoaderArmRoot method).
"""
import copy, json, math
import numpy as np
from scipy.optimize import brentq
from scipy.spatial.transform import Rotation as R, Slerp
from r26_core import *
import r26_timing as T

# R26b: the hang retime stops at the detach cue (R26a moved the swing ahead of it).
REVISION = 'Super90LoaderR26b-20261016'
WRITE = [n for n in ARM if n != 'clavicle_l'] + FINGERS
RAD = math.pi / 180.


def smooth(x):
    x = min(1., max(0., x))
    return x * x * x * (x * (x * 6 - 15) + 10)


def ramp(p, a, b):
    return smooth((p - a) / (b - a))


def hump(p, a, b):
    x = (p - a) / (b - a)
    return math.sin(math.pi * x) ** 2 if 0. < x < 1. else 0.


_peak = {}
def impulse(p, t0, rise, decay, period):
    """Damped impact response starting at t0 (pace frames), first peak normalised to 1."""
    key = (rise, decay, period)
    if key not in _peak:
        xs = np.linspace(0., 6. * decay, 6001)
        _peak[key] = float(np.max((1 - np.exp(-xs / rise)) * np.exp(-xs / decay) * np.cos(2 * np.pi * xs / period)))
    x = p - t0
    if x <= 0.:
        return 0.
    tail = 1. - smooth((x - 4. * decay) / (2. * decay))
    return (1 - math.exp(-x / rise)) * math.exp(-x / decay) * math.cos(2 * math.pi * x / period) / _peak[key] * tail


# ---- Perceived-time layers (degrees; pace frames, 60 Hz pace).
RELEASE = (116.6, 119.6)          # hand leaves the knob after the seat at pace 116


def push_roll(p):
    """About the knob axis; + = wrist carried along the forearm's push (inertia)."""
    # Alignment keys are ~3 pace frames apart on the 60 Hz source, so the dock
    # catch is kept broad enough to land on real keys instead of between them.
    # The seat recoil is carried by flick_snap: it acts against the push, so a
    # separate forward throw would only zig-zag on the 60 Hz keys.
    r = (4.0 * impulse(p, 87.2, .8, 3.5, 14.)                     # dock catch
         - 6.5 * ramp(p, 88., 98.5) - 1.2 * hump(p, 93.5, 103.5)   # cock the wrist, one settle
         + 2.8 * ramp(p, 104.5, 114.5))                            # drive: wrist follows through
    return r * (1. - ramp(p, *RELEASE))


def push_twist(p):
    """About the forearm; + = index side leads the drive."""
    return (2.0 * ramp(p, 103., 112.) - 1.0 * hump(p, 88., 99.)) * (1. - ramp(p, *RELEASE))


SNAP_ONSET = 116.4                # pace; recoil off the seat (pace 116), two keys of rise


def flick_snap(p):
    """Peel-off roll (see snap_setup): wrist leads the throw, then follow-through."""
    return 13. * impulse(p, SNAP_ONSET, 2.0, 3.4, 16.)


def squeeze(p):
    return 1.6 * impulse(p, 87.2, .8, 3.5, 16.) + 1.0 * ramp(p, 104., 109.) * (1. - ramp(p, 114.5, 116.))


def joint(n):
    return n.split('_')[1]


SQUEEZE_GAIN = {n: 0. if 'metacarpal' in n else
                ({'01': .3, '02': .8, '03': .5} if n.startswith('thumb') else {'01': 1., '02': .7, '03': .35})[joint(n)]
                for n in FINGERS}
WHIP_LAG = {n: 0. if 'metacarpal' in n else
            ({'01': .5, '02': .7, '03': .9} if n.startswith('thumb') else {'01': .35, '02': .75, '03': 1.1})[joint(n)]
            for n in FINGERS}
WHIP = (112.5, 114.5, 127., 133.)  # source frames: in, full, out-begin, out-end
WHIP_ZETA = .75



_pace = {}
def pace(f):
    if f not in _pace:
        _pace[f] = T.pace_frame(f)
    return _pace[f]


# ---- Geometry helpers.
def gun_rel(w, n):
    return np.linalg.inv(w[GUN]) @ w[n]


def rot(axis, deg):
    return R.from_rotvec(norm(axis) * deg * RAD).as_matrix()


def about(m, pivot, r):
    out = m.copy()
    out[:3, :3] = r @ m[:3, :3]
    out[:3, 3] = pivot + r @ (m[:3, 3] - pivot)
    return out


def interp_gun(W, tau, n):
    lo = int(math.floor(tau)); hi = min(lo + 1, len(W) - 1); u = tau - lo
    a, b = gun_rel(W[lo], n), gun_rel(W[hi], n)
    out = np.eye(4)
    out[:3, 3] = a[:3, 3] * (1 - u) + b[:3, 3] * u
    out[:3, :3] = Slerp([0, 1], R.from_matrix([a[:3, :3], b[:3, :3]]))(u).as_matrix()
    return out


def lerp_pos(W, tau, n):
    lo = int(math.floor(tau)); hi = min(lo + 1, len(W) - 1); u = tau - lo
    return W[lo][n][:3, 3] * (1 - u) + W[hi][n][:3, 3] * u


def tip(w, digit):
    a, b = w[digit + '_02_l'][:3, 3], w[digit + '_03_l'][:3, 3]
    return b + (b - a) * .8


def conventions(W):
    """Hand-local axes and signs from a held push frame (all families share the rig)."""
    w = W[100]
    h = w['hand_l']; hi = np.linalg.inv(h[:3, :3])
    c = w[POST][:3, 3]; wrist = h[:3, 3]
    width = norm(w['index_01_l'][:3, 3] - w['pinky_01_l'][:3, 3])
    fingers = norm(w['middle_01_l'][:3, 3] - wrist)
    fore = norm(wrist - w['lowerarm_l'][:3, 3])
    push = w[GUN][:3, :3] @ norm(gun_rel(W[110], POST)[:3, 3] - gun_rel(W[90], POST)[:3, 3])
    knob = norm(w[POST][:3, 2]) * np.sign(np.dot(w[POST][:3, 2], width))
    s_in = np.sign(np.dot(np.cross(knob, wrist - c), fore))
    s_tw = np.sign(np.dot(np.cross(fore, w['index_01_l'][:3, 3] - c), push))
    tips = np.mean([tip(w, d) for d in DIGITS if d != 'thumb'], axis=0)
    knuckles = np.mean([w[d + '_01_l'][:3, 3] for d in DIGITS if d != 'thumb'], axis=0)
    palmar = tips - knuckles; palmar = norm(palmar - fingers * np.dot(palmar, fingers))
    s_open = np.sign(np.dot(np.cross(width, tip(w, 'middle') - wrist), -palmar))
    return dict(knob_local=hi @ (knob * s_in), width_local=hi @ (width * s_open),
                s_in=s_in, s_tw=s_tw, s_open=s_open)


def flex_axes(rows):
    """Per-joint flexion axis in the parent frame: grasp (100) relative to splayed open (116)."""
    out = {}
    for n in FINGERS:
        rv = (R.from_quat(rows[100][n][3:7]) * R.from_quat(rows[116][n][3:7]).inv()).as_rotvec()
        size = np.linalg.norm(rv)
        out[n] = (rv / size if size > 1e-6 else np.zeros(3), min(1., math.degrees(size) / 5.))
    return out


# S_Super90_Loader_Detach and the R21 detach response both start at this source
# frame; the return swing must not leave before them (R26 first save did, ~3.5 frames).
DETACH_CUE = 123.464567
HANG_BEGIN = 115                  # the throw through source 115 keeps its installed speed


def hang_warp(W, a):
    """Retime the gun-relative wrist along its own path between the flick and the detach cue.

    Only [a, floor(DETACH_CUE)] is retimed and both ends keep their frames, so the
    swing after the detach is the installed motion. Inside, the flick decays
    exponentially into the installed swing-start speed instead of stopping."""
    P = np.array([gun_rel(w, 'hand_l')[:3, 3] for w in W])
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    speed = seg * FPS
    b = int(math.floor(DETACH_CUE))
    L = np.r_[0., np.cumsum(seg)]
    length, n = L[b] - L[a], b - a
    v0, v1 = seg[a], seg[b]
    def area(t):
        k = np.arange(n)
        return float(np.sum(v1 + (v0 - v1) * np.exp(-k / t))) - length
    tc = brentq(area, .05, 50.)
    vn = v1 + (v0 - v1) * np.exp(-np.arange(n) / tc)
    if np.any(vn <= 0):
        raise ValueError('Non-monotone hang retime')
    Ln = L[a] + np.r_[0., np.cumsum(vn)]
    tau = np.interp(Ln, L, np.arange(len(L)))
    tau[-1] = b
    return {int(f): float(t) for f, t in zip(range(a, b + 1), tau)}, dict(window=[a, b], decay_frames=float(tc),
        old_min_mps=float(speed[a:b].min()), new_min_mps=float(vn.min() * FPS),
        old_peak_mps=float(speed[a:b].max()), new_peak_mps=float(vn.max() * FPS))


def spring(targets, lag, velocity, zeta=WHIP_ZETA, sub=16):
    """Second-order follower; starts on the target with its own velocity (no built-up lag)."""
    wn = 2 * zeta / lag
    x, v, out = targets[0].copy(), velocity.copy(), [targets[0].copy()]
    for i in range(1, len(targets)):
        for s in range(sub):
            r = targets[i - 1] + (targets[i] - targets[i - 1]) * (s + 1) / sub
            v += (wn * wn * (r - x) - 2 * zeta * wn * v) / sub
            x += v / sub
        out.append(x.copy())
    return np.array(out)


def whip_weight(f):
    a, b, c, d = WHIP
    return ramp(f, a, b) * (1. - ramp(f, c, d))


def finger_locals(rows, axes):
    """Squeeze during the push, then proximal->distal trailing once the hand is clear."""
    n_frames = len(rows)
    out = [{n: rows[f][n][3:7].copy() for n in FINGERS} for f in range(n_frames)]
    for f in range(n_frames):
        amount = squeeze(pace(f)) if f <= 111 else 0.
        if abs(amount) < 1e-9:
            continue
        for n in FINGERS:
            axis, scale = axes[n]
            gain = SQUEEZE_GAIN[n] * scale
            if gain:
                out[f][n] = (R.from_rotvec(axis * amount * gain * RAD) * R.from_quat(out[f][n])).as_quat()
    a, d = int(WHIP[0]), int(WHIP[3]) + 1
    for n in FINGERS:
        if not WHIP_LAG[n]:
            continue
        ref = R.from_quat(out[a][n])
        target = np.array([(R.from_quat(out[f][n]) * ref.inv()).as_rotvec() for f in range(a - 1, d + 1)])
        follow = spring(target[1:], WHIP_LAG[n], (target[2] - target[0]) / 2.)
        for i, f in enumerate(range(a, d + 1)):
            wgt = whip_weight(f)
            if wgt <= 0.:
                continue
            q = Slerp([0, 1], R.from_quat([out[f][n], (R.from_rotvec(follow[i]) * ref).as_quat()]))(wgt)
            out[f][n] = q.as_quat()
    return out


KNOB_SAMPLES = [d + s for d in ('index', 'middle', 'ring', 'pinky', 'thumb') for s in ('_02_l', '_03_l')]
def knob_clearance(w):
    """Smallest distance (mm) from finger joints and tips to the knob axis, in gun metres."""
    g = np.linalg.inv(w[GUN])
    post = g @ w[POST]
    c, k = post[:3, 3], norm(post[:3, 2])
    pts = [(g @ w[n])[:3, 3] for n in KNOB_SAMPLES] + [(g[:3, :3] @ tip(w, d) + g[:3, 3]) for d in DIGITS]
    out = []
    for p in pts:
        r = p - c
        out.append(np.linalg.norm(r - k * np.dot(r, k)) if abs(np.dot(r, k)) < .035 else 1.)
    return float(min(out) * 1000)


def snap_setup(W, conv):
    """The fist peels off the seated knob: roll about the knob axis through the seated
    knob centre (rigid palm/finger distances to that axis are preserved), then the
    pivot slides to the wrist once the hand is clear. Sign adds to the throw."""
    seat = gun_rel(W[110], POST)[:3, 3]
    w = W[111]
    k = norm(w['hand_l'][:3, :3] @ conv['knob_local'])
    c = (w[GUN] @ np.r_[seat, 1.])[:3]
    throw = W[114]['hand_l'][:3, 3] - W[111]['hand_l'][:3, 3]
    return dict(seat=seat, sign=float(np.sign(np.dot(np.cross(k, w['hand_l'][:3, 3] - c), throw))), gain=1.)


SNAP_PIVOT = (113., 116.)         # source frames: seated knob centre -> wrist


def hand_target(W, f, conv, tau, snap):
    w, p = W[f], pace(f)
    roll, twist, angle = push_roll(p), push_twist(p), flick_snap(p) * snap['gain']
    hand, pole = w['hand_l'], None
    warped = f in tau and abs(tau[f] - f) > 1e-6
    if warped:
        hand = w[GUN] @ interp_gun(W, tau[f], 'hand_l')
        a, e, t = (lerp_pos(W, tau[f], n) for n in ('upperarm_l', 'lowerarm_l', 'hand_l'))
        axis0 = norm(t - a)
        pole = (axis0, e - a - axis0 * np.dot(e - a, axis0))
    if abs(roll) > 1e-6 or abs(twist) > 1e-6:
        fore = norm(w['hand_l'][:3, 3] - w['lowerarm_l'][:3, 3])
        r = rot(w['hand_l'][:3, :3] @ conv['knob_local'], roll) @ rot(fore * conv['s_tw'], twist)
        hand = about(hand, w[POST][:3, 3], r)
    if abs(angle) > 1e-6:
        u = ramp(f, *SNAP_PIVOT)
        pivot = (w[GUN] @ np.r_[snap['seat'], 1.])[:3] * (1. - u) + hand[:3, 3] * u
        hand = about(hand, pivot, rot(hand[:3, :3] @ conv['knob_local'], angle * snap['sign']))
    return hand, pole, warped, roll, angle


def fit_snap(W, conv, tau, snap, frames=range(110, 118), tolerance=1.):
    """Largest snap gain (<= 1) that brings no rigid finger point closer to the
    falling knob than the installed release does (minus `tolerance` mm). Points
    already farther than the held grasp distance cannot newly penetrate."""
    held = knob_clearance(W[100])
    def ok(gain):
        trial = dict(snap, gain=gain)
        for f in frames:
            hand = hand_target(W, f, conv, tau, trial)[0]
            moved = {n: (hand @ np.linalg.inv(W[f]['hand_l']) @ W[f][n]) if n in FINGERS or n == 'hand_l' else W[f][n]
                     for n in W[f]}
            if knob_clearance(moved) < min(knob_clearance(W[f]), held) - tolerance:
                return False
        return True
    if ok(1.):
        return 1.
    lo, hi = 0., 1.
    for _ in range(14):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if ok(mid) else (lo, mid)
    return lo


def author(role, family, conv, axes, tau, snap):
    rows = posed_local(role, family)
    W = [world(row) for row in rows]
    fingers = finger_locals(rows, axes)
    new_rows, metrics = [], dict(snap_deg=0., roll_deg=[0., 0.], clearance_drop_mm=0., length_err_mm=0., wrist_shift_mm=0.)
    for f, (row, w) in enumerate(zip(rows, W)):
        hand, pole, warped, roll, angle = hand_target(W, f, conv, tau, snap)
        squeezed = any(np.abs(fingers[f][n] - row[n][3:7]).max() > 1e-9 for n in FINGERS)
        if not (warped or squeezed or abs(roll) > 1e-6 or abs(push_twist(pace(f))) > 1e-6 or abs(angle) > 1e-6):
            new_rows.append(row)
            continue
        metrics['roll_deg'] = [min(metrics['roll_deg'][0], roll), max(metrics['roll_deg'][1], roll)]
        metrics['snap_deg'] = max(metrics['snap_deg'], abs(angle))
        out = solve_arm(w, hand, pole)
        for n in NAMES:
            if n in FINGERS:
                out[n] = out[PARENTS[n]] @ matrix(np.r_[row[n][:3], fingers[f][n], row[n][7:]])
        local = dict(row)
        for n in WRITE:
            local[n] = pack(np.linalg.inv(out[PARENTS[n]]) @ out[n])
        new_rows.append(local)
        # Author-side geometry checks (not a gameplay test).
        # Component space is centimetres (native root scale 100).
        for upper, lower in (('upperarm_l', 'lowerarm_l'), ('lowerarm_l', 'hand_l')):
            l0 = np.linalg.norm(w[lower][:3, 3] - w[upper][:3, 3]); l1 = np.linalg.norm(out[lower][:3, 3] - out[upper][:3, 3])
            metrics['length_err_mm'] = max(metrics['length_err_mm'], float(abs(l1 - l0) * 10))
        if f <= 118 and knob_clearance(out) < 15.:
            metrics['clearance_drop_mm'] = max(metrics['clearance_drop_mm'], knob_clearance(w) - knob_clearance(out))
        if not warped:
            metrics['wrist_shift_mm'] = max(metrics['wrist_shift_mm'], float(np.linalg.norm(out['hand_l'][:3, 3] - w['hand_l'][:3, 3]) * 10))
    return rows, new_rows, metrics


def track(n, values):
    values = np.array(values, float)
    for i in range(1, len(values)):
        if values[i - 1, 3:7] @ values[i, 3:7] < 0:
            values[i, 3:7] *= -1
    constant = np.max(np.abs(values - values[0])) < 1e-9
    return dict(bone=n, times=[0.] if constant else (np.arange(len(values)) / FPS).tolist(),
                values=values[0].tolist() if constant else values.ravel().tolist())


IDENTITY = np.array([0, 0, 0, 0, 0, 0, 1, 0, 0, 0], float)


def clip_inputs(role):
    """Clock-level inputs shared by all grip families of one clip (retime and snap gain)."""
    base_rows = posed_local(role)
    base_world = [world(r) for r in base_rows]
    tau, hang = hang_warp(base_world, HANG_BEGIN)
    setups = {}
    for family in ('base',) + FAMILIES:
        W = base_world if family == 'base' else [world(r) for r in posed_local(role, family)]
        conv = conventions(W)
        snap = snap_setup(W, conv)
        snap['gain'] = fit_snap(W, conv, tau, snap)
        setups[family] = (conv, snap)
    gain = min(s['gain'] for _, s in setups.values())
    for _, s in setups.values():
        s['gain'] = gain
    return setups, flex_axes(base_rows), tau, hang


def process(role):
    clip = D['clips'][role]
    setups, axes, tau, hang = clip_inputs(role)
    conv, snap = setups['base']
    _, base_new, base_metrics = author(role, 'base', conv, axes, tau, snap)
    spec = dict(path=clip['path'], source_sha256=clip['sha256'], frames=clip['frames'],
                duration=clip['duration'], tracks=[track(n, [r[n] for r in base_new]) for n in WRITE])
    layers, family_metrics = {}, {}
    for family in FAMILIES:
        fam_conv, fam_snap = setups[family]
        _, fam_new, fam_metrics = author(role, family, fam_conv, axes, tau, fam_snap)
        layer = copy.deepcopy(D['profiles'][family]['clips'][clip['path']])
        kept = [t for t in layer['tracks'] if t['bone'] not in WRITE]
        for n in WRITE:
            a = np.array([r[n] for r in base_new]); b = np.array([r[n] for r in fam_new])
            q = (R.from_quat(b[:, 3:7]) * R.from_quat(a[:, 3:7]).inv()).as_quat()
            q[q[:, 3] < 0] *= -1
            values = np.c_[b[:, :3] - a[:, :3], q, b[:, 7:] - a[:, 7:]]
            if np.max(np.abs(values - IDENTITY)) > 1e-7:
                kept.append(track(n, values))
        layer['tracks'] = kept
        layers[family] = layer
        family_metrics[family] = fam_metrics
    note = dict(conventions={k: float(conv[k]) for k in ('s_in', 's_tw', 's_open')},
                snap=dict(gain=snap['gain'], sign=snap['sign']), hang=hang, base=base_metrics, families=family_metrics)
    return role, spec, layers, note


def main():
    import multiprocessing
    out = dict(revision=REVISION, fps=FPS, write_bones=WRITE, clips={},
               profiles={f: dict(path=D['profiles'][f]['path'], clips={}) for f in FAMILIES}, runtime_tested=False)
    notes = dict(revision=REVISION, clock='Super90LoaderPushTiming.h from r26_timing.py', layers=dict(
        push_roll='knob axis, pivot knob centre: dock catch 3.5, pre-load -6.5 with 1.2 settle, drive +2.8, seat throw 6.0 deg',
        push_twist='forearm axis, pivot knob centre: -1.0 alignment, +2.0 drive deg',
        flick_snap='knob axis, pivot seated knob centre -> wrist (source %s): up to 13 deg peel-off from pace %.1f, '
                   'follow-through ~-5 deg; gain limited by knob clearance' % (list(SNAP_PIVOT), SNAP_ONSET),
        squeeze='dock pulse 1.6 deg and drive effort 1.0 deg at MCP (PIP 0.7, DIP 0.35, thumb 0.8/0.5)',
        whip='spring follow zeta %.2f, lag MCP/PIP/DIP 0.5/1.1/1.7 frames, source window %s' % (WHIP_ZETA, list(WHIP)),
        hang='wrist retimed along its gun-relative path only between source %d and the detach cue %.3f; '
             'flick decays into the installed swing-start speed, swing itself unchanged' % (HANG_BEGIN, DETACH_CUE)),
        preserved='pusher, tube, gun, right arm, clavicle, camera, audio, ammo commit, clip lengths and frame rate',
        clips={}, runtime_tested=False)
    with multiprocessing.Pool(min(7, len(D['clips']))) as pool:
        for role, spec, layers, note in pool.imap(process, list(D['clips'])):
            out['clips'][role] = spec
            for family, layer in layers.items():
                out['profiles'][family]['clips'][spec['path']] = layer
            notes['clips'][role] = note
            print('R26_AUTHORED', role, json.dumps(dict(snap_gain=note['snap']['gain'], hang=note['hang'], base=note['base'])), flush=True)
    (O / 'animation_patch.json').write_text(json.dumps(out, separators=(',', ':')))
    (O / 'authoring.json').write_text(json.dumps(notes, indent=2))


if __name__ == '__main__':
    main()
