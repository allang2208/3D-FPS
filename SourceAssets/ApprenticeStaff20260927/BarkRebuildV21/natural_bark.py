"""Author a continuous irregular branch from the approved front/side/back design.

Centimetres, local Z up. All relief is in the indexed closed shell itself;
there are no detached bark strips, Boolean cuts, or shader-only displacement.
The accepted hand-contact section and the head/rope seat remain exact.
"""
import math
import random


def smooth(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


# z, centre x/y, nominal radius: a gently crooked branch, not a swept cylinder.
PROFILE = [
    (-80.0, -.22, .18, 2.10), (-79.4, -.23, .19, 2.46),
    (-73.0, -.45, .24, 2.50), (-63.0, -.08, -.12, 2.70),
    (-53.0, .40, -.38, 2.41), (-41.0, -.42, -.18, 2.79),
    (-29.0, -.64, .26, 2.47), (-17.0, .25, .46, 2.84),
    (-5.0, .48, -.14, 2.62), (7.0, -.27, -.40, 2.53),
    (17.0, -.39, -.13, 2.78), (22.0, 0.0, 0.0, 2.98),
    (42.0, 0.0, 0.0, 2.98), (46.0, -.24, .18, 2.64),
    (50.0, -.41, .27, 2.47), (54.0, -.12, .12, 2.70),
    (57.0, 0.0, 0.0, 2.98), (64.65, 0.0, 0.0, 2.98),
]

# Scattered healed branch stubs, scaled for the actual 160 cm staff.
# z, angle, tangential half-width, vertical half-length, protrusion.
KNOTS = [
    (-63.0, .25, .92, 1.65, .81),
    (-43.5, 2.72, 1.12, 2.15, 1.04),
    (-22.0, -1.10, 1.02, 1.85, .90),
    (2.5, .35, .91, 1.70, .79),
    (15.7, 2.30, .83, 1.50, .67),
    (48.7, -1.22, .84, 1.32, .73),
    (53.3, 1.96, .71, 1.18, .56),
]

_rng = random.Random(210927)
GROOVES = []
for index in range(13):
    GROOVES.append((
        index * math.tau / 13 + _rng.uniform(-.16, .16),
        _rng.uniform(.072, .13), _rng.uniform(.15, .32),
        _rng.uniform(0, math.tau), _rng.uniform(.037, .076),
    ))
SCARS = [(_rng.uniform(-76, 55), _rng.uniform(-math.pi, math.pi),
          _rng.uniform(3.5, 10.5), _rng.uniform(.08, .16)) for _ in range(17)]


def profile(z):
    for first, second in zip(PROFILE, PROFILE[1:]):
        if z <= second[0]:
            t = smooth((z - first[0]) / (second[0] - first[0]))
            return tuple(first[i] * (1 - t) + second[i] * t for i in (1, 2, 3))
    return PROFILE[-1][1:]


def angle_delta(a, b):
    return math.atan2(math.sin(a - b), math.cos(a - b))


def surface_point(angle, z, fitted_radius):
    # Zero displacement at both actual grip cuts and the full head/rope seat.
    below_grip = 1 - smooth((z - 17.0) / 5.0)
    above_grip = smooth((z - 42.0) / 3.0)
    natural = max(below_grip, above_grip) * (1 - smooth((z - 55.1) / 1.7))
    if natural <= 0:
        return (fitted_radius * math.cos(angle), fitted_radius * math.sin(angle), z)

    cx, cy, radius = profile(z)
    end_softening = .3 + .7 * smooth((z + 80.0) / 1.7)
    relief = .16 * math.cos(2 * angle + .033 * z + .4)
    relief += .105 * math.sin(3 * angle - .047 * z + 1.3)
    relief += .055 * math.sin(5 * angle + .13 * z) * math.sin(.051 * z + .8)

    # Long fibres wander around knots; no regularly repeated horizontal rings.
    warp = 0.0
    for kz, ka, kw, kh, protrusion in KNOTS:
        da = angle_delta(angle, ka)
        dz = z - kz
        warp += .17 * math.tanh(da * 4) * math.exp(-((dz / (kh * 2.6)) ** 2 + (da / .67) ** 2))
    for ga, width, depth, phase, frequency in GROOVES:
        path = ga + .073 * math.sin(z * frequency + phase) + .027 * math.sin(z * .23 + phase) + warp
        delta = angle_delta(angle, path)
        broken = .58 + .42 * smooth(.5 + .5 * math.sin(z * .14 + phase * 1.7))
        width *= 1 + .15 * math.sin(z * .16 + phase)
        relief -= depth * broken * math.exp(-.5 * (delta / width) ** 2)
        # One uneven raised lip, with a broad base instead of a separate flake.
        relief += depth * .21 * broken * math.exp(-.5 * ((delta - width * 1.9) / (width * 1.35)) ** 2)

    for sz, sa, length, depth in SCARS:
        longitudinal = math.exp(-((z - sz) / length) ** 6)
        path = sa + .025 * math.sin((z - sz) * .6)
        relief -= depth * longitudinal * math.exp(-.5 * (angle_delta(angle, path) / .067) ** 2)

    for kz, ka, kw, kh, protrusion in KNOTS:
        da = angle_delta(angle, ka)
        dz = z - kz
        horizontal = da * radius / kw
        vertical = (dz - .24 * math.sin(da * 3.0)) / kh
        q = horizontal * horizontal + vertical * vertical
        # A broad growth collar, flat-topped broken nub and shallow inset core.
        relief += protrusion * .22 * math.exp(-q * .58)
        relief += protrusion * .82 * math.exp(-q * q * 2.9)
        relief -= .105 * math.exp(-((math.sqrt(q) - .79) / .12) ** 2)
        relief -= .12 * math.exp(-q * 22)

    radius = max(1.85, radius + relief * end_softening)
    x = cx + radius * math.cos(angle)
    y = cy + radius * math.sin(angle)
    return (x * natural + fitted_radius * math.cos(angle) * (1 - natural),
            y * natural + fitted_radius * math.sin(angle) * (1 - natural), z)
