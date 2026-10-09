"""Original stationary electrical machinery, authored in metres.

Only the two new hero bodies live here. No furniture, switchgear, luminaires,
controls, pumps, texture generation, scene export, or gameplay is supplied.
Both entry points append geometry to the supplied precision toolkit. Every
visible part, including fasteners, belongs to that hero's ``Machine`` group.
"""
import math
from mathutils import Vector


KIND = 'Machine'


def _panel(g, c, normal, width, height, depth, bevel=.04, mat='Paint'):
    """Closed, corner-chamfered plate; width/height lie in its own face plane."""
    n, u, v = g.basis(normal)
    c = Vector(c)
    w, h = width / 2, height / 2
    b = min(bevel, w * .7, h * .7)
    outline = [(-w + b, -h), (w - b, -h), (w, -h + b),
               (w, h - b), (w - b, h), (-w + b, h),
               (-w, h - b), (-w, -h + b)]
    vs = [c + n * d + u * x + v * y
          for d in (-depth / 2, depth / 2) for x, y in outline]
    fs = [tuple(reversed(range(8))), tuple(range(8, 16))]
    fs += [(i, (i + 1) % 8, (i + 1) % 8 + 8, i + 8)
           for i in range(8)]
    g.poly(KIND, vs, fs, mat)


def _barrel_collision(g, c, axis, profile, segments=16):
    """Separate low-sided convex hull. Caller supplies a convex profile."""
    n, u, v = g.basis(axis)
    c = Vector(c)
    vs = [c + n * z + (u * math.cos(j * math.tau / segments)
          + v * math.sin(j * math.tau / segments)) * r
          for z, r in profile for j in range(segments)]
    fs = [tuple(reversed(range(segments))),
          tuple((len(profile) - 1) * segments + i for i in range(segments))]
    for k in range(len(profile) - 1):
        for i in range(segments):
            j = (i + 1) % segments
            fs.append((k * segments + i, k * segments + j,
                       (k + 1) * segments + j, (k + 1) * segments + i))
    g.hull(KIND, vs, fs)


def _sole_rail(g, y):
    # A cast, chamfer-ended machine bed rather than an encompassing plinth.
    x, w, b = 3.925, .205, .12
    outline = [(-x + b, y - w), (x - b, y - w), (x, y - w + b),
               (x, y + w - b), (x - b, y + w), (-x + b, y + w),
               (-x, y + w - b), (-x, y - w + b)]
    g.prism(KIND, outline, 0, .17, 'Paint', collision=True)
    g.box(KIND, (0, y, .195), (7.52, .25, .05), 'Steel')
    for x0 in (-3.48, -2.05, 1.65, 3.40):
        for y0 in (y - .105, y + .105):
            g.bolt(KIND, (x0, y0, .222), (0, 0, 1), .026)


def _scalloped_band(g, x, z, radius=1.365, inner=1.16, depth=.075,
                    scallop=.045, lobes=16, mat='Paint'):
    # Real rounded cast fluting around each stator rib, not a texture cylinder.
    seg = 96
    vs = []
    sections = [(-depth / 2, radius - .012, True),
                (-depth / 2 + .012, radius, True),
                (depth / 2 - .012, radius, True),
                (depth / 2, radius - .012, True),
                (depth / 2, inner, False), (-depth / 2, inner, False)]
    for dx, r, shaped in sections:
        for j in range(seg):
            a = j * math.tau / seg
            rr = r - scallop * (.5 + .5 * math.cos(lobes * a)) if shaped else r
            vs.append((x + dx, math.cos(a) * rr, z + math.sin(a) * rr))
    fs = []
    smooth = []
    for k in range(len(sections)):
        kk = (k + 1) % len(sections)
        for i in range(seg):
            j = (i + 1) % seg
            fs.append((k * seg + i, k * seg + j, kk * seg + j, kk * seg + i))
            smooth.append(k in (0, 1, 2, 4))
    g.poly(KIND, vs, fs, mat, smooth=smooth)


def _radial_rib_x(g, x0, x1, z, angle, r0, r1, halfangle=.022, mat='Paint'):
    outline = [(r0, angle - halfangle), (r1, angle - halfangle),
               (r1, angle + halfangle), (r0, angle + halfangle)]
    vs = [(x, r * math.cos(a), z + r * math.sin(a))
          for x in (x0, x1) for r, a in outline]
    g.poly(KIND, vs, g.FACES, mat)


