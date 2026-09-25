"""V59: V54 poses, 0.33 s spin, right-arm orbit supports the wrist."""
import bisect

FPS = 120
END = 1.20

# V54 pose values. Spin 0.40-0.73 = 0.33 s. Hold 360; no reverse settle.
PHI = [
    (0.00, 0.0), (0.18, 0.0), (0.40, -14.0),
    (0.445, 50.0), (0.497, 110.0), (0.539, 160.0), (0.577, 205.0),
    (0.615, 255.0), (0.657, 305.0), (0.699, 345.0), (0.73, 360.0),
    (END, 360.0),
]

PSI = [
    (0.00, 0.0), (('phi', 20), 4.0), (('phi', 90), 32.0), (('phi', 150), 72.0),
    (('phi', 200), 84.0), (('phi', 255), 78.0), (('phi', 300), 45.0),
    (('phi', 340), 12.0), (0.784, 2.0), (0.884, 0.0), (END, 0.0),
]

THETA = [
    (0.00, 0.0), (0.20, 0.0), (0.40, -6.0), (('phi', 45), 14.0), (('phi', 110), 6.0),
    (('phi', 165), -4.0), (('phi', 215), -22.0), (('phi', 260), -10.0),
    (('phi', 310), -4.0), (('phi', 345), 2.0), (0.817, 0.0), (END, 0.0),
]

RHO = [(0.00, 0.0), (0.10, 0.0), (0.36, 1.0), (0.817, 1.0), (1.019, 0.0), (END, 0.0)]

LIFT = [
    (0.00, 0.0), (0.10, 0.0), (0.36, 0.035), (('phi', 60), 0.028), (('phi', 180), 0.02),
    (('phi', 300), 0.034), (0.764, 0.04), (0.898, 0.03), (1.066, 0.0), (END, 0.0),
]
FORWARD = [
    (0.00, 0.0), (0.10, 0.0), (0.36, 0.02), (('phi', 60), 0.045), (('phi', 180), 0.03),
    (('phi', 300), 0.01), (0.764, 0.0), (END, 0.0),
]
OUT = [(0.00, 0.0), (0.10, 0.0), (0.36, 0.025), (0.764, 0.02), (1.066, 0.0), (END, 0.0)]

FINGERS = {
    'pinky': [(0.00, 0.0), (0.20, 0.0), (0.40, 0.35), (('phi', 90), 0.9), (('phi', 150), 1.0),
              (('phi', 270), 1.0), (('phi', 345), 0.0), (END, 0.0)],
    'ring': [(0.00, 0.0), (0.20, 0.0), (0.40, 0.3), (('phi', 90), 0.8), (('phi', 150), 1.0),
             (('phi', 265), 1.0), (('phi', 340), 0.0), (END, 0.0)],
    'middle': [(0.00, 0.0), (0.22, 0.0), (0.40, 0.22), (('phi', 90), 0.7), (('phi', 155), 1.0),
               (('phi', 258), 1.0), (('phi', 332), 0.0), (END, 0.0)],
    'index': [(0.00, 0.0), (0.32, 0.0), (('phi', 40), 0.2), (('phi', 110), 0.55),
              (('phi', 165), 0.9), (('phi', 245), 0.9), (('phi', 318), 0.0), (END, 0.0)],
    'thumb': [(0.00, 0.0), (('phi', 60), 0.0), (('phi', 150), 0.55), (('phi', 250), 0.55),
              (('phi', 312), 0.0), (END, 0.0)],
}
OPEN_PHALANX = 0.82
OPEN_METACARPAL = 0.5

GRIP = [
    (0.00, 1.0), (0.18, 1.0), (0.40, 0.82),
    (('phi', 60), 0.38), (('phi', 95), 0.12),
    (('phi', 145), 0.0), (('phi', 255), 0.0),
    (('phi', 315), 0.42), (('phi', 345), 0.86),
    (0.784, 1.0), (END, 1.0),
]

# Drop before the spin, hold, raise back after 0.73 so recover is one lift to idle.
LEFT_PATH = [(0.00, 0.0), (0.10, 0.0), (0.36, 1.0), (0.73, 1.0), (1.12, 0.0), (END, 0.0)]
LEFT_OPEN = [(0.00, 0.0), (0.10, 0.0), (0.28, 1.0), (0.73, 1.0), (1.08, 0.0), (END, 0.0)]
# X right, Y view-forward, Z up. Lower and a little left; do not yank 22 cm down with a grip world quat.
LEFT_PARK = (-0.06, 0.00, -0.16)
LEFT_BULGE = (0.00, 0.01, -0.025)
LEFT_SHOULDER = (0.00, 0.00, -0.025)
PIVOT_LOCAL_Z = -0.040

