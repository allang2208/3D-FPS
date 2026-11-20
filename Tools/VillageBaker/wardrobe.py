"""Cut the baker's apron, towel, sash and closures in Jason StrongTall R4's rest pose."""
from pathlib import Path
import gzip
import json
import math
import os
import pickle
import subprocess
import sys
import tempfile

import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.spatial import ConvexHull, cKDTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/VillageBaker/WardrobeR1'
CARPENTER = ROOT / 'SourceAssets/VillageCarpenterNPC/Outfit/workwear.json.gz'
sys.path.insert(0, str(ROOT / 'Tools/VillageBlacksmithNPC/FinishR2/BodyOutfit'))
from cloth_surface import Bind
sys.path.insert(0, str(ROOT / 'Tools/VillageCarpenterNPC/Head'))
from fit_head import native_neck


def smooth(t):
    t = np.clip(t, 0., 1.)
    return t * t * (3 - 2 * t)


def normalized(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-9)


def collect_meshes():
    with gzip.open(CARPENTER, 'rt', encoding='utf8') as src:
        donor = json.load(src)
    pos = np.asarray(donor['positions'])
    faces = np.asarray(donor['triangles'])
    normals = np.asarray(donor['normals'])
    uvs = np.asarray(donor['uv'])
    mats = np.asarray(donor['triangle_materials'])
    items = []

    def part(name):
        a, i, b, j = donor['parts'][name]
        return pos[a:b].copy(), faces[i:j] - a, donor['weights'][a:b]

    def put(name, p, f, uv, material, weights, norm=None, indices=None):
        items.append(dict(name=name, positions=np.asarray(p).astype('f'), faces=np.asarray(f).astype('i'),
                          uv=np.asarray(uv).astype('f'), materials=material, weights=weights,
                          normals=None if norm is None else np.asarray(norm).astype('f'), indices=indices))

    def garment(name):
        a, i, b, j = donor['parts'][name]
        p, f, w = part(name)
        ids = None
        if name == 'boots':
            slots = ['Boot', 'Sole']
            ids = (mats[i:j] == 5).astype('i')
            # Tuck the shafts inside the trouser hem, retaining the vamp and welt.
            t = .87 * smooth((p[:, 2] - 7.) / 11.)
            for sign in (-1, 1):
                mask = sign * p[:, 0] > 0
                rad = p[mask, :2] - [sign * 13.7, -2.3]
                p[mask, :2] -= .16 * t[mask, None] * rad
        elif name == 'trousers':
            slots = ['Pants']
        elif name.startswith('Twice turned'):
            slots = ['Cuff']
        elif name.startswith('Rolled cuff'):
            slots = ['Thread']
        else:
            slots = ['Shirt']
        put(name, p, f[:, ::-1], uvs[i:j, ::-1], slots, w, normals[i:j, ::-1], ids)

    for name in donor['parts']:
        if (name in ('Continuous linen shirt', 'Soft collar stand with inner facing', 'trousers', 'boots')
                or name.startswith(('Twice turned sleeve', 'Overlapping front placket',
                                    'Flat-felled shoulder seam', 'Rolled cuff lockstitch'))):
            garment(name)

    pshirt, fshirt, wshirt = part('Continuous linen shirt')
    ptrouser, ftrouser, wtrouser = part('trousers')
    pwaist, _, wwaist = part('Skived and rounded waist belt')
    waist_binding = Bind(pwaist, wwaist)
    shirt_binding = Bind(pshirt, wshirt)
    leg_bind = []
    for sign in (-1, 1):
        ids = np.flatnonzero(sign * ptrouser[:, 0] > .05)
        leg_bind.append(Bind(ptrouser[ids], [wtrouser[i] for i in ids]))

    def cloth_binding(p):
        # The flat front crosses the leg gap. Feather the left and right weights
        # over the centre rather than introducing a sharp nearest-leg boundary.
        waist = smooth((p[:, 2] - 90) / 12.)
        left = smooth((p[:, 0] + 8.) / 16.)
        base = waist_binding(p)
        right_leg, left_leg = [binder(p) for binder in leg_bind]
        result = []
        for i, xyz in enumerate(p):
            row = {}
            layers = ((base[i], waist[i]), (left_leg[i], left[i] * (1 - waist[i])),
                      (right_leg[i], (1 - left[i]) * (1 - waist[i])))
            for values, amount in layers:
                for bone, w in values:
                    row[bone] = row.get(bone, 0.) + w * amount
            pairs = sorted(row.items(), key=lambda t: -t[1])[:8]
            total = sum(w for _, w in pairs)
            result.append([(bone, w / total) for bone, w in pairs if w > 1e-7])
        return result

    def grid(name, rows, mat, binder, uv=None, flip=False, thickness=0.):
        rows = np.asarray(rows)
        h, w = rows.shape[:2]
        p = rows.reshape(-1, 3)
        xy = np.arange(len(p)).reshape(h, w)
        a, b, c, d = xy[:-1, :-1], xy[:-1, 1:], xy[1:, 1:], xy[1:, :-1]
        f = np.stack((a, b, c, a, c, d), axis=-1).reshape(-1, 3)
        if flip:
            f = f[:, ::-1]
        if uv is None:
            col = np.r_[0., np.cumsum(np.linalg.norm(np.diff(rows, axis=1), axis=2).mean(0))]
            row = np.r_[0., np.cumsum(np.linalg.norm(np.diff(rows, axis=0), axis=2).mean(1))]
            uv = np.stack(np.meshgrid(col, row), axis=-1) / 18.
        base_uv = np.asarray(uv).reshape(-1, 2)
        if thickness:
            normal = normalized(np.cross(np.gradient(rows, axis=1), np.gradient(rows, axis=0)))
            if flip:
                normal = -normal
            back = (rows - thickness * normal).reshape(-1, 3)
            border = np.r_[xy[0], xy[1:, -1], xy[-1, -2::-1], xy[-2:0:-1, 0], xy[0, 0]]
            e, g = border[:-1], border[1:]
            sides = np.stack((g, e, e + len(p), g, e + len(p), g + len(p)), axis=1).reshape(-1, 3)
            if flip:
                sides = sides[:, ::-1]
            f = np.vstack((f, f[:, ::-1] + len(p), sides))
            base_uv = np.concatenate((base_uv, base_uv))
            p = np.concatenate((p, back))
        put(name, p, f, base_uv[f], [mat], binder(p))

    # Convex sections across the clothed hips keep each apron panel outside both
    # thighs. The lower rows hang from the hip instead of following the crotch.
    trunk = np.concatenate((ptrouser[ftrouser], pshirt[fshirt][np.max(abs(pshirt[fshirt][:, :, 0]), axis=1) < 23.]))
    z_levels = np.arange(38., 111.)
    angle_count = 180
    angles = np.arange(angle_count) * math.tau / angle_count
    direction = np.stack((np.sin(angles), np.cos(angles)), axis=1)
    origin = np.array([0., .45])
    radius = []
    for z in z_levels:
        signed = trunk[:, :, 2] - z
        chosen = (signed.min(1) <= 0) & (signed.max(1) > 0)
        tri, signed = trunk[chosen], signed[chosen]
        face, edge = np.where((signed > 0) != np.roll(signed > 0, -1, axis=1))
        next_edge = (edge + 1) % 3
        k = signed[face, edge] / (signed[face, edge] - signed[face, next_edge])
        pts = tri[face, edge] + k[:, None] * (tri[face, next_edge] - tri[face, edge])
        eq = ConvexHull(pts[:, :2] - origin).equations
        denominator = eq[:, :2] @ direction.T
        hit = np.min(np.where(denominator > 1e-7, -eq[:, 2, None] / np.maximum(denominator, 1e-7), np.inf), axis=0)
        radius.append(hit)
    radius = gaussian_filter(radius, (.65, 1.3), mode=('nearest', 'wrap'))
    def section(z, angle):
        z, angle = np.broadcast_arrays(z, angle)
        h = np.clip(z - z_levels[0], 0, len(z_levels) - 1.001)
        a = angle % math.tau * (angle_count / math.tau)
        lo, j = h.astype(int), a.astype(int)
        high = (j + 1) % angle_count
        fz, fa = h - lo, a - j
        return ((1 - fz) * ((1 - fa) * radius[lo, j] + fa * radius[lo, high])
                + fz * ((1 - fa) * radius[lo + 1, j] + fa * radius[lo + 1, high]))

    def place(z, a, rad):
        return np.stack((origin[0] + np.sin(a) * rad, origin[1] + np.cos(a) * rad, z), axis=-1)

    def sheet(t, u):
        a = (2 * u - 1) * (2.22 - .23 * t) + .015 * np.sin(3.1 * t)
        z = 102.6 - 61.0 * t + .68 * np.sin(1.65 * a + .25) * t + .38 * np.cos(2.55 * a + t)
        floor = section(88., a) + .16 + 1.75 * t ** 1.65
        envelope = np.maximum(section(z, a), (1. - smooth((z - 87.) / 13.)) * floor)
        pleat = (.36 * np.sin(5.2 * a + 1.7 * t) + .25 * np.cos(8.5 * a - .9 * t)
                 + .17 * np.sin(17 * a + 2.1 * t))
        fullness = .57 + 1.2 * smooth(t / .35) + (.25 + .75 * t) * pleat
        gather = np.exp(-((t - .060 - .014 * np.cos(2.1 * a)) / .029) ** 2)
        return place(z, a, envelope + fullness + .38 * gather)

    t, u = np.meshgrid(np.linspace(0, 1, 56), np.linspace(0, 1, 101), indexing='ij')
    sheet_uv = np.stack((u, t), axis=-1)
    grid('Waist apron | two woven madder stripes', sheet(t, u), 'Apron', cloth_binding, sheet_uv, thickness=.14)
    # Fold a narrow facing back inside the bottom edge, using the same warp/weft phase.
    edge = sheet(t[-1], u[-1])
    inward = normalized(np.column_stack((edge[:, 0], edge[:, 1] - origin[1], np.zeros(len(edge)))))
    hems = [edge - .055 * inward, edge - .17 * inward + [0., 0., -.11], edge - .29 * inward + [0., 0., .12],
            edge - .31 * inward + [0., 0., 1.10]]
    hemuv = np.stack([np.stack([u[-1], np.full_like(u[-1], v)], axis=1) for v in (.999, .997, .993, .981)])
    grid('Apron | doubled bottom hem', hems, 'Apron', cloth_binding, hemuv)

    # The rear tail of the blue shirt is visible in the opening underneath the sash.
    t, a = np.meshgrid(np.linspace(0, 1, 22), np.linspace(-math.pi, math.pi, 123), indexing='ij')
    rear = smooth((.33 - np.cos(a)) / .98)
    z = 104.3 - t * (4.5 + 13.6 * rear) + .65 * t * rear * np.sin(2 * a + .4)
    r = section(z, a) + .18 + rear * t * (.41 + .20 * np.cos(7 * a - t))
    grid('Linen | untucked rear shirttail', place(z, a, r), 'Shirt', cloth_binding, thickness=.09)

    def sash(v, a):
        z = 106.25 - 6.25 * v + .32 * np.sin(a * 2 + .47) - .21 * np.cos(a * 3) * v
        r = section(z, a) + 1.10 + .31 * np.sin(math.pi * v)
        r += .22 * np.sin(4 * math.pi * v + .72 * np.sin(2 * a + .6)) * np.sin(math.pi * v)
        return place(z, a, r)

    v, a = np.meshgrid(np.linspace(0, 1, 23), np.linspace(-math.pi, math.pi, 137), indexing='ij')
    grid('Waistband | folded linen wrap', sash(v, a), 'Sash', waist_binding, thickness=.19)
    # One narrow binding winds over the broad sash and crosses just before the back knot.
    for side in (-1, 1):
        v, a = np.meshgrid(np.linspace(0, 1, 6), np.linspace(-.06, math.pi, 82), indexing='ij')
        a *= side
        lane = .58 + .18 * np.sin(.94 * a + .35) + .19 * v
        p = sash(lane, a)
        n = normalized(p * [1., 1., 0.])
        p += n * (.21 + .11 * np.sin(v * math.pi))[:, :, None]
        grid('Waistband | narrow front tie ' + str(side), p, 'Sash', waist_binding, flip=side < 0, thickness=.10)

    def cloth_ribbon(name, guides, widths, twists, binding):
        from scipy.interpolate import CubicSpline
        path = np.asarray(guides)
        arc = np.r_[0., np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
        s = np.linspace(0., arc[-1], max(17, int(arc[-1] * 2)))
        curve = CubicSpline(arc, path, axis=0, bc_type='natural')
        centre = curve(s)
        tangent = normalized(curve(s, 1))
        flat = normalized(np.cross(tangent, [0., 1., 0.]))
        depth = normalized(np.cross(tangent, flat))
        twist = np.interp(s, arc, twists)
        across = flat * np.cos(twist[:, None]) + depth * np.sin(twist[:, None])
        face = normalized(np.cross(across, tangent))
        x = np.linspace(-1., 1., 7)
        half = np.interp(s, arc, widths) * .5
        rows = centre[:, None] + (across * half[:, None])[:, None] * x[None, :, None]
        rows += face[:, None] * (.14 * (1 - x ** 2))[None, :, None]
        grid(name, rows, 'Sash', binding, thickness=.12)

    rear_contact = sash(np.array([.54]), np.array([math.pi]))[0]
    knot_y, knot_z = rear_contact[1] - .86, rear_contact[2]
    for side in (-1, 1):
        guides = [(0, -.2, .2), (2.9, -.55, 1.23), (6.7, -.45, .92), (8.75, -.56, -.68),
                  (7.42, -1.05, -2.61), (4.55, -1.48, -2.65), (1.18, -1.30, -.44)]
        bow = [(side * x, knot_y + y, knot_z + z + (x * .095 * side)) for x, y, z in guides]
        cloth_ribbon('Back tie | loop ' + str(side), bow, [1.8, 1.85, 1.62, 1.48, 1.63, 1.83, 1.80],
                     [0, .3 * side, .64 * side, 1.18 * side, 1.58 * side, 2.50 * side, 2.82 * side], waist_binding)
        end = 24.3 + side * .8
        guides = []
        for x, drop, off in ((.45, .35, 1.72), (1.65, 3., 1.55), (2.30, 6.5, .40),
                             (2.80, 12., .25), (3.07, 18., .58), (3.68, end, .81)):
            xx = x * side
            zz = knot_z - drop
            aa = math.pi - math.asin(xx / max(section(zz, math.pi), 11.))
            yy = min(knot_y, origin[1] + math.cos(aa) * (section(zz, aa) + 1.0)) - off
            guides.append((xx, yy, zz))
        cloth_ribbon('Back tie | free end ' + str(side), guides, [1.54, 1.77, 2.03, 2.45, 2.54, 2.57],
                     [side * .57, side * .31, side * -.14, side * .24, side * .39, side * .16], cloth_binding)
    rv, ra = np.meshgrid(np.linspace(0, 1, 9), np.linspace(0, math.tau, 27), indexing='ij')
    knot = np.stack(((1.52 - .26 * np.sin(rv * math.pi)) * np.cos(ra) + .22 * rv,
                     knot_y - .55 + (.98 - .14 * np.sin(rv * math.pi)) * np.sin(ra),
                     knot_z + 1.54 - 3.15 * rv + .15 * np.cos(ra)), axis=-1)
    grid('Back tie | wrapped knot', knot, 'Sash', waist_binding, thickness=.14, flip=True)

    # The cheek of the folded towel faces forward. The shorter outer end lies
    # over the long checked flap and both turn over a common waist attachment.
    for outer in (False, True):
        t, u = np.meshgrid(np.linspace(0, 1, 32), np.linspace(0, 1, 35), indexing='ij')
        a = .965 + .085 * t + (.25 + .16 * t) * (2 * u - 1)
        z = 100.82 + .92 * np.cos((u - .4) * 2.2) - t * ((16.35 if outer else 24.9) + 3.2 * u)
        z += (.89 * np.sin(2 * math.pi * u + .4) - (2.7 if outer else .60) * (1 - u)) * t ** 2
        # Query the same draped apron at this angle and height to set the space between layers.
        sample_t = np.clip((102.6 - z) / 61., 0., 1.)
        sample_u = .5 * (1 + (a - .015 * np.sin(3.1 * sample_t)) / (2.22 - .23 * sample_t))
        carrier = sheet(sample_t, sample_u)
        r = np.linalg.norm(carrier[:, :, :2] - origin, axis=2)
        r = np.maximum(r, section(z, a) + 1.55)
        fold = (.15 + .85 * smooth(t * 2.2)) * (.62 * np.cos(3.2 * math.pi * u - .6 * t)
                                                  + .24 * np.sin(5.1 * math.pi * u + 1.2 * t))
        r += (.90 if outer else .34) + fold * (.82 if outer else .44)
        r += (1.08 if outer else .42) * np.sin(math.pi * t * .65) + (.68 if outer else .0) * t
        tex = np.stack(((1 - u) if outer else u, (.94 - .83 * t) if outer else t), axis=-1)
        grid('Left hip towel | ' + ('short folded flap' if outer else 'long checked flap'),
             place(z, a, r), 'Towel', cloth_binding, tex, thickness=.12)

    # Fit rounded horn buttons and their stitch to the actual overlapping henley placket.
    upper, _, upper_weights = part('Overlapping front placket 1')
    opposite, _, _ = part('Overlapping front placket -1')
    placket = np.vstack((upper, opposite))
    order = np.argsort(placket[:, 2])
    for i, z in enumerate((141., 145.05, 148.66)):
        row = placket[np.abs(placket[:, 2] - z) < .66]
        y = np.max(row[:, 1]) if len(row) else np.interp(z, placket[order, 2], placket[order, 1])
        a = np.linspace(0., math.tau, 25)
        rows = []
        for radius_b, off in ((.085, .20), (.58, .20), (.67, .29), (.68, .40), (.58, .48), (.39, .43), (.06, .44)):
            rows.append(np.stack((.14 + radius_b * np.cos(a), np.full_like(a, y + off), z + radius_b * np.sin(a)), axis=-1))
        grid('Henley | horn button ' + str(i + 1), rows, 'Button', shirt_binding, flip=True)
        # Stitched through the face; the thread is slightly proud of the recessed centre.
        path = np.linspace(-.15, .15, 8)
        v, a = np.meshgrid(path, np.linspace(0., math.tau, 8), indexing='ij')
        filament = np.stack((.14 + v, y + .455 + .055 * np.cos(a) + .08 * (1 - (v / .15) ** 2),
                             z + .72 * v + .055 * np.sin(a)), axis=-1)
        grid('Henley | button stitch ' + str(i + 1), filament, 'Thread', shirt_binding)

    # The Jason body ends at its shoulder boundary. The original head contains the
    # matching lower neck. Keep it separate so a fitted head that includes the
    # full native neck can replace exactly this one piece.
    (cp, cn, cu, cw, cf, cut), *_ = native_neck()
    put('Baker_Neck_Base', cp, cf[:, ::-1], cu[cf[:, ::-1]], ['NativeNeck'],
        [list(row.items()) for row in cw], cn[cf[:, ::-1]])
    items[-1]['upper_ring'] = np.asarray(cut, dtype=int)
    return items, [b['name'] for b in donor['bones']]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    items, bones = collect_meshes()
    blender = os.environ.get('BLENDER_EXE', 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe')
    with tempfile.TemporaryDirectory(prefix='village_baker_workwear_') as temp:
        mesh = Path(temp) / 'patterns.pickle'
        with mesh.open('wb') as out:
            pickle.dump((items, bones), out, protocol=4)
        subprocess.run([blender, '--background', '--factory-startup', '--python-exit-code', '1',
                        '--python', str(Path(__file__).with_name('wardrobe_blend.py')), '--', str(mesh)], check=True)


if __name__ == '__main__':
    main()
