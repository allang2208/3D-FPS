"""Cut the boot outsole from the manufacturer's bottom-view tread layout."""
import numpy as np
import shapely
from shapely.geometry import LineString, Polygon, box


# Heel to toe stations on the reference photograph, with its two shoulder edges.
# These map onto the actual boot last, preserving the separate shapes of each foot.
PHOTO_X = [60, 77, 109, 160, 225, 299, 340, 391, 434, 492, 553, 610, 671, 725, 765, 806, 831, 837]
PHOTO_TOP = [201, 149, 121, 103, 97, 94, 85, 80, 69, 48, 38, 35, 46, 63, 85, 115, 163, 200]
PHOTO_BOTTOM = [208, 268, 309, 324, 327, 306, 289, 279, 285, 303, 320, 327, 323, 311, 301, 274, 238, 205]

# Interlocking traction blocks, in image coordinates (heel on the left).
CENTRES = [
    [(106,199),(110,159),(164,150)], [(119,215),(158,177),(184,195),(150,237)],
    [(160,173),(183,148),(223,145),(192,184)],
    [(162,246),(209,182),(240,204),(213,236),(181,253)],
    [(228,170),(246,145),(292,149),(303,191),(257,192)],
    [(239,244),(262,214),(304,209),(310,244),(269,261)],
    [(194,260),(217,247),(241,270),(218,282)],
    [(119,237),(146,252),(170,275),(138,285)],
    [(432,138),(466,121),(466,177),(437,182)],
    [(489,120),(535,102),(561,126),(525,163),(485,179)],
    [(556,100),(597,88),(672,96),(641,131),(593,121)],
    [(533,176),(568,137),(629,149),(582,205)],
    [(626,185),(681,119),(717,152),(651,195)],
    [(689,106),(730,100),(758,123),(772,160)],
    [(688,196),(737,167),(774,190),(722,215)],
    [(435,198),(466,191),(485,244),(444,233)],
    [(489,192),(530,188),(563,217),(536,253),(504,248)],
    [(558,258),(608,197),(660,243),(621,268),(589,270)],
    [(652,266),(685,241),(659,217),(673,207),(751,253),(701,269)],
    [(735,224),(775,202),(772,248)],
]