# Extra hand+sword translation (m). Peak ~9 cm; hand/sword relative pose unchanged.
ARM_OUT = [
    (0.00, 0.0), (0.20, 0.0), (0.36, 0.02),
    (('phi', 60), 0.055), (('phi', 150), 0.04), (('phi', 240), 0.07),
    (('phi', 330), 0.03), (0.80, 0.0), (END, 0.0),
]
ARM_FWD = [
    (0.00, 0.0), (0.20, 0.0), (0.36, 0.015),
    (('phi', 60), 0.04), (('phi', 180), 0.065), (('phi', 300), 0.025),
    (0.80, 0.0), (END, 0.0),
]
ARM_LIFT = [
    (0.00, 0.0), (0.20, 0.0), (0.36, 0.01),
    (('phi', 60), -0.03), (('phi', 180), -0.015), (('phi', 300), 0.025),
    (0.80, 0.0), (END, 0.0),
]
# Shoulder follow (m). Peak ~4 cm.
SHOULDER_OUT = [
    (0.00, 0.0), (0.20, 0.0), (0.36, 0.01),
    (('phi', 60), 0.022), (('phi', 180), 0.018), (('phi', 240), 0.028),
    (('phi', 330), 0.012), (0.80, 0.0), (END, 0.0),
]
SHOULDER_FWD = [
    (0.00, 0.0), (0.20, 0.0), (0.36, 0.008),
    (('phi', 60), 0.018), (('phi', 180), 0.03), (('phi', 300), 0.012),
    (0.80, 0.0), (END, 0.0),
]
SHOULDER_UP = [
    (0.00, 0.0), (0.20, 0.0), (0.36, 0.005),
    (('phi', 60), -0.012), (('phi', 180), -0.008), (('phi', 300), 0.016),
    (0.80, 0.0), (END, 0.0),
]
# Elbow pole tilt weights 0-1: out / down so the forearm can follow the palm flip.
POLE_OUT = [
    (0.00, 0.0), (0.36, 0.2),
    (('phi', 90), 0.7), (('phi', 180), 0.45), (('phi', 270), 0.85),
    (('phi', 345), 0.2), (0.80, 0.0), (END, 0.0),
]
POLE_DOWN = [
    (0.00, 0.0), (0.36, 0.35),
    (('phi', 60), 0.9), (('phi', 180), 0.4), (('phi', 300), 0.15),
    (0.80, 0.0), (END, 0.0),
]


def _slopes(xs, ys):
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0.0:
            m[i] = 0.0
        else:
            w1 = 2.0 * h[i] + h[i - 1]
            w2 = h[i] + 2.0 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    return m


class Curve:
    def __init__(self, keys):
        pairs = sorted(keys)
        merged = []
        for x, y in pairs:
            if merged and abs(x - merged[-1][0]) < 1e-9:
                merged[-1] = (x, y)
            else:
                merged.append((x, y))
        self.xs = [p[0] for p in merged]
        self.ys = [p[1] for p in merged]
        self.ms = _slopes(self.xs, self.ys)

    def __call__(self, x):
        xs, ys, ms = self.xs, self.ys, self.ms
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = bisect.bisect_right(xs, x) - 1
        h = xs[i + 1] - xs[i]
        t = (x - xs[i]) / h
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h * ms[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h * ms[i + 1])


PHI_CURVE = Curve(PHI)
SPIN_START = 0.40
SPIN_END = 0.73


def time_of_phi(angle):
    lo, hi = SPIN_START, SPIN_END
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if PHI_CURVE(mid) < angle:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def resolve(keys):
    out = []
    for x, y in keys:
        if isinstance(x, tuple) and x[0] == 'phi':
            x = time_of_phi(x[1])
        out.append((x, y))
    return Curve(out)


def build():
    curves = {
        'phi': PHI_CURVE, 'psi': resolve(PSI), 'theta': resolve(THETA), 'rho': resolve(RHO),
        'lift': resolve(LIFT), 'forward': resolve(FORWARD), 'out': resolve(OUT),
        'grip': resolve(GRIP),
        'left_path': resolve(LEFT_PATH), 'left_open': resolve(LEFT_OPEN),
        'arm_out': resolve(ARM_OUT), 'arm_fwd': resolve(ARM_FWD), 'arm_lift': resolve(ARM_LIFT),
        'shoulder_out': resolve(SHOULDER_OUT), 'shoulder_fwd': resolve(SHOULDER_FWD),
        'shoulder_up': resolve(SHOULDER_UP),
        'pole_out': resolve(POLE_OUT), 'pole_down': resolve(POLE_DOWN),
    }
    for name, keys in FINGERS.items():
        curves['finger_' + name] = resolve(keys)
    return curves


def smoothstep(x):
    x = max(0.0, min(1.0, x))
    return x * x * x * (x * (x * 6.0 - 15.0) + 10.0)


def frames():
    return int(round(END * FPS))
