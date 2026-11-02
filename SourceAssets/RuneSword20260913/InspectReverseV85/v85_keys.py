"""V85 clocks: the reference #10 绕手 frames played in reverse (counter-clockwise), from keys_v85.json.

Every hand / hilt channel is interpolated between the reference keys with monotone cubics (no overshoot).
R4: the sword turn comes from one continuous speed profile and every key's time is where that clock reaches the
key's phase, so the hand channels are locked to the blade.
"""
import bisect
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parents[0] / 'InspectForwardSpinV54'))
from spin_design import Curve, smoothstep  # noqa: E402

class Hermite:
    """Cubic Hermite through (t, value, slope per second) keys; holds the end values outside."""

    def __init__(self, keys):
        self.keys = sorted(keys)
        self.ts = [k[0] for k in self.keys]

    def __call__(self, t):
        k = self.keys
        if t <= k[0][0]:
            return k[0][1]
        if t >= k[-1][0]:
            return k[-1][1]
        i = bisect.bisect_right(self.ts, t) - 1
        (t0, v0, m0), (t1, v1, m1) = k[i], k[i + 1]
        h = t1 - t0
        u = (t - t0) / h
        u2, u3 = u * u, u * u * u
        return ((2 * u3 - 3 * u2 + 1) * v0 + (u3 - 2 * u2 + u) * h * m0
                + (-2 * u3 + 3 * u2) * v1 + (u3 - u2) * h * m1)

FPS = 120
# R5 (user: "整体动画适当放慢一些，20%"): the whole clip plays at 0.8x. Every time in this module is motion time;
# the author samples frame f at t = f / (FPS * TEMPO), so the clip lasts END * TEMPO and per-frame limits shrink by
# 1/TEMPO (same motion as R4, only slower).
TEMPO = 1.25
# R4 (user: R3's rhythm read "weird", V82 flowed better). motion_profile.py shows V82's blade never stops — one
# speed wave from the flick to the catch — while R3's key-to-key Hermite stalled it in the web (182 -> 190 -> 186,
# ~50 deg/s for 80 ms), re-accelerated it into the fist, and turned the hand hardest while the blade was slowest
# (six separate hand bursts). R4: one speed profile — flick, coast round the hand while it turns over, push home,
# caught still moving — and the hang keys N2w/N3 are gone from keys_v85.json.
SPIN_START = 0.395
WINDUP = [(0.00, 0.0), (0.18, 0.0), (0.31, -7.0), (SPIN_START, -12.0)]  # R4: smaller counter-tilt (R3 -20)
# The slow stretch (182-240 deg) is where the hand turns over (~170 deg of forearm roll): the blade coasts at
# ~450 deg/s so that roll has ~120 ms instead of R3's 55 ms snap.
SPEED = Curve([(SPIN_START, 0.0), (0.43, 800.0), (0.475, 1300.0), (0.525, 1100.0), (0.565, 620.0), (0.60, 420.0),
               (0.68, 400.0), (0.73, 540.0), (0.785, 680.0), (0.835, 620.0), (0.88, 430.0)])
SPIN_END = SPEED.xs[-1]
RECOVER_END = SPIN_END + 0.24  # V82 0.22, R3 0.32 (the long settle dragged and split the left hand's return)
END = RECOVER_END + 0.12

_DT = 1.0 / 2400.0
_N = int(round((SPIN_END - SPIN_START) / _DT))
_acc = [0.0]
for _i in range(_N):
    _acc.append(_acc[-1] + 0.5 * (SPEED(SPIN_START + _i * _DT) + SPEED(SPIN_START + (_i + 1) * _DT)) * _DT)
SPEED_SCALE = (360.0 - WINDUP[-1][1]) / _acc[-1]  # the profile is a shape; it is scaled to land exactly on 360
_PHI_TAB = [WINDUP[-1][1] + SPEED_SCALE * a for a in _acc]
END_SPEED = SPEED_SCALE * SPEED.ys[-1]  # deg/s the blade still has when the fist closes
_WIND = Curve(WINDUP)


def phi_at(t):
    if t <= SPIN_START:
        return _WIND(t)
    if t >= SPIN_END:
        return 360.0
    x = (t - SPIN_START) / _DT
    i = min(int(x), _N - 1)
    return _PHI_TAB[i] + (_PHI_TAB[i + 1] - _PHI_TAB[i]) * (x - i)


