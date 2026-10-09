"""Expanded, precision-built central accumulator for the second PowerTheme.

This module appends only the hero core to StoragePrototype/Machine.  It does
not author the room, its upper annulus, stairs, furniture, or control room.
Dimensions below are the final design dimensions in metres at scale=1.65:
7.40 m maximum diameter, ground pivot, and a 7.815 m porcelain-crown top.

The casting is newly segmented rather than a uniform enlargement of the
previous storage prop. Existing closed-plate and machined-part helpers are
reused, with no edits to the previous machinery module or source assets.
"""

import math

from mathutils import Vector
from machinery import _panel, _circle_bolts, _barrel_collision, _ceramic_contact


KIND = 'Machine'
ROOM = 'StoragePrototype'
DESIGN_SCALE = 1.65


def _frame(angle):
    return (Vector((math.cos(angle), math.sin(angle), 0)),
            Vector((-math.sin(angle), math.cos(angle), 0)))


def _point(n, t, radius, tangent=0, z=0):
    return n * radius + t * tangent + Vector((0, 0, z))


def _front_bolts(g, c, n, width, height, size=.018):
    """Four independent bolts, safely inboard of a chamfered cover's corners."""
    n, u, v = g.basis(n)
    c = Vector(c)
    for sx in (-1, 1):
        for sy in (-1, 1):
            g.bolt(KIND, c + u * sx * width / 2 + v * sy * height / 2,
                   n, size)


def _label(g, c, w, h, key, normal, atlas):
    """Use the existing Chinese atlas, consolidating its faces into Machine.

    geometry.plate uses fixed Signs/Hardware groups. Move only the newly
    appended portions, preserving any pre-existing room groups and face UVs.
    This keeps all hero detail together in the normal machine export path.
    """
    if not atlas or key not in atlas.get('rects', {}):
        return
    marks = {}
    for kind in ('Signs', 'Hardware'):
        data = g.G.get((ROOM, kind))
        marks[kind] = (len(data['v']), len(data['f'])) if data else (0, 0)
    g.plate(c, w, h, key, normal=normal, atlas=atlas)
    target = g.group(KIND)
    for kind, (v0, f0) in marks.items():
        key_ = (ROOM, kind)
        data = g.G.get(key_)
        if not data:
            continue
        off = len(target['v']) - v0
        target['v'].extend(data['v'][v0:])
        target['f'].extend(tuple(i + off for i in f) for f in data['f'][f0:])
        for channel in ('m', 'uv', 'smooth'):
            target[channel].extend(data[channel][f0:])
            del data[channel][f0:]
        del data['v'][v0:]
        del data['f'][f0:]
        if not data['v'] and not data['f']:
            del g.G[key_]


def _foot_gusset(g, n, t, z0=.49, z1=1.10):
    """Closed triangular web from the bearing skirt down to the sole plate."""
    vs = [_point(n, t, r, side * .065, z)
          for side in (-1, 1)
          for r, z in ((2.66, z0), (3.17, z0), (2.66, z1))]
    fs = [(0, 1, 2), (5, 4, 3), (3, 4, 1, 0),
          (4, 5, 2, 1), (5, 3, 0, 2)]
    g.poly(KIND, vs, fs, 'Paint')