def tread_blocks(boot, perimeter, base):
    sole = perimeter.buffer(-.10)
    minx, miny, maxx, maxy = sole.bounds
    stations = np.linspace(miny + .006, maxy - .006, 241)
    bounds = np.array([sole.intersection(LineString([(minx - 1, y), (maxx + 1, y)])).bounds for y in stations])

    def chart(points):
        u, v = np.array(points, dtype=float).T
        y = miny + (maxy - miny) * (u - 60) / (837 - 60)
        lo, hi = np.interp(u, PHOTO_X, PHOTO_TOP), np.interp(u, PHOTO_X, PHOTO_BOTTOM)
        across = np.clip((v - lo) / (hi - lo), .008, .992)
        left, right = np.interp(y, stations, bounds[:, 0]), np.interp(y, stations, bounds[:, 2])
        return np.column_stack((left + across * (right - left), y))

    def surface(label, polygon, height, inner=None, low=None):
        patch = polygon if inner is None else polygon.difference(inner)
        patch = shapely.set_precision(patch, .00001)
        triangles = shapely.get_parts(shapely.constrained_delaunay_triangles(shapely.segmentize(patch, .48)))
        if not len(triangles):
            return
        coords = shapely.get_coordinates(triangles).reshape(-1, 4, 2)[:, :3, :]
        q, indices = np.unique(coords.reshape(-1, 2).round(6), axis=0, return_inverse=True)
        h = height
        if inner is not None:
            high_edge = shapely.distance(shapely.points(q), inner.boundary) < .00002
            h = np.where(high_edge, height, low)
        boot.add(label, "Outsole", base(q, h), indices.reshape(-1, 3), q / 4., [0., 0., -1.])

    def lug(label, outline, angle=None, spacing=.66, depth=.68):
        outline = outline.intersection(sole)
        for i, part in enumerate(shapely.get_parts(outline)):
            if not isinstance(part, Polygon) or part.area < .095:
                continue
            tag = label + "_" + str(i)
            # A slight bevel at the lip preserves the sharp edges of the actual
            # mould. The narrow slots open to daylight along the edge of the lug.
            shoulder = part.buffer(-.080, quad_segs=2, join_style="mitre")
            if shoulder.is_empty:
                continue
            floor = depth - .115 if angle is not None else depth
            surface(tag + "_wall", part, floor, shoulder, low=.04)
            if angle is None:
                surface(tag, shoulder, depth)
                continue
            rad = np.deg2rad(angle)
            tangent = np.array((np.cos(rad), np.sin(rad)))
            axis = np.array((-tangent[1], tangent[0]))
            centre = np.array(shoulder.representative_point().coords[0])
            reach = np.hypot(part.bounds[2]-part.bounds[0], part.bounds[3]-part.bounds[1]) + 1
            count = int(np.ceil(reach / spacing))
            slots = []
            for step in range(-count, count + 1):
                mid = centre + axis * ((step + .45) * spacing)
                slots.append(LineString((mid - reach * tangent, mid + reach * tangent)).buffer(.051, cap_style="flat"))
            crests = shoulder.difference(shapely.union_all(slots))
            grooves = shoulder.difference(crests)
            surface(tag + "_slot_floors", grooves, floor)
            for k, crest in enumerate(shapely.get_parts(crests)):
                if not isinstance(crest, Polygon) or crest.area < .018:
                    continue
                top = crest.buffer(-.027, quad_segs=1, join_style="mitre")
                if top.is_empty:
                    surface(tag + "_tip_" + str(k), crest, floor)
                else:
                    surface(tag + "_sipe_" + str(k), crest, depth, top, low=floor)
                    surface(tag + "_contact_" + str(k), top, depth)

    for i, corners in enumerate(CENTRES):
        shape = Polygon(chart(corners)).buffer(.023, quad_segs=2)
        angle = -25 if i % 3 == 0 else (31 if i % 3 == 1 else 17)
        lug("mould_block_" + str(i), shape, angle)

    # Segmented shoulders have short lateral channels that alternate across
    # the waist of the shoe; the tip and heel have continuous transverse bars.
    ranges = [(113,159),(166,225),(231,297),(430,480),(490,549),
              (557,620),(629,687),(695,748),(755,782)]
    for edge in (0, 1):
        for i, (a, b) in enumerate(ranges):
            if edge and i >= 3:
                a, b = a + 5, b + 5
            us = np.linspace(a, b, 9)
            lo, hi = np.interp(us, PHOTO_X, PHOTO_TOP), np.interp(us, PHOTO_X, PHOTO_BOTTOM)
            outside = lo if edge == 0 else hi
            inside = outside + (1 if edge == 0 else -1) * (hi-lo) * (.173 if i < 3 else .154)
            points = list(zip(us, outside)) + list(zip(us[::-1], inside[::-1]))
            shape = Polygon(chart(points))
            lug(f"shoulder_{edge}_{i}", shape, -15 if edge else 14, spacing=.59)

    for i, (a, b) in enumerate([(61,77),(82,95),(99,108),(785,797),(801,812),(816,827),(829,836)]):
        ya, yb = miny + (np.array([a, b]) - 60) * (maxy-miny) / 777.
        lug("terminal_bar_" + str(i), box(minx-1, ya, maxx+1, yb), depth=.64)

    # The recessed waist retains an open centre and short fore/aft grip bars.
    for i, cut in enumerate([
        [(318,94),(348,85),(362,129),(323,130)], [(379,128),(397,83),(415,79),(413,126)],
        [(325,145),(367,146),(361,158),(332,162)], [(330,170),(361,167),(357,180),(338,184)],
        [(337,208),(361,205),(359,218),(330,222)], [(329,233),(361,225),(354,239),(324,248)],
        [(324,263),(350,249),(337,278),(322,284)], [(377,248),(410,250),(427,276),(391,268)],
        [(385,220),(417,223),(425,238),(381,235)],
    ]):
        lug("arch_bridge_" + str(i), Polygon(chart(cut)), depth=.44)
