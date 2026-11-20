"""Blender background entry point for the serving counter. All dimensions are in cm."""
import sys
from pathlib import Path

from mathutils import Vector
from mathutils.geometry import normal


sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import author


def pierced_plank(m):
    # One continuous board surrounding the inset pan. Its four cheeks share UV phase.
    xs = (-17.925, -16.3, -1.7, -.075)
    ys = (-122.42, 76., 114., 122.42)
    pts = [(x, y, z) for z in (99.4, 105.) for y in ys for x in xs]
    faces = []
    edge_use = {}
    for row in range(3):
        for column in range(3):
            if (row, column) == (1, 1):
                continue
            a = 4 * row + column
            quad = (a, a + 1, a + 5, a + 4)
            faces += [tuple(reversed(quad)), tuple(i + 16 for i in quad)]
            for edge in zip(quad, quad[1:] + quad[:1]):
                if edge[::-1] in edge_use:
                    del edge_use[edge[::-1]]
                else:
                    edge_use[edge] = True
    for a,b in edge_use:
        faces.append((a,b,b+16,a+16))
    m.solid(pts, faces, author.Y, 'OiledOak', .24)


def top(m):
    for x in (-27., 9., 27.):
        m.rect((x,0,102.2),(17.85,244.84,5.6),'OiledOak',.38)
    pierced_plank(m)
    # Breadboard ends cap the exposed endgrain and turn the grain across the width.
    for y in (-126.25,126.25):
        m.rect((0,y,102.2),(71.85,7.5,5.6),'OiledOak',.33)
    # Wrought tray inset into the tap-side plank. Slats and rims are below the serving plane.
    m.rect((-9,95,102.86),(14.6,38,.32),'Iron',.12)
    for x in (-16.05,-1.95):
        m.rect((x,95,103.88),(.5,38,2.05),'Iron',.12)
    for y in (76.28,113.72):
        m.rect((-9,y,103.88),(13.7,.56,2.05),'Iron',.12)
    for j in range(10):
        m.rect((-9,78.35+j*3.70,104.39),(13.84,2.94,1.18),'OiledOak',.24)
    # Ledges actually support the removable slats, and the gutter remains visible between them.
    for x in (-15.25,-2.75):
        m.rect((x,95,103.40),(1.45,36.9,.8),'Iron',.12)


def face_loop(centre_y, inset, x):
    lo_y, hi_y = centre_y - 35.95 + inset, centre_y + 35.95 - inset
    lo_z, hi_z = 20.80 + inset, 80.78 - inset
    return [(x,lo_y,lo_z), (x,hi_y,lo_z), (x,hi_y,hi_z), (x,lo_y,hi_z)]


def mitred_moulding(m, centre_y):
    # Profile of a quirk, raised bead and inner reveal, swept between four true mitres.
    section = ((0,25.62),(0,27.27),(.34,27.67),(.85,27.67),(1.12,27.39),
               (1.61,27.92),(2.10,28.32),(2.64,28.28),(3.10,27.91),(3.52,26.44),(3.52,25.62))
    loops = [face_loop(centre_y, inset, x) for inset,x in section]
    for side in range(4):
        a = [loop[side] for loop in loops]
        b = [loop[(side+1)%4] for loop in loops]
        grain = (Vector(b[0])-Vector(a[0])).normalized()
        if normal([Vector(p) for p in a]).dot(grain) < 0:
            a.reverse()
            b.reverse()
        m.rings([a,b],grain,'Sawn',.06)


def clip_y(points, limit, keep_greater):
    result = []
    for a,b in zip(points, points[1:] + points[:1]):
        a_in = a[1] >= limit if keep_greater else a[1] <= limit
        b_in = b[1] >= limit if keep_greater else b[1] <= limit
        if a_in:
            result.append(a)
        if a_in != b_in:
            t = (limit-a[1]) / (b[1]-a[1])
            result.append(tuple(v + (w-v)*t for v,w in zip(a,b)))
    return result


def field_board(m, surfaces, y0, y1):
    # Crop a contiguous raised field into actual glued boards with separate wood-grain origins.
    pts, faces, indices, boundary = [], [], {}, set()
    for surface in surfaces:
        clipped = clip_y(clip_y(surface,y0,True),y1,False)
        if len(clipped) < 3:
            continue
        face = []
        for p in clipped:
            p = tuple(round(v,5) for v in p)
            if p not in indices:
                indices[p] = len(pts)
                pts.append(p)
            if not face or face[-1] != indices[p]:
                face.append(indices[p])
        if len(face) > 1 and face[0] == face[-1]:
            face.pop()
        if len(face) < 3:
            continue
        faces.append(tuple(face))
        for edge in zip(face,face[1:]+face[:1]):
            if edge[::-1] in boundary:
                boundary.remove(edge[::-1])
            else:
                boundary.add(edge)
    count = len(pts)
    pts += [(24.,y,z) for _,y,z in pts[:]]
    faces += [tuple(i+count for i in reversed(face)) for face in faces[:]]
    faces += [(b,a,a+count,b+count) for a,b in sorted(boundary)]
    m.solid(pts,faces,author.Z,'OiledOak',.048)


def panel(m, centre_y):
    # The old frame and inner backing stay the same depth from the service shelves.
    for j in range(5):
        m.rect((22.55,centre_y+(j-2)*14.35,50.5),(3.,14.12,72.),'Oak',.26)
    mitred_moulding(m,centre_y)
    profiles = ((3.34,26.22),(4.82,26.22),(5.13,26.51),(8.71,28.31),(9.12,28.38))
    loops = [face_loop(centre_y,inset,x) for inset,x in profiles]
    surfaces = []
    for outer,inner in zip(loops,loops[1:]):
        for i in range(4):
            j = (i+1) % 4
            surfaces.append([outer[i],outer[j],inner[j],inner[i]])
    surfaces.append(loops[-1])
    joints = (-33.,-11.7,9.6,33.)
    for start,end in zip(joints,joints[1:]):
        field_board(m,surfaces,centre_y+start+.045,centre_y+end-.045)


if __name__ == '__main__':
    model = author.Model('Counter_Service',171903)
    author.counter(model,service=sys.modules[__name__])
    # Short forged ferrules connect the existing brackets to the timber footrail.
    for y in (-104,0,104):
        model.lathe((46.4,y-1.3,22),(46.4,y+1.3,22),
                    ((0,2.66),(.10,2.82),(.90,2.82),(1,2.66)),'Iron',20)
    model.export((0,0,0))
    author.bind_surfaces(author.OUT)
    author.relative_to_blend(author.OUT)
    author.bpy.ops.wm.save_as_mainfile(filepath=str(author.OUT/'TavernServiceCounter.blend'),relative_remap=False)
