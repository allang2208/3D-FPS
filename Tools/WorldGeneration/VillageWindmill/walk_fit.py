"""Player circulation geometry. All coordinates are Blender metres in the part datum."""
import math

import building
import millkit


# D05 and D06 are still installed at the surveyed well centre. Only their timber moves.
WELL_CENTER = (1.62, -1.02)
WALL_ANGLE = math.atan2(WELL_CENTER[1], WELL_CENTER[0])
ECCENTRICITY = .169
NEWEL_OFFSET = (-ECCENTRICITY * math.cos(WALL_ANGLE), -ECCENTRICITY * math.sin(WALL_ANGLE))
START = math.radians(-134)
SWEEP = math.radians(295)


def well_radius(angle):
    """Original tread rim, measured radially from the fixed deck opening datum."""
    return 1.188 - ECCENTRICITY * math.cos(angle - WALL_ANGLE)


def _tread_radius(angle):
    # Intersect a ray from the new post with the old deck rim. The old rim is
    # eccentric, so reusing its radius at the new polar angle would move the edge.
    dx, dy = math.cos(angle), math.sin(angle)
    low, high = 1.04, 1.36
    for _ in range(24):
        r = (low + high) * .5
        x, y = NEWEL_OFFSET[0] + r * dx, NEWEL_OFFSET[1] + r * dy
        if math.hypot(x, y) > well_radius(math.atan2(y, x)):
            high = r
        else:
            low = r
    return (low + high) * .5


def _point(radius, angle, z):
    return (NEWEL_OFFSET[0] + radius * math.cos(angle),
            NEWEL_OFFSET[1] + radius * math.sin(angle), z)


def _tread(name, start, end, z, thickness, segments):
    vertices, faces = [], []
    for j in range(segments + 1):
        angle = start + (end - start) * j / segments
        radius = _tread_radius(angle)
        for r, h in ((.062, z-thickness), (radius, z-thickness), (radius, z), (.062, z)):
            vertices.append(_point(r, angle, h))
    faces.append((0, 1, 2, 3))
    faces.append(tuple(4 * segments + k for k in (3, 2, 1, 0)))
    for j in range(segments):
        for k in range(4):
            nxt = (k + 1) % 4
            faces.append((4*j + k, 4*(j+1) + k, 4*(j+1) + nxt, 4*j + nxt))
    building.rough_edges(millkit.mesh(name, vertices, faces, "oak"), .003)


def build_stair(upper):
    """Build one flight and its flush landing in the original assembly datum."""
    height, steps = (2.80, 16) if upper else (3.10, 18)
    millkit.cyl("Turned centre newel", (*NEWEL_OFFSET, 0), (*NEWEL_OFFSET, height),
                .068, "darkwood", 24)
    rail = []
    for j in range(steps):
        a = START + SWEEP * j / steps
        b = START + SWEEP * (j + 1) / steps
        z = height * (j + 1) / steps
        _tread("Wedged oak tread", a, b-.0015, z, .068, 6)
        if j >= 2:
            r = _tread_radius(a) - .025
            rail.append(_point(r, a, z+.915))
            if j % 2 == 0:
                millkit.cyl("Rail baluster", _point(r, a, z-.028), _point(r, a, z+.92),
                            .023, "lightwood", 12)
        if j % 3 == 0:
            millkit.cyl("Newel peg", _point(.058, a, z-.03), _point(.089, a, z-.03),
                        .010, "endgrain", 10)
    end = START + SWEEP
    _tread("Level timber landing", end, START + math.tau, height, .076, 16)
    r = _tread_radius(end) - .025
    rail.append(_point(r, end, height+.915))
    for a, b in zip(rail, rail[1:]):
        millkit.cyl("Hewn handrail", a, b, .029, "darkwood", 16)
    millkit.cyl("Landing post", _point(r, end, height-.04), _point(r, end, height+.93),
                .029, "lightwood", 16)


def build_guard():
    # The doorway and flour collar are on the -Y side. Turn this end of the
    # guard in before the collar so that the aisle can approach on its inner side.
    # The opposite corner follows the tower's curved wall. The east return
    # passes below the high spur wheel and stays clear of the new stair post.
    gate_start = (-.34, -1.36)
    outline = [(-1.94, -.42), (-1.94, .59), (-1.72, .97), (-1.51, 1.22),
               (.14, 1.14), (.87, .50), (.92, .08), (.62, -.12),
               (.36, -.46), (.12, -.76), gate_start, (-1.08, -.60),
               (-1.42, -.53)]
    for x, y in outline:
        millkit.box("Pinned oak post", (x, y, .52), (.09, .09, 1.04), "oak", .006)
        millkit.box("Foot shoe", (x, y, .055), (.14, .14, .09), "iron", .005)
    for a, b in zip(outline, outline[1:] + outline[:1]):
        if a == gate_start:
            # A closed service gate allows access to the drive from the bagging
            # side. The rails are carried by the gate's own hinged oak stiles.
            span = math.dist(a, b)
            direction = ((b[0]-a[0])/span, (b[1]-a[1])/span)
            first = (a[0]+direction[0]*.077, a[1]+direction[1]*.077)
            last = (b[0]-direction[0]*.077, b[1]-direction[1]*.077)
            for p in (first, last):
                millkit.box("Service gate stile", (*p, .62), (.060, .060, .72), "oak", .004)
            for z in (.34, .94):
                millkit.beam("Pinned gate rail", (*first, z), (*last, z), .065, .080, "lightwood")
                millkit.cyl("Gate hinge pin", (*first, z-.045), (*first, z+.045), .018, "iron", 12)
            millkit.beam("Gate brace", (*first, .38), (*last, .90), .045, .045, "oak")
        else:
            for z in (.34, .94):
                millkit.beam("Lapped rail", (*a, z), (*b, z), .065, .080, "lightwood")


def fit_hurst_west(source, data):
    """Refit C05's two western bents, after applying the master's world matrix.

    The attached longitudinal and transverse timbers follow the moved joints.
    The cover boards, central stone bearers, spindle and east drive bay retain
    their surveyed seats. Distances are in C05 space, before the -1.12 m install.
    """
    name = source.name
    if name.startswith(("Hurst cover board", "Spindle well short plank",
                        "Bedded stone bearer")):
        return
    for vertex in data.vertices:
        x, y, z = vertex.co
        if z >= 3.05 or x >= -.15:
            continue
        west_weight = min(1., (-.15 - x) / .45)
        vertex.co.x += .24 * west_weight
        # Move the whole feet and posts rigidly. The side rails between them
        # shorten along their length. Room at the front is needed for the
        # capsule to pass between the flour collar and the guard end.
        travel = min(1., abs(y) / .84)
        dy = .65 if y < 0 else -.39
        vertex.co.y += dy * travel * west_weight