def _base_and_casting(g):
    # A broad, shallow anchor base gives the larger body a grounded footprint.
    # Convex collision is split by physical casting, not an enclosing room hull.
    g.lathe(KIND, (0, 0, 0), (0, 0, 1),
            [(0, 3.47), (.10, 3.70), (.27, 3.70), (.43, 3.45)],
            'Paint', 32)
    _barrel_collision(g, (0, 0, 0), (0, 0, 1),
                      [(0, 3.47), (.10, 3.70), (.27, 3.70), (.43, 3.45)], 32)
    g.ring(KIND, (0, 0, .436), (0, 0, 1), 3.48, 3.19, .062, 'Steel', 64)
    _circle_bolts(g, (0, 0, .470), (0, 0, 1), 3.34, 32, .036, math.pi / 32)
    g.lathe(KIND, (0, 0, 0), (0, 0, 1),
            [(.43, 3.14), (.56, 3.14), (.75, 2.72), (.88, 2.72)],
            'Paint', 64)
    _barrel_collision(g, (0, 0, 0), (0, 0, 1),
                      [(.43, 3.14), (.56, 3.14), (.88, 2.72)], 24)
    g.ring(KIND, (0, 0, .594), (0, 0, 1), 3.117, 2.87, .045, 'Steel', 64)

    # Twelve triangulated cast feet are intentionally visible below the banks.
    for i in range(12):
        n, t = _frame((i + .5) * math.tau / 12)
        _foot_gusset(g, n, t)
        _panel(g, _point(n, t, 3.04, z=.535), (0, 0, 1),
               .31, .43, .055, .04, 'Paint')
        for dx in (-.095, .095):
            g.bolt(KIND, _point(n, t, 3.04, dx, .568), (0, 0, 1), .027)

    # Two sealed, independently flanged cast drums and a sloping upper shoulder.
    g.lathe(KIND, (0, 0, 0), (0, 0, 1),
            [(.77, 2.65), (.93, 2.80), (2.72, 2.80), (2.81, 2.74)],
            'Paint', 64)
    g.lathe(KIND, (0, 0, 0), (0, 0, 1),
            [(2.95, 2.75), (3.04, 2.80), (4.99, 2.80),
             (5.14, 2.90), (5.30, 2.84), (5.79, 2.21)], 'Paint', 64)
    _barrel_collision(g, (0, 0, 0), (0, 0, 1),
                      [(.76, 2.65), (.94, 2.81), (5.15, 2.81), (5.80, 2.21)], 24)
    _barrel_collision(g, (0, 0, 0), (0, 0, 1),
                      [(.915, 2.92), (1.025, 2.92)], 24)
    _barrel_collision(g, (0, 0, 0), (0, 0, 1),
                      [(5.08, 3.00), (5.20, 3.00), (5.87, 2.27)], 24)

    # Machined lands, gasket, and tangential clamp lugs make the split legible.
    for z, outer, inner, depth in ((.97, 2.91, 2.69, .095),
                                  (2.77, 2.96, 2.69, .11),
                                  (2.96, 2.96, 2.69, .11),
                                  (5.13, 3.00, 2.74, .095)):
        g.ring(KIND, (0, 0, z), (0, 0, 1), outer, inner, depth, 'Steel', 64)
    g.lathe(KIND, (0, 0, 2.82), (0, 0, 1), [(0, 2.865), (.09, 2.865)],
            'Rubber', 64)
    _barrel_collision(g, (0, 0, 0), (0, 0, 1), [(2.715, 2.96), (3.02, 2.96)], 24)
    _circle_bolts(g, (0, 0, 3.017), (0, 0, 1), 2.895, 40, .026)
    _circle_bolts(g, (0, 0, 5.184), (0, 0, 1), 2.935, 32, .025, math.pi / 32)
    for i in range(16):
        a = i * math.tau / 16
        n, t = _frame(a)
        _panel(g, _point(n, t, 2.925, z=2.88), n, .145, .35, .075, .025)
        for z in (2.765, 2.995):
            g.bolt(KIND, _point(n, t, 2.97, z=z), n, .019)

    # Cast roof gores converge toward the separate crown instead of one cone.
    for i in range(12):
        n, t = _frame((i + .5) * math.tau / 12)
        g.beam(KIND, _point(n, t, 2.83, z=5.25),
               _point(n, t, 2.17, z=5.82), .115, .105, 'Paint')
    g.ring(KIND, (0, 0, 5.815), (0, 0, 1), 2.27, 2.01, .10, 'Steel', 64)
    g.lathe(KIND, (0, 0, 0), (0, 0, 1),
            [(5.81, 2.04), (5.88, 2.14), (6.095, 2.14), (6.18, 2.02)],
            'Enamel', 64)
    _barrel_collision(g, (0, 0, 0), (0, 0, 1),
                      [(5.80, 2.14), (6.18, 2.14)], 24)
    g.ring(KIND, (0, 0, 6.16), (0, 0, 1), 2.135, 1.93, .064, 'Steel', 64)
    _circle_bolts(g, (0, 0, 6.197), (0, 0, 1), 2.04, 28, .023)


