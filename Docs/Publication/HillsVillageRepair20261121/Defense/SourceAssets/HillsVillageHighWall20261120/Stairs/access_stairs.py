"""Dressed stone switchback in the same centimetre basis as the hill village wall."""
import math
import random
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools/WorldGeneration/VillagePerimeter"))
from wall_geometry import Mesh


RISE = 18
RUN = 28
FLIGHT_START = -120
TURN = 160
BACK = 280
SOCKET = -280
DECK = 360
# Position of the first tread in the published paving layout's random stream.
PAVING_SEED = 612003
PAVING_DRAW_OFFSET = 5163


def partitions(rng, lo, hi, pitch, stagger=0):
    """Running bond; avoid short slivers at the far quoin."""
    start = lo
    while start < hi:
        width = stagger if start == lo and stagger else rng.uniform(pitch * .82, pitch * 1.18)
        end = min(hi, start + width)
        if hi - end < pitch * .43:
            end = hi
        yield start, end
        start = end


def ashlar(mesh, x0, x1, y0, y1, z0, z1, slot, dressed=False):
    """Cut, slightly chamfered stones with irregular corner breaks and planar tops."""
    r = mesh.rng
    width, depth, height = x1 - x0, y1 - y0, z1 - z0
    bevel = min(.75 if dressed else 1.4, width * .10, depth * .10, height * .18)
    corners = [r.uniform(.65, 1.9) if dressed else r.uniform(1.5, 4.3) for _ in range(4)]
    corners = [min(c, width * .18, depth * .18) for c in corners]
    bite_x = r.uniform(.22, .73)
    bite = r.uniform(.11, .50) if dressed else r.uniform(.40, 1.25)
    def ring(inset, z):
        xa, xb, ya, yb = x0 + inset, x1 - inset, y0 + inset, y1 - inset
        a, b, c, d = corners
        return [(xa+a,ya,z), (xa+(xb-xa)*bite_x,ya+bite,z), (xb-b,ya,z),
                (xb,ya+b,z), (xb,yb-c,z), (xb-c,yb,z), (xa+d,yb,z),
                (xa,yb-d,z), (xa,ya+a,z)]
    offset = (r.random(), r.random())
    if dressed:
        mesh.solid([ring(bevel*.53, z0), ring(0, z0+bevel),
                    ring(0, z1-bevel*.92), ring(bevel, z1)], slot, offset)
        mesh.stones += 1
    else:
        # The low riser under a dressed nosing exposes short, rough split stones.
        # This private stream leaves all subsequent paving joints and UVs in place.
        face = RubbleFacing(mesh, random.Random(offset[0]))
        ends = [x0, x1]
        if width > 43 and offset[1] < .80:
            ends.insert(1, x0 + width * face.rng.uniform(.38, .62))
        for left, right in zip(ends, ends[1:]):
            face.place((left, right, y0, y1), z0, z1, slot, z0, z1)


def quad(mesh, a, b, c, d):
    mesh.triangle(a, b, c, "Mortar")
    mesh.triangle(a, c, d, "Mortar")


def core_profile(spans):
    heights = [top - 1.15 for _, _, top in spans]
    cuts = [spans[0][0]+4]
    for i in range(1, len(spans)):
        previous, current = heights[i-1], heights[i]
        cuts.append(spans[i][0] + (4 if current > previous else -4 if current < previous else 0))
    cuts.append(spans[-1][1]-4)
    return cuts, heights


def mortar_core(mesh, x0, x1, spans):
    # One continuous supporting mass, with a short setback for the facing and tread stones.
    cuts, heights = core_profile(spans)
    lo, hi = cuts[0], cuts[-1]
    quad(mesh, (x0,lo,0), (x0,hi,0), (x1,hi,0), (x1,lo,0))
    for i, (a, b) in enumerate(zip(cuts, cuts[1:])):
        top = heights[i]
        quad(mesh, (x0,a,top), (x1,a,top), (x1,b,top), (x0,b,top))
        quad(mesh, (x0,a,0), (x0,a,top), (x0,b,top), (x0,b,0))
        quad(mesh, (x1,a,0), (x1,b,0), (x1,b,top), (x1,a,top))
        prev = heights[i-1] if i else 0
        if top != prev:
            quad(mesh, (x0,a,prev), (x1,a,prev), (x1,a,top), (x0,a,top))
    quad(mesh, (x0,hi,0), (x0,hi,heights[-1]), (x1,hi,heights[-1]), (x1,hi,0))


def surface_slot(mesh, z):
    # A few dark split slates among the fieldstone, weighted toward the footing.
    return "YardSlate" if mesh.rng.random() < (.35 if z < 36 else .14) else "YardField"


class RubbleFacing:
    """Use the perimeter's battered fieldstone profile under a level tread or coping."""
    def __init__(self, mesh, rng):
        self.mesh = mesh
        self.rng = rng
        self.stones = 0

    def place(self, bounds, low, high, slot, floor, ceiling):
        self.floor, self.ceiling = floor, ceiling
        Mesh.stone(self, *bounds, low, high, slot)

    def solid(self, rings, slot, offset):
        # Vary the bedding gently across adjacent stones but trim at the stair envelope.
        for ring in rings:
            for p in ring:
                wave = 1.4 * math.sin(.045 * (p[0]+p[1]) + .053 * p[2])
                p[2] = max(self.floor, min(self.ceiling, p[2] + wave))
        self.mesh.solid(rings, slot, offset)
        self.mesh.stones += 1


