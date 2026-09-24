"""Shared manufactured guardrail details for the boss stairs and gallery, in metres."""
import math
from mathutils import Vector


class Guardrails:
    def __init__(self, library, oriented_box):
        self.h = library
        self.oriented_box = oriented_box
        self.posts = set()

    def rounded(self, points, reach=.10):
        points = [Vector(p) for p in points]
        path = [points[0]]
        for a, b, c in zip(points, points[1:], points[2:]):
            r = min(reach, (b-a).length*.3, (c-b).length*.3)
            start, end = b+(a-b).normalized()*r, b+(c-b).normalized()*r
            path.append(start)
            for i in range(1, 9):
                t = i/8
                path.append((1-t)**2*start+2*(1-t)*t*b+t*t*end)
        path.append(points[-1])
        return path

    def post(self, bottom, top, kind):
        b, t = Vector(bottom), Vector(top)
        key = tuple(round(v, 3) for v in b)
        if key in self.posts:
            return
        self.posts.add(key)
        h = self.h
        h['box'](kind, b+Vector((0, 0, .009)), (.13, .13, .018), 'BossStructuralSteel')
        h['tube'](kind, [b+Vector((0, 0, .018)), t], .025, 'BossStructuralSteel', 24)
        h['detail'].ring(b+Vector((0, 0, .054)), (0, 0, 1), .034, .025, .072, 'BareSteel', 24, kind)
        for dx in (-.044, .044):
            for dy in (-.044, .044):
                h['detail'].fastener(b+Vector((dx, dy, .021)), (0, 0, 1), .008, kind)
        h['detail'].ring(t-Vector((0, 0, .055)), (0, 0, 1), .030, .025, .055, 'BareSteel', 24, kind)

    def horizontal(self, a, b, base=3.6, kind='GalleryRails', yellow=True):
        a, b = Vector((*a[:2], base)), Vector((*b[:2], base))
        axis = (b-a).normalized()
        for z, r, material in ((1.10, .024, 'YellowPaint' if yellow else 'BossStructuralSteel'),
                                (.54, .021, 'BossStructuralSteel')):
            self.h['tube'](kind, [a+Vector((0, 0, z)), b+Vector((0, 0, z))], r, material, 32)
            # Coupling sleeves hide exposed butt joints and make short segments readable.
            for p in (a+axis*.08, b-axis*.08):
                self.h['detail'].ring(p+Vector((0, 0, z)), axis, r+.005, r, .07, 'BareSteel', 24, kind)
        count = max(1, math.ceil((b-a).length/1.2))
        for i in range(count+1):
            p = a+(b-a)*i/count
            self.post(p, p+Vector((0, 0, 1.10)), kind)
        self.h['bar'](kind, a+Vector((0, 0, .065)), b+Vector((0, 0, .065)), .009, .10, 'BossStructuralSteel')

    def staircase(self, spec, kind):
        n, run, rise = spec['steps_per_flight'], spec['run'], spec['rise']
        y0 = spec['y0']; y1 = y0+n*run; y2 = y1+spec['landing']; y3 = y2+n*run
        z1, z2 = n*rise, 2*n*rise
        for x in (spec['x0']+.065, spec['x1']-.065):
            # One continuous bent handrail across both flights and the intermediate landing.
            for height, radius, material in ((1.10, .024, 'YellowPaint'), (.54, .021, 'BossStructuralSteel')):
                path = [(x, y0-.20, height), (x, y0, height), (x, y1, z1+height),
                        (x, y2, z1+height), (x, y3, z2+height)]
                if height == 1.10:
                    path.insert(0, (x, y0-.20, .54))  # rounded closed return, no projecting pipe end
                self.h['tube'](kind, self.rounded(path), radius, material, 32)
            for sy, sz in ((y0, 0), (y2, z1)):
                for step in (0, 4, 8):
                    y = sy+(step+.5)*run
                    bottom = Vector((x, y, sz+(step+1)*rise))
                    top = Vector((x, y, sz+(step+.5)*rise+1.10))
                    self.post(bottom, top, kind)
                # A formed edge strip follows the stair stringer, with a real thickness.
                a, b = Vector((x, sy, sz+.16)), Vector((x, sy+n*run, sz+n*rise+.16))
                axis = (b-a).normalized(); side = Vector((1, 0, 0)); up = axis.cross(side)
                self.oriented_box(kind, (a+b)/2, (side, up, axis), (.009, .10, (b-a).length), 'BossStructuralSteel')
            for y, z in ((y1, z1), (y2, z1), (y3, z2)):
                self.post((x, y, z), (x, y, z+1.10), kind)
            self.h['bar'](kind, (x, y1, z1+.065), (x, y2, z1+.065), .009, .10, 'BossStructuralSteel')