def _cooling_bank(g, angle, atlas):
    """Twin removable fin cassettes, headers, service couplings and open guard."""
    n, t = _frame(angle)
    _panel(g, _point(n, t, 2.815, z=3.00), n, 1.88, 4.00, .095, .14, 'Dark')
    for side in (-1, 1):
        p = _point(n, t, 2.95, side * .89, 3.015)
        g.box(KIND, p, (.10, .27, 3.89), 'Paint', angle + math.pi / 2)
    # The folded fins have actual air gaps, leading lips, and split-height banks.
    for j in range(14):
        offset = (j - 6.5) * .125
        for z, h in ((1.96, 1.54), (3.965, 1.69)):
            p = _point(n, t, 3.12, offset, z)
            g.box(KIND, p, (.045, .46, h), 'Paint', angle + math.pi / 2)
            lip = _point(n, t, 3.355, offset, z)
            g.box(KIND, lip, (.059, .025, h - .075), 'Steel', angle + math.pi / 2)
            root = _point(n, t, 2.915, offset, z)
            g.box(KIND, root, (.081, .035, h + .035), 'Paint', angle + math.pi / 2)
    for z in (1.115, 2.79, 3.085, 4.91):
        _panel(g, _point(n, t, 3.075, z=z), n, 1.94, .15, .33, .04)
        for offset in (-.84, .84):
            g.bolt(KIND, _point(n, t, 3.25, offset, z), n, .021)

    # Paired oil/water headers are round cast manifolds, connected to the shell.
    for z in (1.115, 4.91):
        g.cylinder(KIND, _point(n, t, 2.975, -.82, z),
                   _point(n, t, 2.975, .82, z), .115, 'Enamel', 20)
        for side in (-1, 1):
            g.rounded_pipe(KIND, [_point(n, t, 2.65, side * 1.06, z + .17),
                                  _point(n, t, 3.04, side * 1.06, z + .17),
                                  _point(n, t, 3.04, side * 1.06, z),
                                  _point(n, t, 3.04, side * .69, z)],
                           .079, 'Enamel', 16)
            g.flange(KIND, _point(n, t, 3.04, side * .91, z), t, .085, 8)

    # Open cage only covers this bank. It is visibly lighter than the casting.
    for offset in (-.94, 0, .94):
        p0 = _point(n, t, 3.46, offset, 1.00)
        p1 = _point(n, t, 3.46, offset, 5.035)
        g.cylinder(KIND, p0, p1, .028 if offset else .019, 'Paint', 12)
        if offset:
            for z in (1.045, 4.99):
                g.beam(KIND, _point(n, t, 3.14, offset, z),
                       _point(n, t, 3.46, offset, z), .055, .065, 'Steel')
    for z in (1.035, 2.055, 3.045, 4.07, 5.00):
        g.cylinder(KIND, _point(n, t, 3.46, -.955, z),
                   _point(n, t, 3.46, .955, z),
                   .026 if z == 5.00 else .016,
                   'Yellow' if z == 5.00 else 'Steel', 12)
    # The narrow bank box matches occupied fins, plus a thin guard facet.
    g.box(None, _point(n, t, 3.085, z=3.00), (1.89, .57, 4.00),
          yaw=angle + math.pi / 2, collision=KIND)
    g.box(None, _point(n, t, 3.455, z=3.025), (1.97, .065, 4.06),
          yaw=angle + math.pi / 2, collision=KIND)
    _panel(g, _point(n, t, 3.483, -.43, 4.62), n, .69, .22, .025, .024, 'Enamel')
    _label(g, _point(n, t, 3.499, -.43, 4.62), .63, .165, 'Cooling', n, atlas)


