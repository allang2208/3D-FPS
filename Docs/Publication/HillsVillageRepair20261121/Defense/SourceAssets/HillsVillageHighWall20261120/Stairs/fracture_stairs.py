"""Disassemble the authored switchback into its original stones on split masonry cores."""
import math
from itertools import groupby

import access_stairs as stairs


# Each bay has a footing and a moving upper section. Heights lie in the mortar beds.
BAYS = ("LowerFoot", "LowerMiddle", "LowerHead", "UpperHead", "UpperMiddle",
        "UpperFoot", "TurnLeft", "TurnRight", "WallLanding")
BED = (8., 36., 72., 144., 108., 90., 90., 90., 180.)


def bay_at(x, y):
    if y >= stairs.TURN:
        return 6 if x < 0 else 7
    if y < stairs.FLIGHT_START and x >= 0:
        return 8
    third = 0 if y < stairs.FLIGHT_START + 3*stairs.RUN else 1 if y < stairs.FLIGHT_START + 6*stairs.RUN else 2
    return third if x < 0 else 3 + third


def bed_z(bay, x, y):
    # The interior parts along a slightly uneven course, shared by both halves.
    return BED[bay] + 1.8*math.sin(.057*x + bay) + 1.35*math.sin(.043*y)


class Parts:
    def __init__(self):
        intact = stairs.Mesh(612003)
        self.rng = intact.rng
        self.stones = 0
        self.pieces = [stairs.Mesh(0) for _ in range(2*len(BAYS))]

    def solid(self, rings, slot, offset):
        # Route an entire chamfered ashlar, including the original face UV offsets.
        # A transverse flagstone crossing the nominal joint stays on one side.
        x, y = [sum(p[k] for p in rings[0])/len(rings[0]) for k in (0, 1)]
        z = .5*(rings[0][0][2] + rings[-1][0][2])
        bay = bay_at(x, y)
        part = self.pieces[2*bay + int(z > bed_z(bay, x, y))]
        part.solid(rings, slot, offset)
        part.stones += 1

    def collision(self, *args):
        # A fracture piece uses only its portion of each intact step collision.
        pass


def face(mesh, a, b, c, d, material="Mortar"):
    mesh.triangle(a, b, c, material)
    mesh.triangle(a, c, d, material)


def write_core(parts, x0, x1, spans):
    cuts, heights = stairs.core_profile(spans)
    center = (x0+x1)/2
    xs = [x0 + f*(x1-x0) for f in (0., .32, .67, 1.)]
    for bay, indices in groupby(range(len(spans)), lambda i: bay_at(center, .5*(cuts[i]+cuts[i+1]))):
        cells = list(indices)
        for upper in (False, True):
            part = parts.pieces[2*bay + int(upper)]
            for i in cells:
                y0, y1, top = cuts[i], cuts[i+1], heights[i]

                def levels(x, y):
                    split = bed_z(bay, x, y)
                    return (split, top) if upper else (0., split)

                def point(x, y, high):
                    return (x, y, levels(x, y)[high])

                for xa, xb in zip(xs, xs[1:]):
                    for high in (False, True):
                        pts = [point(xa,y0,high), point(xb,y0,high), point(xb,y1,high), point(xa,y1,high)]
                        if not high:
                            pts.reverse()
                        face(part, *pts, "YardField" if high != upper else "Mortar")
                    if i == cells[0]:
                        face(part, point(xa,y0,0), point(xb,y0,0), point(xb,y0,1), point(xa,y0,1))
                    elif upper and heights[i-1] != top:
                        prev = heights[i-1]
                        face(part, (xa,y0,prev), (xb,y0,prev), (xb,y0,top), (xa,y0,top))
                    if i == cells[-1]:
                        face(part, point(xa,y1,0), point(xa,y1,1), point(xb,y1,1), point(xb,y1,0))
                face(part, point(x0,y0,0), point(x0,y0,1), point(x0,y1,1), point(x0,y1,0))
                face(part, point(x1,y0,0), point(x1,y1,0), point(x1,y1,1), point(x1,y0,1))
                lo, hi = (BED[bay], top) if upper else (0., BED[bay])
                part.collision(x0, x1, y0, y1, lo, hi)


def build():
    parts = Parts()
    stairs.build(parts, core=write_core)
    for i, mesh in enumerate(parts.pieces):
        vertices = [p for group in mesh.groups.values() for p in group["vertices"]]
        pivot = [(.5*(min(p[k] for p in vertices) + max(p[k] for p in vertices))) for k in range(3)]
        for group in mesh.groups.values():
            group["vertices"] = [[p[k]-pivot[k] for k in range(3)] for p in group["vertices"]]
        for box in mesh.boxes:
            box["center"] = [p-offset for p, offset in zip(box["center"], pivot)]
        role = BAYS[i//2] + ("Treads" if i%2 else "Footing")
        yield role, mesh, pivot