def time_of_phi(p):
    i = bisect.bisect_left(_PHI_TAB, p)
    if i <= 0:
        return SPIN_START
    if i >= len(_PHI_TAB):
        return SPIN_END
    a, b = _PHI_TAB[i - 1], _PHI_TAB[i]
    return SPIN_START + (i - 1 + (p - a) / max(1e-9, b - a)) * _DT


KEYS = [dict(k, t=round(time_of_phi(float(k['phi'])), 4))
        for k in json.loads((HERE / 'keys_v85.json').read_text(encoding='utf-8'))['keys']]

# R4: the fist takes the blade at END_SPEED and the arm gives with it (8 deg, continuous speed), settling with
# the recovery — V82 gave 4 deg, R3's 14 deg over 0.32 s read as a second, separate move.
FOLLOW_PEAK_DEG = 8.0
FOLLOW = Hermite([(SPIN_END, 0.0, END_SPEED), (SPIN_END + 0.06, FOLLOW_PEAK_DEG, 0.0), (SPIN_END + 0.24, 0.0, 0.0)])
FOLLOW_DROP_M = 0.008
SQUEEZE = Hermite([(SPIN_END, 0.0, 3.0), (SPIN_END + 0.045, 0.08, 0.0), (SPIN_END + 0.20, 0.0, 0.0)])

# Prepare (V82): right 16 cm, elbow-led tip, left hand parked; then the key offsets.
PREPARE_RIGHT_M = 0.16
OUT = Curve([(0.00, 0.0), (0.06, 0.0), (0.16, 0.05), (0.26, 0.145), (0.34, PREPARE_RIGHT_M), (SPIN_END, PREPARE_RIGHT_M)])
PRE_LIFT = [(0.00, 0.0), (0.20, 0.0), (0.29, 0.006), (0.37, -0.026), (0.395, -0.03)]  # R4: R3 sank 4.5 cm
PRE_FWD = [(0.00, 0.0), (0.20, 0.0), (0.32, 0.01), (0.395, 0.04)]


# Extra points for single channels between keys, at a sword phase. R3: the hilt slides toward the pommel early in
# the release so its pommel end is short when it sweeps past the wrist.
EXTRA = {'station': [(40.0, -0.06)]}


def channel(name, pre=None, default=0.0):
    pts = list(pre or [(0.0, default), (0.395, default)])
    pts += [(k['t'], float(k.get(name, default))) for k in KEYS]
    pts += [(time_of_phi(p), v) for p, v in EXTRA.get(name, [])]
    return Curve(pts)


class Soft:
    """R4: Gaussian-softened channel. Monotone cubics stop on every key where a channel turns, and all channels
    turn on the same keys, so R3's hand came to rest on each key (pose-to-pose stop-start). sigma eases to 0 at the
    catch, and for channels that must equal the held fist also at N0, where the raw value stays exact."""
    RATE = 1200

    def __init__(self, curve, sigma, held_start=False):
        self.curve, self.t0, self.held = curve, (KEYS[0]['t'] if held_start else 0.0), held_start
        n = int(round((SPIN_END - self.t0) * self.RATE))
        self.tab = []
        for i in range(n + 1):
            t = self.t0 + i / self.RATE
            w = smoothstep((SPIN_END - t) / 0.04) * (smoothstep((t - self.t0) / 0.04) if held_start else 1.0)
            s = sigma * w
            if s < 1e-4:
                self.tab.append(curve(t))
                continue
            acc = norm = 0.0
            for j in range(-30, 31):
                g = math.exp(-0.5 * (j / 10.0) ** 2)
                acc += g * curve(min(t + s * j / 10.0, SPIN_END))
                norm += g
            self.tab.append(acc / norm)

    def __call__(self, t):
        if t <= self.t0 or t >= SPIN_END:
            return self.curve(t)
        x = (t - self.t0) * self.RATE
        i = min(int(x), len(self.tab) - 2)
        return self.tab[i] + (self.tab[i + 1] - self.tab[i]) * (x - i)


