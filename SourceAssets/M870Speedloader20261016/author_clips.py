"""Author the M870 speedloader clips from the installed SUPER90 R27 loader (offline, numpy).

Rig and gun placement are identical (68 bones, same names/parents/ref; same idle
WPN_root), so the R27 timeline is kept frame for frame and only what differs is
rebuilt:
- right arm: M870's own stock-wrist grip, carried with the R27 gun motion
  (R27 right-arm local deltas on the M870 idle chain, then exact IK contact);
- left arm: leaves and regrips the M870 pump (gun-relative), R27 fetch/dock/push/
  flick in between; fingers blend AKM grip <-> R27;
- loader props (WPN_Shell tube, WPN_SOCKET_Magazine plunger) and the holding hand
  move to the M870 loading port (+DELTA in gun frame) for the docked stroke;
- gun markers / pump / trigger use M870's own locals;
- empty = normal 0..144 (pump forward) + M870 standalone pump cycle (64 frames).
Writes clips.json (local rows per frame) and authoring.json (checks).
"""
import json, math
from pathlib import Path
import numpy as np
from rig import fk, row2m, m2row, inv, q2m, m2q, slerp, blend_m, window

O = Path(__file__).parent
D = json.loads((O / 'inputs.json').read_text())
S, M = D['super90'], D['m870']; SC, MC = D['super90_clips'], D['m870_clips']
NAMES, PAR = M['names'], M['parents']
FINGERS = ('thumb', 'index', 'middle', 'ring', 'pinky')
def chain(side):
    return ['clavicle_' + side, 'upperarm_' + side, 'lowerarm_' + side, 'hand_' + side,
            'lowerarm_aux_' + side, 'lowerarm_twist_01_' + side, 'lowerarm_twist_02_' + side]
def fingers(side): return [n for n in NAMES if n.endswith('_' + side) and n.startswith(FINGERS)]
LEFT, RIGHT = chain('l') + fingers('l'), chain('r')
PROPS = ['WPN_Shell', 'WPN_SOCKET_Magazine']
M870_OWN = ['WPN_bolt', 'WPN_Trigger', 'WPN_SOCKET_Muzzle', 'WPN_SOCKET_Eject', 'WPN_RearSight', 'WPN_FrontSight',
            'WPN_ChargingHandle', 'WPN_BoltCatch'] + fingers('r')
# Gun frame (WPN_root local, metres; +y down, +z back). Receiver bottom edge at the
# port: SUPER90 y=0.0284, M870 y=0.0129-0.0151 (analyze_guide.py); port recess
# centre moves ~5 mm back. R27 seated tube tip: (0, 0.035, 0.056).
DELTA = np.array([0., -0.0150, 0.0050])
NORMAL_FRAMES = 144
CYCLE = MC['cycle']['rows']
M_IDLE = MC['idle']['rows'][0]; S_IDLE = SC['idle']['rows'][0]
W_MIDLE = fk(NAMES, PAR, M_IDLE)
G_L = inv(W_MIDLE['WPN_root']) @ W_MIDLE['hand_l']     # pump grip in gun frame
G_R = inv(W_MIDLE['WPN_root']) @ W_MIDLE['hand_r']     # stock-wrist grip in gun frame


def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return np.array([aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
                     aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz])
def qinv(q): return np.array([-q[0], -q[1], -q[2], q[3]])
def unit(m): return m[:3, :3] / np.linalg.norm(m[:3, :3], axis=0)


def rot_between(u, v):
    u = u / np.linalg.norm(u); v = v / np.linalg.norm(v); c = np.cross(u, v); d = float(np.dot(u, v))
    if d > 1 - 1e-12: return np.eye(3)
    if d < -1 + 1e-12:
        a = np.cross(u, [1, 0, 0]); a = a if np.linalg.norm(a) > 1e-6 else np.cross(u, [0, 1, 0]); a /= np.linalg.norm(a)
        return 2 * np.outer(a, a) - np.eye(3)
    k = np.array([[0, -c[2], c[1]], [c[2], 0, -c[0]], [-c[1], c[0], 0]])
    return np.eye(3) + k + k @ k / (1 + d)