def _bearing_cover(g, angle, z, radius=.67):
    n, t = _frame(angle)
    c = _point(n, t, 2.755, z=z)
    g.lathe(KIND, c, n, [(0, radius * .89), (.11, radius),
                       (.25, radius), (.34, radius * .86)], 'Paint', 48)
    g.ring(KIND, c + n * .255, n, radius * 1.015, radius * .84, .07, 'Steel', 48)
    _circle_bolts(g, c + n * .296, n, radius * .925, 16, .024)
    g.lathe(KIND, c + n * .342, n,
            [(0, radius * .47), (.054, radius * .47), (.085, radius * .39)],
            'Enamel', 40)
    g.ring(KIND, c + n * .428, n, radius * .38, radius * .28, .026, 'Steel', 40)
    g.lathe(KIND, c + n * .446, n, [(0, .080), (.032, .080)], 'Steel', 6)
    _barrel_collision(g, c, n,
                      [(0, radius), (.345, radius), (.49, radius * .48)], 16)
    # Small handholds and the lower oil sample cap belong to the access casting.
    for sign in (-1, 1):
        g.rounded_pipe(KIND, [c + t * sign * radius * .61 + n * .31 + Vector((0, 0, -.14)),
                              c + t * sign * radius * .61 + n * .44 + Vector((0, 0, -.14)),
                              c + t * sign * radius * .61 + n * .44 + Vector((0, 0, .14)),
                              c + t * sign * radius * .61 + n * .31 + Vector((0, 0, .14))],
                       .029, 'Steel', 12)


def _service_hatches(g, atlas):
    # A human-scale, double-skin maintenance door occupies the front clear bay.
    n, t = _frame(-math.pi / 2)
    c = _point(n, t, 2.85, z=3.005)
    _panel(g, c, n, 1.45, 3.08, .19, .13, 'Steel')
    _panel(g, c + n * .118, n, 1.29, 2.91, .075, .10, 'Paint')
    _front_bolts(g, c + n * .165, n, 1.07, 2.67, .021)
    for z in (1.99, 4.035):
        hp = _point(n, t, 3.035, -.68, z)
        g.cylinder(KIND, hp - Vector((0, 0, .13)), hp + Vector((0, 0, .13)),
                   .045, 'Steel', 16)
        for dz in (-.095, .095):
            g.ring(KIND, hp + Vector((0, 0, dz)), (0, 0, 1), .057, .038, .035, 'Steel', 20)
    g.rounded_pipe(KIND, [_point(n, t, 3.04, .43, 2.70),
                          _point(n, t, 3.18, .43, 2.70),
                          _point(n, t, 3.18, .43, 3.08),
                          _point(n, t, 3.04, .43, 3.08)], .033, 'Steel', 12)
    for z in (2.77, 3.01):
        g.lathe(KIND, _point(n, t, 3.051, .20, z), n, [(0, .051), (.035, .051)], 'Steel', 6)
    # A recessed, physically mounted identification plate uses only the atlas.
    _panel(g, _point(n, t, 3.019, z=4.14), n, 1.04, .33, .035, .025, 'Enamel')
    _label(g, _point(n, t, 3.041, z=4.14), .93, .24, 'Core', n, atlas)
    _panel(g, _point(n, t, 3.022, z=3.61), n, .50, .37, .032, .022, 'Enamel')
    _label(g, _point(n, t, 3.044, z=3.61), .43, .29, 'Danger', n, atlas)
    g.box(None, c + n * .04, (1.45, .28, 3.08),
          yaw=-math.pi, collision=KIND)

    _bearing_cover(g, 0, 2.12, .76)
    _bearing_cover(g, math.pi, 4.02, .54)
    # Lower drain cock with a real flanged neck, valve body, and compact wheel.
    n, t = _frame(0)
    g.cylinder(KIND, _point(n, t, 2.66, z=1.01),
               _point(n, t, 3.22, z=1.01), .075, 'Enamel', 20)
    g.flange(KIND, _point(n, t, 3.015, z=1.01), n, .085, 8)
    g.lathe(KIND, _point(n, t, 3.215, z=1.01), n,
            [(0, .11), (.14, .13), (.24, .09)], 'Paint', 20)
    g.cylinder(KIND, (3.34, 0, 1.09), (3.34, 0, 1.29), .033, 'Steel', 12)
    g.torus(KIND, (3.34, 0, 1.31), (0, 0, 1), .16, .022, 'Steel', 24, 8)
    for a in (0, math.tau / 3, math.tau * 2 / 3):
        g.beam(KIND, (3.34, 0, 1.31),
               (3.34 + .15 * math.cos(a), .15 * math.sin(a), 1.31), .025, .025, 'Steel')
    # Radial sample plug below the front door, deliberately without a walkway.
    n, t = _frame(-math.pi / 2)
    g.lathe(KIND, _point(n, t, 2.75, z=1.07), n,
            [(0, .16), (.10, .18), (.15, .18)], 'Steel', 24)
    g.lathe(KIND, _point(n, t, 2.913, z=1.07), n, [(0, .095), (.055, .095)], 'Enamel', 6)