SOFT_TURN_S, SOFT_MOVE_S, SOFT_HILT_S = 0.015, 0.025, 0.012
# During the windup the fist tips with the sword (held), so the hand turn equals the windup turn.
HAND_TURN = Soft(channel('hand_turn', WINDUP), SOFT_TURN_S, held_start=True)
SUPINATE = Soft(Curve([(0.0, 0.0), (0.30, 0.0)] + [(k['t'], float(k['supinate'])) for k in KEYS]), SOFT_TURN_S,
                held_start=True)
EXTEND = Soft(channel('extend'), SOFT_TURN_S, held_start=True)
LIFT = Soft(channel('lift', PRE_LIFT), SOFT_MOVE_S)
FWD = Soft(channel('fwd', PRE_FWD), SOFT_MOVE_S)
GRIP = channel('grip', default=1.0)
# World offsets of the hand group (m): the reference forearm stands upright under a hand close to the lens,
# which this arm only reaches with the hand brought up and back toward the camera.
DEPTH = Soft(channel('depth'), SOFT_MOVE_S)
RIGHT = Soft(channel('right'), SOFT_MOVE_S)
SIDE = Soft(channel('side'), SOFT_HILT_S, held_start=True)
STATION = Soft(channel('station'), SOFT_HILT_S, held_start=True)
ROLL = Soft(channel('roll'), SOFT_HILT_S, held_start=True)
CONTACT = {c: channel_c for c, channel_c in (
    (c, Curve([(0.0, 1.0 if c == 'palm' else 0.0), (0.395, 1.0 if c == 'palm' else 0.0)]
              + [(k['t'], float(k['contact'].get(c, 0.0))) for k in KEYS])) for c in ('palm', 'web', 'dorsal'))}
FINGER_NAMES = ('thumb', 'index', 'middle', 'ring', 'pinky')
_FIELDS = {f: (['01', '02', '03', 'spread', 'oppose'] if f == 'thumb' else ['01', '02', '03', 'spread'])
           for f in FINGER_NAMES}
FINGER = {}
for f in FINGER_NAMES:
    for i, field in enumerate(_FIELDS[f]):
        rest = 1.0 if field in ('01', '02', '03') else 0.0
        FINGER[f + '_' + field] = Curve([(0.0, rest), (0.395, rest)] + [(k['t'], float(k['fingers'][f][i])) for k in KEYS])


def finger_shape(t):
    squeeze = SQUEEZE(t) if t >= SPIN_END else 0.0
    out = {}
    for key, curve in FINGER.items():
        v = curve(min(t, SPIN_END))
        out[key] = v + (squeeze if key[-2:] in ('01', '02', '03') else 0.0)
    return out


LEFT_PATH = Curve([(0.00, 0.0), (0.14, 0.0), (0.26, 0.75), (0.36, 1.0), (SPIN_END, 1.0)])
LEFT_OPEN = Curve([(0.00, 0.0), (0.14, 0.0), (0.24, 0.85), (0.32, 1.0), (SPIN_END, 1.0)])
LEFT_PARK = (-0.06, 0.00, -0.16)
LEFT_BULGE = (0.00, 0.01, -0.025)
LEFT_SHOULDER = (0.00, 0.00, -0.025)
LEFT_APPROACH_START = SPIN_END + 0.020
# R4: the left palm steers onto the (still recovering) grip from the start of its approach and lands a little
# later, so its approach and the right hand's recovery read as one move (R3 had two left-hand pushes).
LEFT_ATTACH_START = LEFT_APPROACH_START  # V82/R3: SPIN_END + 0.038
LEFT_PALM_CONTACT = SPIN_END + 0.17  # V82/R3: + 0.155
LEFT_CLOSE_WINDOWS = {
    'index': (LEFT_PALM_CONTACT - 0.014, LEFT_PALM_CONTACT + 0.044),
    'middle': (LEFT_PALM_CONTACT - 0.006, LEFT_PALM_CONTACT + 0.060),
    'ring': (LEFT_PALM_CONTACT + 0.002, LEFT_PALM_CONTACT + 0.077),
    'pinky': (LEFT_PALM_CONTACT + 0.010, LEFT_PALM_CONTACT + 0.092),
    'thumb': (LEFT_PALM_CONTACT + 0.038, LEFT_PALM_CONTACT + 0.124),
}
