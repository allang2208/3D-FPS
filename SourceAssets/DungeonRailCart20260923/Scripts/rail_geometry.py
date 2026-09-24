"""Fitted industrial handrails, metres. Shared by the corridor and freight dock."""
import math
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def rounded(points, reach=.10):
    points = [Vector(p) for p in points]
    result = [points[0]]
    for a, b, c in zip(points, points[1:], points[2:]):
        if (b-a).normalized().dot((c-b).normalized()) > .9999:
            result.append(b)
            continue
        r = min(reach, (b-a).length*.30, (c-b).length*.30)
        start, end = b+(a-b).normalized()*r, b+(c-b).normalized()*r
        result.append(start)
        for i in range(1, 13):
            t = i/12
            result.append((1-t)**2*start+2*(1-t)*t*b+t*t*end)
    result.append(points[-1])
    return result


class RailAssembly:
    def __init__(self, host, kind='Frames'):
        self.h, self.kind = host, kind
        self.posts = set()

    def run(self, floor_path, supports, return_start=False, return_end=False):
        """One continuous upper tube; posts are saddle-cut to its actual underside."""
        h, kind = self.h, self.kind
        upper = [Vector(p)+Vector((0, 0, 1.10)) for p in floor_path]
        middle = [Vector(p)+Vector((0, 0, .54)) for p in floor_path]
        if return_start:
            upper.insert(0, middle[0])
        if return_end:
            upper.append(middle[-1])
        group = h['group'](kind)
        v0, f0 = len(group['v']), len(group['f'])
        h['tube'](kind, rounded(upper), .027, 'PaintedSteel', 32)
        # Used to construct coping geometry, not a runtime trace or a test.
        rail_surface = BVHTree.FromPolygons(group['v'][v0:],
            [tuple(i-v0 for i in face) for face in group['f'][f0:]])
        h['tube'](kind, rounded(middle), .019, 'PaintedSteel', 24)
        for base in supports:
            b = Vector(base)
            key = tuple(round(v, 4) for v in b)
            if key in self.posts:
                continue
            self.posts.add(key)
            h['box'](kind, b+Vector((0, 0, .008)), (.12, .12, .016), 'BareSteel')
            vertices = []
            sides = 32
            for i in range(sides):
                theta = i*math.tau/sides
                xy = b+Vector((.021*math.cos(theta), .021*math.sin(theta), 0))
                vertices.append(tuple(xy+Vector((0, 0, .016))))
            for i in range(sides):
                xy = Vector(vertices[i])
                hit = rail_surface.ray_cast(xy, Vector((0, 0, 1)), 2.5)[0]
                if hit is None:
                    raise RuntimeError('Post does not meet handrail: '+str(tuple(b)))
                # Coping remains just inside the joint; never above the handrail.
                vertices.append(tuple(hit+Vector((0, 0, .0004))))
            faces = [(i, (i+1)%sides, (i+1)%sides+sides, i+sides) for i in range(sides)]
            faces += [tuple(reversed(range(sides))), tuple(range(sides, sides*2))]
            h['poly'](kind, vertices, faces, 'PaintedSteel',
                      smooth=[True]*sides+[False, False])
            # Foot weld bead and four anchors stay below the upright shaft.
            h['tube'](kind, [b+Vector((0, 0, .016)), b+Vector((0, 0, .023))],
                      .024, 'PaintedSteel', 24)
            for dx in (-.041, .041):
                for dy in (-.041, .041):
                    p = b+Vector((dx, dy, .017))
                    h['tube'](kind, [p, p+Vector((0, 0, .003))], .010, 'BareSteel', 20)
                    h['tube'](kind, [p+Vector((0, 0, .003)), p+Vector((0, 0, .011))],
                              .007, 'BareSteel', 6)


def corridor(host, kind='EndStairRails'):
    assembly = RailAssembly(host, kind)
    # Posts stand inside the 2.05 m treads, not beyond their unsupported side edges.
    for x in (23.045, 24.955):
        path = [(x, 7.74, 0), (x, 9.54, 1), (x, 10.27, 1)]
        supports = [(x, 8.1, .2), (x, 8.82, .6), (x, 9.54, 1), (x, 10.12, 1)]
        assembly.run(path, supports, return_start=True, return_end=True)


def freight(host):
    assembly = RailAssembly(host)
    y = 14.12
    def flight(x, up=True):
        points = [(x, 12.65, 0), (x, 13.85, .6), (x, y, .6)]
        return points if up else points[::-1]
    def stair_posts(x):
        return [(x, 12.95, .15), (x, 13.55, .45)]
    def deck_posts(x0, x1):
        n = max(1, math.ceil((x1-x0)/1.15))
        return [(x0+(x1-x0)*i/n, y, .6) for i in range(n+1)]
    # Each flight flows into the adjacent deck edge instead of intersecting
    # separately authored rails at mismatched elevations and offsets.
    assembly.run([(.17, y, .6)]+flight(2.075, False),
        deck_posts(.26, 1.85)+stair_posts(2.075), return_end=True)
    assembly.run(flight(4.925)+flight(13.075, False),
        stair_posts(4.925)+deck_posts(5.15, 12.85)+stair_posts(13.075),
        return_start=True, return_end=True)
    assembly.run(flight(15.925)+[(17.83, y, .6)],
        stair_posts(15.925)+deck_posts(16.15, 17.74), return_start=True)


def legacy_corridor(scope):
    """Adapter for the original V2 integer-material authoring script."""
    palette = {'PaintedSteel': 2, 'BareSteel': 3}
    host = {
        'group': scope['group'],
        'poly': lambda k, v, f, m, **kwargs: scope['poly'](k, v, f, palette[m]),
        'box': lambda k, c, s, m: scope['box'](k, c, s, palette[m]),
        'tube': lambda k, ps, r, m, sides: scope['tube'](k, ps, r, palette[m], sides),
    }
    corridor(host)