def _junction_gear_and_conduits(g, atlas):
    # The rear local junction gear is integral to the machine, not room consoles.
    n, t = _frame(math.pi / 2)
    c = _point(n, t, 2.99, z=2.27)
    _panel(g, c, n, 1.47, 1.84, .43, .12, 'Paint')
    _panel(g, c + n * .234, n, 1.30, 1.67, .060, .085, 'Enamel')
    _front_bolts(g, c + n * .269, n, 1.09, 1.46, .023)
    g.box(None, c, (1.48, .45, 1.85), yaw=math.pi, collision=KIND)
    g.box(None, _point(n, t, 3.29, z=2.27), (1.30, .22, 1.67),
          yaw=math.pi, collision=KIND)
    for off in (-.42, .42):
        for z in (1.60, 2.94):
            _panel(g, _point(n, t, 2.83, off, z), n, .22, .24, .23, .03, 'Steel')
    _panel(g, _point(n, t, 3.265, z=2.69), n, .96, .28, .025, .02, 'Paint')
    _label(g, _point(n, t, 3.282, z=2.69), .86, .20, 'MainBus', n, atlas)
    # Three independent gland sockets, dial-shaped inspection plugs and hinges.
    for off in (-.44, 0, .44):
        g.lathe(KIND, _point(n, t, 3.263, off, 2.17), n,
                [(0, .11), (.065, .125), (.10, .105)], 'Steel', 24)
        g.lathe(KIND, _point(n, t, 3.370, off, 2.17), n,
                [(0, .080), (.017, .080)], 'Dark', 24)
        g.beam(KIND, _point(n, t, 3.39, off - .037, 2.146),
               _point(n, t, 3.39, off + .043, 2.202), .012, .018, 'Enamel')
    for z in (1.78, 2.75):
        hp = _point(n, t, 3.273, -.685, z)
        g.cylinder(KIND, hp - Vector((0, 0, .085)), hp + Vector((0, 0, .085)),
                   .032, 'Steel', 12)

    # Three individually routed risers: real elbows, gasketed flanges and clamps.
    for index, off in enumerate((-.48, 0, .48)):
        pipe_r = .082 if index == 1 else .055
        rad = 3.12 if index == 1 else 3.03
        points = [_point(n, t, 1.53, off, 6.095),
                  _point(n, t, 2.08, off, 6.095),
                  _point(n, t, rad, off, 5.43),
                  _point(n, t, rad, off, 3.43),
                  _point(n, t, 2.99, off, 3.09)]
        g.rounded_pipe(KIND, points, pipe_r, 'Enamel' if index == 1 else 'Steel', 20)
        for z in (3.71, 4.89):
            g.flange(KIND, _point(n, t, rad, off, z), (0, 0, 1), pipe_r + .007, 8)
        for z in (3.41, 4.42, 5.11):
            g.ring(KIND, _point(n, t, rad, off, z), (0, 0, 1),
                   pipe_r + .027, pipe_r + .006, .066, 'Steel', 24)
            g.beam(KIND, _point(n, t, 2.72, off, z),
                   _point(n, t, rad, off, z), .075, .065, 'Steel')
        # Lower armored tail exits through its own sealed floor-facing gland.
        g.lathe(KIND, _point(n, t, 3.01, off, 1.39), (0, 0, -1),
                [(0, .09), (.11, .09), (.155, .071)], 'Steel', 20)
        g.rounded_pipe(KIND, [_point(n, t, 3.01, off, 1.30),
                              _point(n, t, 3.01, off, .89),
                              _point(n, t, 2.74, off, .66)], .05, 'Rubber', 12)
    # Side-bay auxiliary hydraulic return loop does not intersect the fin banks.
    n, t = _frame(math.pi)
    for side in (-1, 1):
        off = side * .56
        g.rounded_pipe(KIND, [_point(n, t, 2.58, off, 4.94),
                              _point(n, t, 3.14, off, 4.94),
                              _point(n, t, 3.14, off, 1.21),
                              _point(n, t, 2.71, off, 1.00)],
                       .072, 'Enamel', 16)
        for z in (1.77, 4.50):
            g.flange(KIND, _point(n, t, 3.14, off, z), (0, 0, 1), .078, 8)
        for z in (2.27, 3.16, 4.18):
            g.ring(KIND, _point(n, t, 3.14, off, z), (0, 0, 1), .099, .075, .055, 'Steel', 20)
            g.beam(KIND, _point(n, t, 2.72, off, z),
                   _point(n, t, 3.14, off, z), .07, .07, 'Steel')