def axis_rot(axis, ang):
    a = axis / np.linalg.norm(axis); k = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(ang) * k + (1 - math.cos(ang)) * k @ k


def with_rot(m, r):
    out = m.copy(); out[:3, :3] = r * np.linalg.norm(m[:3, :3], axis=0); return out


def ik(W, side, target, stats):
    """Two-bone contact solve (native lengths), pole from the incoming elbow; hand = target.
    Forearm roll change is spread over the native skin stations (aux .2, twist_02 .5, twist_01 .8)."""
    U, L, H = 'upperarm_' + side, 'lowerarm_' + side, 'hand_' + side
    S0, E0, H0 = W[U][:3, 3], W[L][:3, 3], W[H][:3, 3]
    a, b = np.linalg.norm(E0 - S0), np.linalg.norm(H0 - E0)
    goal = target[:3, 3].copy(); v = goal - S0; dist = np.linalg.norm(v); axis = v / dist
    reach = (a + b) * .9995
    if dist > reach:
        stats['shortfall_cm'] = max(stats.get('shortfall_cm', 0.), float(dist - reach)); goal = S0 + axis * reach; dist = reach
    dist = max(dist, abs(a - b) + 1e-6)
    along = (a * a - b * b + dist * dist) / (2 * dist)
    pole = (E0 - S0) - axis * np.dot(E0 - S0, axis); pole /= max(np.linalg.norm(pole), 1e-9)
    E1 = S0 + axis * along + pole * math.sqrt(max(0., a * a - along * along))
    ra = rot_between(E0 - S0, E1 - S0)
    oldL = W[L].copy(); oldH = W[H].copy(); kids = {n: inv(oldL) @ W[n] for n in ('lowerarm_aux_' + side, 'lowerarm_twist_01_' + side, 'lowerarm_twist_02_' + side)}
    W[U] = with_rot(W[U], ra @ unit(W[U]))
    Lm = with_rot(oldL, ra @ unit(oldL)); Lm[:3, 3] = E1
    Hdir = ra @ (H0 - E0)
    rb = rot_between(Hdir, goal - E1)
    Lm = with_rot(Lm, rb @ unit(Lm)); W[L] = Lm
    carried = rb @ ra @ unit(oldH); want = unit(target)
    W[H] = with_rot(oldH, want); W[H][:3, 3] = goal
    fa = (goal - E1) / np.linalg.norm(goal - E1)
    roll = want @ carried.T
    q = m2q(roll); ang = 2 * math.atan2(float(np.dot(q[:3], fa)), q[3]); ang = (ang + math.pi) % (2 * math.pi) - math.pi
    for n, w in (('lowerarm_aux_' + side, .20), ('lowerarm_twist_02_' + side, .50), ('lowerarm_twist_01_' + side, .80)):
        base = W[L] @ kids[n]; W[n] = with_rot(base, axis_rot(fa, ang * w) @ unit(base))
    stats['max_roll_deg'] = max(stats.get('max_roll_deg', 0.), abs(math.degrees(ang)))


def world_from(locals_):
    return fk(NAMES, PAR, locals_)


def locals_of(W, bones, scale_from):
    out = {}
    for n in bones:
        m = inv(W[PAR[n]]) @ W[n]
        out[n] = m2row(m, scale_from[n][7:10])
    return out


