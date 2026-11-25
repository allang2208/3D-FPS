"""Game assembly fits for the surveyed windmill masters. Coordinates are Blender metres."""
import math

import bpy
from mathutils import Matrix, Vector

import drive
import exterior
import millkit
import milling


def _source_timbers(name):
    """Exterior lofts store each chamfered timber as two ordered octagons."""
    source = bpy.context.scene.objects[name]
    source.hide_render = True
    points = [source.matrix_world @ v.co for v in source.data.vertices]
    return [(points[i:i+8], points[i+8:i+16]) for i in range(0, len(points), 16)]


def _cap_trimmers():
    frame = exterior.Parts()
    ribs = _source_timbers("Curved oak cap ribs")
    # Three consecutive ribs around the brake bay, sixteen segments per arch.
    # Interpolate a full arch on each side of the band using the surveyed roof.
    original = -.7425
    fore, aft = -1.06, -.30
    portal_heights = {}
    for index, rings in enumerate(ribs):
        if index // 16 != 3:
            exterior.loft(frame, "Cap ribs", "oak", rings)
            continue
        for station, offset in ((fore, -16), (aft, 16)):
            fraction = abs((station-original)/.7925)
            adjacent = ribs[index+offset]
            sections = [[v.lerp(w, fraction) for v, w in zip(a, b)]
                        for a, b in zip(rings, adjacent)]
            exterior.loft(frame, "Brake bay portal ribs", "oak", sections)
            # Pick up the trimmers directly on the two new ribs.
            left, right = [sum(section, Vector())/len(section) for section in sections]
            for x in (-1., 1.):
                if min(left.x, right.x) <= x <= max(left.x, right.x):
                    f = (x-left.x)/(right.x-left.x)
                    portal_heights[station, x] = left.lerp(right, f).z

    for rings in _source_timbers("Longitudinal cap purlins"):
        a, b = rings
        mid = (sum(a, Vector()) + sum(b, Vector()))/16
        if abs(mid.x) < .1:
            # End the ridge purlin in each new portal. Its load crosses the
            # clear bay on the oak trimmers under the roof, one on each side.
            low_y, high_y = sum(v.y for v in a)/8, sum(v.y for v in b)/8
            for y in (fore, aft):
                if low_y < y < high_y:
                    join = [v.lerp(w, (y-low_y)/(high_y-low_y)) for v, w in zip(a, b)]
                    rings = (a, join) if y == fore else (join, b)
                    break
        exterior.loft(frame, "Longitudinal purlins", "oak", rings)
    for x in (-1., 1.):
        a = (x, fore, portal_heights[fore, x])
        b = (x, aft, portal_heights[aft, x])
        exterior.timber(frame, "Brake bay trimmer", a, b, .115, .115)
    frame.finish()


def _carriage_sheers():
    bpy.context.scene.objects["Longitudinal oak sheers"].hide_render = True
    frame = exterior.Parts()
    # Keep the original end joints and bolts. Square sections normal to the
    # mill centreline give matching bevels at every scarf in the offset bay.
    profile = exterior.chamfer_rect(.285, .230, .013)
    for sign in (-1, 1):
        stations = [(-2.91, 1.20), (-1.55, 1.20), (-1.02, 1.70),
                    (-.30, 1.70), (.23, 1.20), (2.91, 1.20)]
        rings = [[(sign*r+x, y, .331-z) for x, z in profile] for y, r in stations]
        exterior.loft(frame, "Offset longitudinal oak sheer", "oak", rings)
    frame.finish()


def _clearance_cut(host, cutter):
    """Leave a live machining operation for the exporter's evaluated copy."""
    cutter.hide_render = True
    mod = host.modifiers.new("Machined clearance", "BOOLEAN")
    mod.solver = "EXACT"
    mod.operation = "DIFFERENCE"
    mod.object = cutter


def _bedstone():
    # Heights from C01's bedding face (+3.13 m site Z). Above the wooden neck
    # bearing, the thrust flange, square socket and rynd sweep widening circles.
    bore = [(.170, .097), (.211, .097), (.211, .121), (.224, .121),
            (.224, .141), (.237, .141), (.237, .235), (.310, .235)]
    cutter = drive.turned("Stepped spindle counterbore",
                          [(h, r, "round") for h, r in bore], None, sides=96)
    _clearance_cut(bpy.context.scene.objects["Bedded monolithic stone"], cutter)