def _lifting_trunnions(g):
    for angle in (0, math.pi):
        n, t = _frame(angle)
        c = _point(n, t, 2.56, z=5.42)
        g.lathe(KIND, c, n, [(0, .23), (.18, .27), (.33, .27),
                            (.36, .19), (.60, .19), (.66, .25), (.72, .25)],
                'Steel', 32)
        g.ring(KIND, c + n * .15, n, .315, .21, .085, 'Paint', 32)
        _circle_bolts(g, c + n * .197, n, .274, 8, .023)
        _barrel_collision(g, c, n, [(0, .28), (.73, .28)], 12)
        # Paired lifting ears sit above the horizontal trunnion boss.
        for side in (-1, 1):
            p = _point(n, t, 2.94, side * .20, 5.65)
            g.beam(KIND, p - Vector((0, 0, .17)), p + Vector((0, 0, .075)),
                   .095, .115, 'Paint')
            g.torus(KIND, p + Vector((0, 0, .095)), t, .147, .043, 'Steel', 28, 10)


def _terminal_crown(g, atlas):
    # Three separated phase pedestals, each with tall and short porcelain banks.
    # Every folded copper strap joins only its own paired contacts; phases never
    # touch. No single crossbar electrically shorts the crown into a generic ring.
    for x in (-1.30, 0, 1.30):
        _panel(g, (x, .06, 6.22), (0, 0, 1), .58, 1.80, .09, .07, 'Paint')
        for y, height, base in ((-.66, 1.35, 6.27), (.77, 1.05, 6.28)):
            _panel(g, (x, y, base - .025), (0, 0, 1), .46, .46, .055, .055, 'Steel')
            _ceramic_contact(g, (x, y, base), height, .19)
            for dx in (-.16, .16):
                for dy in (-.16, .16):
                    g.bolt(KIND, (x + dx, y + dy, base + .008), (0, 0, 1), .019)
            _barrel_collision(g, (x, y, base), (0, 0, 1),
                              [(0, .24), (height + .195, .24)], 12)
        # A machined terminal shoe wraps the pin, with a bolted copper lap joint.
        for y, z in ((-.66, 7.74), (.77, 7.45)):
            g.box(KIND, (x, y, z), (.25, .255, .075), 'Copper')
            for dx in (-.075, .075):
                g.bolt(KIND, (x + dx, y, z + .041), (0, 0, 1), .019)
        g.beam(KIND, (x, -.66, 7.735), (x, .24, 7.735), .145, .075, 'Copper')
        g.beam(KIND, (x, .24, 7.735), (x, .59, 7.445), .145, .075, 'Copper')
        g.beam(KIND, (x, .59, 7.445), (x, .79, 7.445), .145, .075, 'Copper')
        # A smaller insulated return enters through a sealed rear feedthrough.
        g.lathe(KIND, (x, 1.27, 6.21), (0, 0, 1),
                [(0, .14), (.075, .165), (.13, .13), (.29, .115)], 'Ceramic', 24)
        g.ring(KIND, (x, 1.27, 6.235), (0, 0, 1), .185, .10, .065, 'Steel', 24)
        g.beam(KIND, (x, .78, 7.445), (x, 1.27, 7.19), .125, .065, 'Copper')
        g.beam(KIND, (x, 1.27, 7.19), (x, 1.27, 6.48), .125, .065, 'Copper')
        g.bolt(KIND, (x, .01, 7.779), (0, 0, 1), .018)

    # Local isolated surge pair adds a secondary, visibly smaller crown rhythm.
    for x in (-.64, .64):
        _ceramic_contact(g, (x, -1.47, 6.18), .49, .105)
        g.rounded_pipe(KIND, [(x, -1.47, 6.84), (x, -1.67, 6.84),
                              (x, -1.67, 6.27)], .038, 'Copper', 12)
    _panel(g, (0, -2.10, 5.98), (0, -1, 0), 1.05, .23, .035, .025, 'Paint')
    _label(g, (0, -2.125, 5.98), .94, .17, 'MainBus', (0, -1, 0), atlas)