def visible_beds(spans, bottom, top, neighbour):
    # Merge consecutive steps wherever an entire bed is available. Stones end at the
    # change in height where a tread clips the upper bed or the adjacent flight begins.
    previous = None
    for start, end, height in spans:
        floor = neighbour.get(start, 0)
        low, high = max(bottom, floor), min(top, height)
        bed = (low, high, floor == low, height == high) if high > low else None
        if previous and previous != bed:
            yield first, start, previous
        if bed and previous != bed:
            first = start
        previous = bed
    if previous:
        yield first, end, previous


def masonry_face(mesh, spans, plane, inward, along_y, neighbour=None):
    facing = RubbleFacing(mesh, mesh.rng)
    for bottom in range(0, int(max(h for _, _, h in spans)), 2*RISE):
        for start, end, bed in visible_beds(spans, bottom, bottom+2*RISE, neighbour or {}):
            low, high, at_foot, at_coping = bed
            floor = low if at_foot else low-4
            ceiling = high-6.85 if at_coping else high+4
            width = mesh.rng.uniform(34, 51)
            lead = mesh.rng.uniform(20, 38)
            for a, b in partitions(mesh.rng, start, end, width, lead):
                # Alternate full-height bond stones with pairs of smaller stones,
                # letting short bedding seams terminate against a thicker neighbour.
                split = high-low > 25 and mesh.rng.random() < .53
                rows = [low, high]
                if split:
                    rows.insert(1, low + (high-low)*mesh.rng.uniform(.42, .60))
                for i, (z0, z1) in enumerate(zip(rows, rows[1:])):
                    ends = [a, b]
                    if i and b-a > 36 and mesh.rng.random() < .54:
                        ends.insert(1, a+(b-a)*mesh.rng.uniform(.41,.60))
                    for left, right in zip(ends, ends[1:]):
                        front = mesh.rng.uniform(.0, 1.3)
                        thickness = mesh.rng.uniform(12.0, 17.5)
                        near, far = sorted((plane+inward*front, plane+inward*thickness))
                        bounds = (near,far,left,right) if along_y else (left,right,near,far)
                        facing.place(bounds, z0-.3, z1+.5, surface_slot(mesh,z0), floor, ceiling)


def tread(mesh, x0, x1, y, direction, z, index):
    # Projecting nosing faces toward the ascent; the heel is bedded into the next riser.
    ya, yb = sorted((y-direction*1.2, y+direction*(RUN-.12)))
    # The dark outer edge, tangential to travel, is flush with the rest of the tread.
    edge = 10
    paving = (x0+edge, x1) if direction == 1 else (x0, x1-edge)
    border = (x0, x0+edge) if direction == 1 else (x1-edge, x1)
    ashlar(mesh, border[0]+.10, border[1]-.10, ya, yb, z-7.0, z, "YardSlate", True)
    for a, b in partitions(mesh.rng, *paving, 72, 44 if index % 2 else 0):
        ashlar(mesh, a+.14, b-.14, ya, yb, z-7.0, z, "YardCap", True)
    rise_a, rise_b = sorted((y+direction*.18, y+direction*8.0))
    for a, b in partitions(mesh.rng, x0, x1, 57, 33 if index % 2 else 0):
        ashlar(mesh, a+.23, b-.23, rise_a, rise_b, z-RISE+.14, z-6.85, surface_slot(mesh,z))


def landing(mesh, x0, x1, y0, y1, z):
    # Bonded flagstones. Joint lines stop and restart on each transverse course.
    # Along the wall socket, the bed runs square all the way to the mating plane.
    rows = round((y1-y0) / 40.)
    for row in range(rows):
        a, b = y0+(y1-y0)*row/rows, y0+(y1-y0)*(row+1)/rows
        for left, right in partitions(mesh.rng, x0, x1, 66, 32 if row % 2 else 0):
            ashlar(mesh, left+.12, right-.12, a+.12, b-.12, z-7.0, z, "YardCap", True)


def build(mesh=None, core=mortar_core):
    if mesh is None:
        mesh = Mesh(612003)
    left, right = [], [(SOCKET, FLIGHT_START, DECK)]
    for i in range(10):
        y = FLIGHT_START + i*RUN
        left.append((y, y+RUN, RISE*(i+1)))
        right.append((y, y+RUN, DECK-i*RISE))
    left.append((TURN, BACK, DECK/2))
    right.append((TURN, BACK, DECK/2))
    # The left forecourt between the wall and the first riser stays open on grade.
    core(mesh, -156, -.28, left)
    core(mesh, 3.6, 156, right)
    masonry_face(mesh, left, -160, 1, True)
    masonry_face(mesh, right, 160, -1, True)
    masonry_face(mesh, right, 0, 1, True, {a:h for a,_,h in left})
    masonry_face(mesh, [(-157,157,DECK/2)], BACK, -1, False)
    masonry_face(mesh, [(3,157,DECK)], SOCKET, 1, False)
    # The original capstones are independent of later changes to the rubble backing.
    mesh.rng = random.Random(PAVING_SEED)
    for _ in range(PAVING_DRAW_OFFSET):
        mesh.rng.random()
    for i in range(10):
        y = FLIGHT_START + i*RUN
        for x0, x1, start, sign, top in ((-160,0,y,1,RISE*(i+1)),
                                         (0,160,y+RUN,-1,DECK-i*RISE)):
            tread(mesh, x0, x1, start, sign, top, i)
            mesh.collision(x0, x1, y, y+RUN, 0, top)
    landing(mesh, -160, 160, TURN, BACK, DECK/2)
    landing(mesh, 0, 160, SOCKET, FLIGHT_START, DECK)
    mesh.collision(-160, 160, TURN, BACK, 0, DECK/2)
    mesh.collision(0, 160, SOCKET, FLIGHT_START, 0, DECK)
    return mesh