def _circle_bolts(g, c, axis, radius, count, size=.022, phase=0):
    n, u, v = g.basis(axis)
    c = Vector(c)
    for i in range(count):
        a = phase + i * math.tau / count
        g.bolt(KIND, c + radius * (u * math.cos(a) + v * math.sin(a)), n, size)


def _ceramic_contact(g, c, height=.60, radius=.125):
    x, y, z = c
    g.lathe(KIND, (x, y, z), (0, 0, 1),
            [(0, radius * .94), (.035, radius * 1.14),
             (.07, radius * 1.14), (.085, radius * .83)], 'Steel', 32)
    profile = [(0, radius * .66)]
    pitch = height / 7
    for i in range(7):
        t = i * pitch
        profile.extend([(t + pitch * .08, radius * .68),
                        (t + pitch * .29, radius * 1.24),
                        (t + pitch * .44, radius * 1.25),
                        (t + pitch * .68, radius * .73)])
    profile.append((height, radius * .64))
    g.lathe(KIND, (x, y, z + .075), (0, 0, 1), profile, 'Ceramic', 32)
    g.lathe(KIND, (x, y, z + height + .075), (0, 0, 1),
            [(0, radius * .64), (.045, radius * .64),
             (.055, radius * .48), (.12, radius * .48)], 'Copper', 20)