def build_core(g, atlas=None, scale=1.65):
    """Append the enlarged central core and its local convex collisions.

    ``scale`` retains the integration-facing enlargement parameter. At its
    default, the module uses the final metre dimensions above. Other positive
    values proportionally scale only this call's additions, never existing
    geometry, atlas UV coordinates, or another room's collision objects.

    Returns a conservative metre envelope for layout integration. No export,
    scene mutation, render, test, or global build is performed here.
    """
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError('Core scale must be a finite positive number')
    g.ROOM = ROOM
    data = g.group(KIND)
    v0 = len(data['v'])
    collision_key = (ROOM, KIND)
    c0 = len(g.C[collision_key])

    _base_and_casting(g)
    for angle in (math.pi / 4, 3 * math.pi / 4,
                  5 * math.pi / 4, 7 * math.pi / 4):
        _cooling_bank(g, angle, atlas)
    _service_hatches(g, atlas)
    _junction_gear_and_conduits(g, atlas)
    _lifting_trunnions(g)
    _terminal_crown(g, atlas)

    factor = scale / DESIGN_SCALE
    if factor != 1:
        data['v'][v0:] = [tuple(component * factor for component in vertex)
                          for vertex in data['v'][v0:]]
        for i in range(c0, len(g.C[collision_key])):
            vertices, faces = g.C[collision_key][i]
            g.C[collision_key][i] = (
                [tuple(component * factor for component in vertex)
                 for vertex in vertices], faces)
    return {'radius': 3.70 * factor, 'diameter': 7.40 * factor,
            'base_z': 0.0, 'height': 7.815 * factor,
            'group': KIND, 'room': ROOM}