def _runner():
    # The steel shoulders end at +/-222 mm. The pockets run through the eye,
    # with 7 mm at the wing ends. The two bearing lands are dressed to within
    # 0.2 mm of the broad steel shoulders, which carry the weight of the runner.
    crown, base = .0392, -.051
    cutter = millkit.box("Rynd keyway broach", (0, 0, (crown+base)/2),
                         (.458, .104, crown-base), None)
    _clearance_cut(bpy.context.scene.objects["Runner with cut rynd seats"], cutter)


def _hurst():
    frame = bpy.context.scene.objects
    for source in list(frame):
        if source.name.startswith("Long-direction knee") and source.matrix_world.translation.x > 0:
            source.hide_render = True
            sign = math.copysign(1., source.matrix_world.translation.y)
            millkit.beam("East gear-bay knee", (.81, sign*1.08, 2.08),
                         (.81, sign*.89, 2.765), .125, .145, "oak")
        if source.name.startswith("Mortised top plate") and source.matrix_world.translation.x > 0:
            source.hide_render = True
        if source.name.startswith("Hurst cover board") and source.matrix_world.translation.x > .85:
            cutter = millkit.cyl("Upright clearance auger", (1.12, 0, 3.02),
                                 (1.12, 0, 3.18), .235, None, 96)
            _clearance_cut(source, cutter)
    # Keep the top seating face and both mortised ends. The shallow central
    # soffit clears the great wheel nave; the bevels slope back to full section.
    section = [(-1.19, 2.680), (-.59, 2.680), (-.37, 2.786), (.37, 2.786),
               (.59, 2.680), (1.19, 2.680), (1.19, 2.890), (-1.19, 2.890)]
    plate = milling.slab("Hurst bridged gear plate", [(.71, y, z) for y, z in section],
                         (.20, 0, 0), "darkwood")
    drive.soft(plate, .008)


def prepare(part):
    if part == "A04":
        _cap_trimmers()
    elif part == "A06":
        _carriage_sheers()
    elif part == "C01":
        _bedstone()
    elif part == "C02":
        _runner()
    elif part == "C05":
        _hurst()


def _cosine_bell(distance, extent):
    return .5 + .5*math.cos(math.pi*min(abs(distance)/extent, 1.))


def _dress_cog(data, brake):
    count, pitch, root, tip = (66, 1.32, .082, .239) if brake else (24, .48, -.064, .069)
    step = math.tau/count
    for vertex in data.vertices:
        p = vertex.co
        u, w, height = (p.x, -p.z, p.y) if brake else (p.x, p.y, p.z)
        a = (round(math.atan2(w, u)/step-.5)+.5)*step
        c, s = math.cos(a), math.sin(a)
        rise = min(1., max(0., (height-root)/(tip-root)))
        scale = 1.-.15*rise
        radial = pitch + (u*c+w*s-pitch)*scale
        tangent = (-u*s+w*c)*scale
        p.x = radial*c-tangent*s
        if brake:
            p.z = -(radial*s+tangent*c)
        else:
            p.y = radial*s+tangent*c


def fit_source(part, source, data):
    """Fit a world-transformed evaluated mesh in metres, before UV projection."""
    if part == "A04":
        # Fair the weatherboards, shingles, saddle and their frames together.
        # This shallow crown leaves the exterior watertight over the brake.
        for vertex in data.vertices:
            p = vertex.co
            if p.z > 2.0 and abs(p.x) < 1.55 and abs(p.y+.67) < 1.35:
                p.z += .040*_cosine_bell(p.x, 1.55)*_cosine_bell(p.y+.67, 1.35)
    elif part == "A07" and source.name.startswith(("Laminated pinion", "Shrunk shroud",
                                                     "Replaceable hornbeam", "Exposed stave")):
        # Re-index the lantern on the spindle. The bracket and crank retain
        # their installed pose. Blender +Z maps to negative UE yaw.
        data.transform(Matrix.Rotation(math.radians(6.), 4, "Z"))
    elif part == "B01" and source.name == "Sail tenon cross pin":
        # The A03 cheeks supply both exposed ends. Recess the centre segment's
        # end caps 1.5 mm inside each cheek to avoid two coplanar iron faces.
        for vertex in data.vertices:
            vertex.co.x *= .1565/.158
    elif part in {"B03", "B05"} and "hardwood cog" in source.name:
        _dress_cog(data, part == "B03")
    elif part == "C01" and source.name.startswith("Quartered journal bush"):
        for vertex in data.vertices:
            vertex.co.z = min(vertex.co.z, .170)