def build(count):
    src_rows = SC['normal_%d' % count]['rows']
    rows, stats = [], {}
    for f, src in enumerate(src_rows):
        Ws = world_from(src)
        gun = Ws['WPN_root']
        loc = {n: list(src[n]) for n in NAMES}
        for n in M870_OWN: loc[n] = list(M_IDLE[n])
        # Right arm: R27 local deltas carried onto M870's own chain.
        for n in RIGHT:
            dq = qmul(src[n][3:7], qinv(S_IDLE[n][3:7]))
            loc[n] = list(M_IDLE[n][:3]) + list(qmul(dq, M_IDLE[n][3:7])) + list(M_IDLE[n][7:10])
        # Left arm FK base: M870 idle <-> R27 by the start/end weights.
        # Regrip starts after the R27 detach cue (src 123.46) and lands as the gun settles (~140).
        ws = window(f, 0, 16) * (1 - window(f, 125, 140))
        for n in LEFT:
            a, b = np.array(M_IDLE[n]), np.array(src[n])
            loc[n] = list(a[:3] + (b[:3] - a[:3]) * ws) + list(slerp(a[3:7], b[3:7], ws)) + list(a[7:10])
        W = world_from(loc)
        sr = {}
        ik(W, 'r', gun @ G_R, sr)
        # Port offset for the loader and the hand that holds it.
        wd = window(f, 56, 80) * (1 - window(f, 118, 128))
        off = unit(gun) @ (DELTA * wd) * np.linalg.norm(gun[:3, :3], axis=0)[0]
        held = Ws['hand_l'].copy(); held[:3, 3] += off
        target = blend_m(gun @ G_L, held, ws)
        sl = {}
        ik(W, 'l', target, sl)
        new = {}
        new.update(locals_of(W, ['upperarm_r', 'lowerarm_r', 'hand_r', 'lowerarm_aux_r', 'lowerarm_twist_01_r', 'lowerarm_twist_02_r'], loc))
        new.update(locals_of(W, ['upperarm_l', 'lowerarm_l', 'hand_l', 'lowerarm_aux_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l'], loc))
        for n in PROPS:
            pw = Ws[n].copy(); pw[:3, 3] += off
            # After the props hide (src 125) settle onto M870's parked pose for a clean join.
            park = window(f, 126, 140)
            if park > 0:
                parked = W_MIDLE[PAR[n]] @ row2m(M_IDLE[n]); parent_now = world_from(loc)[PAR[n]]
                pw = blend_m(pw, parent_now @ inv(W_MIDLE[PAR[n]]) @ parked, park)
            parent = world_from({**loc, **new})[PAR[n]] if PAR[n] not in ('VM_Root', 'WPN_root') else Ws[PAR[n]]
            new[n] = m2row(inv(parent) @ pw, src[n][7:10])
        loc.update(new)
        rows.append(loc)
        for k, v in list(sr.items()) + [('left_' + k, v) for k, v in sl.items()]:
            stats[k] = max(stats.get(k, 0.), v)
    # Exact endpoints: frame 0 and the last frame are the M870 idle arms.
    for f in (0, len(rows) - 1):
        for n in LEFT + RIGHT + M870_OWN: rows[f][n] = list(M_IDLE[n])
    return rows, stats


def empty_from(normal):
    rows = [dict(r) for r in normal]
    for f in range(1, len(CYCLE)):
        r = {n: list(CYCLE[f][n]) for n in NAMES}
        rows.append(r)
    return rows


if __name__ == '__main__':
    out, report = {}, {'delta_gun_m': DELTA.tolist(), 'normal_frames': NORMAL_FRAMES, 'cycle_frames': len(CYCLE) - 1, 'clips': {}}
    for count in range(1, 8):
        normal, st = build(count)
        empty = empty_from(normal)
        out['normal_%d' % count] = dict(frames=len(normal) - 1, rows=normal)
        out['empty_%d' % count] = dict(frames=len(empty) - 1, rows=empty)
        report['clips']['normal_%d' % count] = st
        print('M870_LOADER_AUTHOR', count, {k: round(v, 3) for k, v in st.items()}, 'empty frames', len(empty) - 1, flush=True)
    (O / 'clips.json').write_text(json.dumps(out, separators=(',', ':')))
    (O / 'authoring.json').write_text(json.dumps(report, indent=1))