def build_generator(g):
    """8 m horizontal cast dynamo body, ground pivot; no moving/interactive parts."""
    g.ROOM = 'GeneratorPrototype'
    z = 1.92

    for y in (-1.13, 1.13):
        _sole_rail(g, y)

    # Four cast supports with separate contact feet and triangular stiffeners.
    for x in (-1.49, 1.12):
        g.box(KIND, (x, 0, .41), (.69, 2.54, .26), 'Paint', collision=True)
        for side in (-1, 1):
            y = side * .99
            g.box(KIND, (x, y, .685), (.55, .43, .45), 'Paint', collision=True)
            g.box(KIND, (x, y, .255), (.83, .53, .07), 'Steel')
            for dx in (-.30, .30):
                g.bolt(KIND, (x + dx, y, .292), (0, 0, 1), .032)
            for dx in (-.235, .235):
                # Closed triangular cast gussets, not separate furniture.
                a, b = y - side * .20, y + side * .18
                vs = [(x + dx + d, yy, zz) for d in (-.032, .032)
                      for yy, zz in [(a, .54), (b, .54), (a, 1.02)]]
                fs = [(2, 1, 0), (3, 4, 5), (0, 1, 4, 3),
                      (1, 2, 5, 4), (2, 0, 3, 5)]
                if side < 0:
                    fs = [tuple(reversed(face)) for face in fs]
                g.poly(KIND, vs, fs, 'Paint')

    # Chamfered stator casting. The low-sided collision is a separate solid.
    body = [(-1.99, .96), (-1.78, 1.215), (1.46, 1.215), (1.68, .985)]
    g.lathe(KIND, (0, 0, z), (1, 0, 0), body, 'Paint', 64)
    _barrel_collision(g, (0, 0, z), (1, 0, 0),
                      [(-2.0, .97), (-1.79, 1.32), (1.48, 1.32), (1.70, 1.0)])
    for x in (-1.72, -1.44, -1.16, -.88, -.60, .56, .84, 1.12, 1.40):
        _scalloped_band(g, x, z)
    for x in (-1.83, 1.54):
        g.ring(KIND, (x, 0, z), (1, 0, 0), 1.385, 1.13, .105, 'Steel', 64)
        for outward in (-1, 1):
            _circle_bolts(g, (x + outward * .059, 0, z), (outward, 0, 0),
                          1.29, 20, .021)
    # Long longitudinal parting-line strips tie the cast fluting together.
    for a in (math.radians(31), math.radians(149), math.radians(211), math.radians(329)):
        _radial_rib_x(g, -1.69, 1.38, z, a, 1.20, 1.365, .018)

    # Service hatches occupy the intentionally clear central casting bay.
    for side in (-1, 1):
        normal = (0, side, 0)
        _panel(g, (-.02, side * 1.223, 1.94), normal, .94, .78, .065, .095, 'Steel')
        _panel(g, (-.02, side * 1.264, 1.94), normal, .83, .67, .045, .075, 'Paint')
        for x in (-.365, .325):
            for zz in (1.665, 2.215):
                g.bolt(KIND, (x, side * 1.29, zz), normal, .015)
        for zz in (1.73, 2.12):
            g.cylinder(KIND, (-.45, side * 1.284, zz - .058),
                       (-.45, side * 1.284, zz + .058), .028, 'Steel', 12)
        # A recessed enamel maker's plate, deliberately without invented text.
        _panel(g, (-.03, side * 1.292, 1.997), normal, .39, .155, .011, .012, 'Enamel')
        for x in (-.195, .135):
            g.bolt(KIND, (x, side * 1.303, 1.997), normal, .006)
        g.beam(KIND, (.30, side * 1.32, 1.87), (.30, side * 1.32, 2.025),
               .035, .055, 'Steel')

    # Rear stationary coupling / flywheel guard, stepped cast silhouette.
    g.lathe(KIND, (0, 0, z), (1, 0, 0),
            [(-3.66, .34), (-3.53, .51), (-3.23, .83), (-2.94, .91)], 'Paint', 64)
    _barrel_collision(g, (0, 0, z), (1, 0, 0),
                      [(-3.67, .36), (-3.49, .59), (-3.02, 1.01)])
    g.lathe(KIND, (0, 0, z), (1, 0, 0),
            [(-3.05, .92), (-2.94, 1.275), (-2.39, 1.275), (-2.27, .87)], 'Paint', 64)
    _barrel_collision(g, (0, 0, z), (1, 0, 0),
                      [(-3.06, .93), (-2.95, 1.32), (-2.38, 1.32), (-2.26, .89)])
    g.lathe(KIND, (0, 0, z), (1, 0, 0),
            [(-2.34, .80), (-2.16, .80), (-2.04, .64), (-1.89, .64)], 'Steel', 48)
    _barrel_collision(g, (0, 0, z), (1, 0, 0), [(-2.32, .82), (-1.88, .82)])
    for x in (-2.955, -2.375):
        g.ring(KIND, (x, 0, z), (1, 0, 0), 1.325, 1.175, .06, 'Steel', 64)
        _circle_bolts(g, (x - .039, 0, z), (-1, 0, 0), 1.25, 18, .023)
    # Radial external webs support the guard's raised annular rim.
    for i in range(12):
        _radial_rib_x(g, -3.075, -3.025, z, i * math.tau / 12,
                      .58, 1.16, .027, 'Paint')
    g.ring(KIND, (-3.53, 0, z), (1, 0, 0), .56, .33, .09, 'Steel', 48)
    _circle_bolts(g, (-3.581, 0, z), (-1, 0, 0), .445, 12, .022)
    g.lathe(KIND, (-3.68, 0, z), (1, 0, 0),
            [(0, .275), (.045, .30), (.09, .30)], 'Enamel', 40)
    for x in (-2.72, -2.64):
        g.ring(KIND, (x, 0, z), (1, 0, 0), 1.280, 1.255, .024, 'Yellow', 64)
    # Rear bearing pedestal bears on the same rails; it is not a separate pump.
    g.box(KIND, (-3.27, 0, .355), (.62, 2.42, .27), 'Paint', collision=True)
    _panel(g, (-3.27, 0, .85), (0, 0, 1), .91, .70, .74, .10, 'Paint')
    g.box(None, (-3.27, 0, .85), (.91, .70, .74), collision=KIND)

    # Forward neck: longitudinal cooling ribs and a genuinely open fan guard.
    g.lathe(KIND, (0, 0, z), (1, 0, 0),
            [(1.57, .94), (1.82, 1.045), (2.56, 1.045), (2.79, .87)], 'Paint', 64)
    _barrel_collision(g, (0, 0, z), (1, 0, 0),
                      [(1.56, .96), (1.81, 1.10), (2.57, 1.10), (2.8, .88)])
    for i in range(24):
        _radial_rib_x(g, 1.80, 2.59, z, i * math.tau / 24, 1.022, 1.115, .016)
    for x in (1.78, 2.65):
        g.ring(KIND, (x, 0, z), (1, 0, 0), 1.15, .93, .065, 'Steel', 64)
    g.ring(KIND, (3.06, 0, z), (1, 0, 0), 1.182, 1.048, .51, 'Paint', 64)
    g.ring(KIND, (3.338, 0, z), (1, 0, 0), 1.196, 1.033, .07, 'Steel', 64)
    _barrel_collision(g, (0, 0, z), (1, 0, 0), [(2.78, 1.19), (3.38, 1.19)])
    _circle_bolts(g, (3.380, 0, z), (1, 0, 0), 1.112, 20, .018)
    # No opaque cap is put in the grille plane. Its slots are real openings.
    for radius in (.425, .705, .968):
        g.ring(KIND, (3.391, 0, z), (1, 0, 0), radius + .015,
               radius - .015, .035, 'Steel', 64)
    for i in range(24):
        a = i * math.tau / 24
        p0 = (3.401, .265 * math.cos(a), z + .265 * math.sin(a))
        p1 = (3.401, 1.048 * math.cos(a), z + 1.048 * math.sin(a))
        g.beam(KIND, p0, p1, .028, .036, 'Steel')
    g.lathe(KIND, (3.25, 0, z), (1, 0, 0),
            [(0, .255), (.135, .285), (.23, .25)], 'Paint', 48)
    g.ring(KIND, (3.485, 0, z), (1, 0, 0), .256, .188, .03, 'Steel', 40)
    g.lathe(KIND, (3.491, 0, z), (1, 0, 0), [(0, .188), (.025, .17)], 'Enamel', 32)
    _circle_bolts(g, (3.515, 0, z), (1, 0, 0), .215, 8, .012)

    # Joined cooling conduit remains inside a ~3.1 m transverse envelope.
    for side in (-1, 1):
        y = side * 1.34
        g.rounded_pipe(KIND, [(-1.30, side * 1.10, 1.29),
                              (-1.30, y, 1.29), (2.30, y, 1.29),
                              (2.55, y, 1.50), (2.55, side * .95, 1.66)],
                       .06, 'Enamel', 16)
        for x in (-.93, 1.80):
            g.flange(KIND, (x, y, 1.29), (1, 0, 0), .067, 8)
        for x in (-.44, .93):
            g.ring(KIND, (x, y, 1.29), (1, 0, 0), .084, .061, .052, 'Steel', 20)
            g.beam(KIND, (x, side * 1.10, 1.28), (x, y, 1.28), .075, .06, 'Steel')
        g.tube(KIND, [(-.86, side * 1.02, 2.75), (-.50, side * 1.03, 2.78),
                      (.38, side * 1.03, 2.78), (.58, side * .91, 2.92)], .025, 'Copper', 12)
    # Forged lifting eyes and cast lugs make the high silhouette purposeful.
    for x in (-1.31, 1.02):
        _panel(g, (x, 0, 3.175), (0, 0, 1), .47, .40, .10, .07, 'Paint')
        g.beam(KIND, (x, 0, 3.19), (x, 0, 3.40), .12, .14, 'Steel')
        g.torus(KIND, (x, 0, 3.44), (0, 1, 0), .165, .041, 'Steel', 32, 10)
        for yy in (-.14, .14):
            g.bolt(KIND, (x, yy, 3.23), (0, 0, 1), .022)


def build_storage(g):
    """Sealed, broad flywheel accumulator body, partial cage and three contacts."""
    g.ROOM = 'StoragePrototype'

    # Polygonal, independently bolted base. Nothing extends below ground.
    g.lathe(KIND, (0, 0, 0), (0, 0, 1),
            [(0, 2.005), (.075, 2.135), (.22, 2.135), (.30, 2.035)], 'Paint', 16)
    _barrel_collision(g, (0, 0, 0), (0, 0, 1),
                      [(0, 2.025), (.075, 2.16), (.23, 2.16), (.32, 2.05)], 16)
    g.ring(KIND, (0, 0, .302), (0, 0, 1), 2.075, 1.775, .074, 'Steel', 64)
    _circle_bolts(g, (0, 0, .344), (0, 0, 1), 1.962, 24, .031, math.pi / 24)
    g.lathe(KIND, (0, 0, 0), (0, 0, 1),
            [(.29, 1.75), (.44, 1.75), (.59, 1.825), (2.82, 1.825),
             (3.13, 1.51), (3.23, 1.51)], 'Paint', 32)
    _barrel_collision(g, (0, 0, 0), (0, 0, 1),
                      [(.32, 1.75), (.59, 1.91), (2.83, 1.91), (3.24, 1.53)], 16)
    # Two major cast halves have a dark gasket seam and machined flange lands.
    for zz in (.61, 1.545, 1.665, 2.835):
        g.ring(KIND, (0, 0, zz), (0, 0, 1), 1.907, 1.74,
               .071 if zz in (1.545, 1.665) else .055, 'Steel', 64)
    g.ring(KIND, (0, 0, 1.605), (0, 0, 1), 1.884, 1.775, .042, 'Rubber', 64)
    _circle_bolts(g, (0, 0, 1.706), (0, 0, 1), 1.852, 32, .023, math.pi / 32)

    # Vertical twin-bank radiator shrouds. Their air gaps are actual geometry.
    for i in range(8):
        a = i * math.tau / 8
        n = Vector((math.cos(a), math.sin(a), 0))
        t = Vector((-math.sin(a), math.cos(a), 0))
        if i == 0:
            # Keep the +X service bearing cover clear instead of clipping fins.
            continue
        _panel(g, n * 1.811 + Vector((0, 0, 1.70)), n, .96, 2.09, .10, .12, 'Dark')
        for j in range(8):
            offset = (j - 3.5) * .108
            p = n * 1.904 + t * offset
            for zz, hh in ((1.086, .80), (2.183, .89)):
                g.box(KIND, (p.x, p.y, zz), (.037, .212, hh), 'Paint', a + math.pi / 2)
                # Narrow folded leading face catches a restrained steel highlight.
                lip = n * 2.014 + t * offset
                g.box(KIND, (lip.x, lip.y, zz), (.039, .014, hh - .09), 'Steel', a + math.pi / 2)
        for zz in (.66, 1.525, 1.745, 2.685):
            _panel(g, n * 1.954 + Vector((0, 0, zz)), n, 1.01, .112,
                   .153, .025, 'Paint')
        for off in (-.465, .465):
            p = n * 1.94 + t * off
            for zz in (.717, 2.64):
                g.bolt(KIND, (p.x, p.y, zz), n, .015)

    # Eight cast roof gores and chamfered crown cover keep this squat and solid.
    for i in range(8):
        a = (i + .5) * math.tau / 8
        p0 = (1.80 * math.cos(a), 1.80 * math.sin(a), 2.795)
        p1 = (1.41 * math.cos(a), 1.41 * math.sin(a), 3.205)
        g.beam(KIND, p0, p1, .072, .080, 'Paint')
    g.ring(KIND, (0, 0, 3.25), (0, 0, 1), 1.535, 1.345, .083, 'Steel', 64)
    g.lathe(KIND, (0, 0, 0), (0, 0, 1),
            [(3.25, 1.345), (3.305, 1.29), (3.34, 1.29)], 'Enamel', 48)
    _circle_bolts(g, (0, 0, 3.297), (0, 0, 1), 1.438, 20, .023)

    # Large bolted inspection / bearing access cover, not a control panel.
    g.lathe(KIND, (1.792, 0, 1.78), (1, 0, 0),
            [(0, .46), (.055, .49), (.115, .49), (.17, .42)], 'Paint', 48)
    g.ring(KIND, (1.922, 0, 1.78), (1, 0, 0), .493, .406, .045, 'Steel', 48)
    _circle_bolts(g, (1.953, 0, 1.78), (1, 0, 0), .452, 12, .021)
    g.lathe(KIND, (1.965, 0, 1.78), (1, 0, 0),
            [(0, .193), (.03, .193), (.045, .16)], 'Enamel', 32)
    g.lathe(KIND, (2.012, 0, 1.78), (1, 0, 0), [(0, .055), (.025, .055)], 'Steel', 6)
    _panel(g, (1.848, 0, 2.50), (1, 0, 0), .50, .19, .014, .012, 'Enamel')
    for yy in (-.214, .214):
        g.bolt(KIND, (1.865, yy, 2.50), (1, 0, 0), .006)

    # Three electrically separated porcelain contacts and folded copper straps.
    # The busbars do not short the three terminals together.
    for x in (-.73, 0, .73):
        _panel(g, (x, -.10, 3.365), (0, 0, 1), .35, .34, .045, .035, 'Paint')
        _ceramic_contact(g, (x, -.10, 3.39), .74, .124)
        for xx in (x - .12, x + .12):
            for yy in (-.215, .015):
                g.bolt(KIND, (xx, yy, 3.391), (0, 0, 1), .013)
        g.beam(KIND, (x, -.10, 4.296), (x, .65, 4.296), .107, .052, 'Copper')
        g.beam(KIND, (x, .65, 4.296), (x, .86, 4.064), .107, .052, 'Copper')
        g.beam(KIND, (x, .86, 4.064), (x, .86, 3.49), .107, .052, 'Copper')
        for yy in (-.10, .48):
            g.bolt(KIND, (x, yy, 4.326), (0, 0, 1), .017)
        g.lathe(KIND, (x, .86, 3.355), (0, 0, 1),
                [(0, .093), (.08, .109), (.19, .077)], 'Ceramic', 24)
        g.ring(KIND, (x, .86, 3.38), (0, 0, 1), .135, .069, .055, 'Steel', 24)

    # Selected front arc has a real, open safety cage, not a solid yellow wall.
    r = 2.285
    start, stop = math.radians(210), math.radians(330)
    for zz in (.59, 1.105, 1.62, 2.135, 2.72):
        points = [(r * math.cos(start + (stop - start) * j / 48),
                   r * math.sin(start + (stop - start) * j / 48), zz)
                  for j in range(49)]
        g.tube(KIND, points, .026 if zz in (.59, 2.72) else .014,
               'Yellow' if zz == 2.72 else 'Steel', 10)
    for i in range(13):
        a = start + (stop - start) * i / 12
        x, y = r * math.cos(a), r * math.sin(a)
        major = i % 2 == 0
        g.cylinder(KIND, (x, y, .52), (x, y, 2.73),
                   .030 if major else .012, 'Paint' if major else 'Steel', 12)
        if major:
            inside = (1.96 * math.cos(a), 1.96 * math.sin(a), .35)
            outside = (x, y, .56)
            g.beam(KIND, inside, outside, .095, .065, 'Steel')
            _panel(g, (x, y, .51), (0, 0, 1), .16, .19, .035, .025, 'Paint')
            g.bolt(KIND, (x, y, .535), (0, 0, 1), .023)
        if i in (0, 12):
            for zz in (.79, 1.91):
                g.cylinder(KIND, (x, y, zz - .095), (x, y, zz + .095), .033, 'Yellow', 12)
    # Thin convex cage facets stop collision at its visible envelope. These
    # do not seal an accessible route: the entire interior is occupied casing.
    for i in range(6):
        a = start + (stop - start) * (i + .5) / 6
        rc = r * math.cos(math.radians(10))
        g.box(None, (rc * math.cos(a), rc * math.sin(a), 1.63),
              (2 * r * math.sin(math.radians(10)), .065, 2.26),
              yaw=a + math.pi / 2, collision=KIND)

    # External protected electrical conduit at the uncaged rear side.
    g.rounded_pipe(KIND, [(.81, 1.18, 3.23), (.81, 1.73, 3.23),
                          (.81, 1.91, 2.97), (.81, 1.91, .72),
                          (.65, 1.99, .40)], .063, 'Enamel', 16)
    g.flange(KIND, (.81, 1.91, 1.06), (0, 0, 1), .066, 8)
    for zz in (1.31, 2.52):
        g.ring(KIND, (.81, 1.91, zz), (0, 0, 1), .086, .064, .059, 'Steel', 20)
        g.beam(KIND, (.81, 1.62, zz), (.81, 1.91, zz), .075, .055, 'Steel')
    for xx in (.60, 1.01):
        g.rounded_pipe(KIND, [(xx, 1.28, 3.13), (xx, 1.88, 2.94),
                              (xx, 1.88, .83), (xx, 1.72, .53)], .030, 'Rubber', 12)
    # Recessed low bearing inspection plugs complete the heavy base assembly.
    for a in (0, math.pi / 2, math.pi):
        n = Vector((math.cos(a), math.sin(a), 0))
        c = n * 1.805 + Vector((0, 0, .89))
        g.lathe(KIND, c, n, [(0, .108), (.045, .13), (.075, .13)], 'Steel', 20)
        g.lathe(KIND, c + n * .077, n, [(0, .056), (.027, .056)], 'Enamel', 6)
