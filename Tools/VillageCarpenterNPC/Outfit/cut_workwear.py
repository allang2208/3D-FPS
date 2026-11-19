"""Cut the carpenter's work clothes in the strong Jason body's native rest space (cm)."""
from pathlib import Path
import gzip
import json
import math
import sys

import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[3]
SMITH = ROOT / 'SourceAssets/VillageBlacksmithNPC20261118/FinishR2/BodyOutfit'
OUT = ROOT / 'SourceAssets/VillageCarpenterNPC/Outfit'
sys.path.insert(0, str(ROOT / 'Tools/VillageBlacksmithNPC/FinishR2/BodyOutfit'))
from cloth_surface import Bind, grid_tris, ray_dist, rays_at_x, row_normals, unit

source = json.loads((SMITH / 'outfit.json').read_bytes())
positions = np.asarray(source['positions'])
triangles = np.asarray(source['triangles'])
base_uv = np.asarray(source['uv'])
base_normals = np.asarray(source['normals'])
slots = ['Linen', 'Twill', 'Canvas', 'Saddle', 'Boot', 'Sole', 'Brass', 'Thread', 'Tools']
mesh = {key: [] for key in ('positions', 'uv', 'normals', 'weights', 'triangles', 'triangle_materials')}
mesh.update(material_slots=slots, bones=source['bones'], parts={})


def write_part(name, points, faces, uv, material, weights, normals=None):
    start, face_start = len(mesh['positions']), len(mesh['triangles'])
    mesh['positions'].extend(points.round(5).tolist())
    mesh['weights'].extend(weights)
    mesh['triangles'].extend((faces + start).tolist())
    mesh['uv'].extend(uv.round(6).tolist())
    normals = row_normals(points, faces)[faces] if normals is None else normals
    mesh['normals'].extend(normals.round(6).tolist())
    mesh['triangle_materials'].extend([slots.index(material)] * len(faces)
                                      if isinstance(material, str) else material)
    mesh['parts'][name] = [start, face_start, len(mesh['positions']), len(mesh['triangles'])]


def carry(name):
    from garment_uv import garment_uv

    a, i, b, j = source['parts'][name]
    # Slots 0, 1, 3..7 deliberately retain the donor's order and surface class.
    uv = garment_uv(name, positions[a:b], triangles[i:j] - a, base_uv[i:j], source['triangle_materials'][i:j])
    write_part(name, positions[a:b], triangles[i:j] - a, uv,
               source['triangle_materials'][i:j], source['weights'][a:b], base_normals[i:j])


for name in source['parts']:
    if (name in ('Continuous linen shirt', 'Soft collar stand with inner facing', 'trousers',
                 'boots', 'Skived and rounded waist belt', 'Cast buckle frame', 'Buckle tongue')
            or name.startswith(('Twice turned sleeve', 'Overlapping front placket', 'Flat-felled shoulder seam'))):
        carry(name)


class PatternSurface:
    """Interpolate the front of a supplied garment in the cutting plane, including its skin weights."""

    def __init__(self, name, garment=source):
        a, i, b, j = garment['parts'][name]
        self.points = np.asarray(garment['positions'][a:b])
        self.faces = np.asarray(garment['triangles'][i:j]) - a
        self.projection = self.points[self.faces][:, :, [0, 2]]
        self.tree = cKDTree(self.projection.mean(axis=1))
        self.bind = Bind(self.points, garment['weights'][a:b])

    def depth(self, x, z):
        x, z = np.broadcast_arrays(x, z)
        shape = x.shape
        samples = np.stack((x.ravel(), z.ravel()), axis=1)
        result = []
        # Restrict the closest-face arrays to a few thousand corners at a time.
        for offset in range(0, len(samples), 128):
            section = samples[offset:offset + 128]
            indices = self.tree.query(section, k=80)[1]
            projected = self.projection[indices]
            p = section[:, None] - projected[:, :, 0]
            u = projected[:, :, 1] - projected[:, :, 0]
            v = projected[:, :, 2] - projected[:, :, 0]
            den = u[:, :, 0] * v[:, :, 1] - u[:, :, 1] * v[:, :, 0]
            den[np.abs(den) < 1e-9] = np.nan
            b = (p[:, :, 0] * v[:, :, 1] - p[:, :, 1] * v[:, :, 0]) / den
            c = (p[:, :, 1] * u[:, :, 0] - p[:, :, 0] * u[:, :, 1]) / den
            inside = (b >= -.001) & (c >= -.001) & (b + c <= 1.001)
            ys = self.points[self.faces[indices], 1]
            depths = ys[:, :, 0] + b * (ys[:, :, 1] - ys[:, :, 0]) + c * (ys[:, :, 2] - ys[:, :, 0])
            h = np.max(np.where(inside, depths, -np.inf), axis=1)
            fallback = np.max(ys[:, :4], axis=(1, 2))
            result.extend(np.where(np.isfinite(h), h, fallback))
        return np.asarray(result).reshape(shape)


shirt = PatternSurface('Continuous linen shirt')
apron = PatternSurface('Cut leather bib and vented apron')


def grid(name, rows, mat, binder, scale=20, flip=False):
    rows = np.asarray(rows)
    points = rows.reshape(-1, 3)
    faces = grid_tris(*rows.shape[:2], reverse=flip)
    across = np.r_[0., np.cumsum(np.mean(np.linalg.norm(np.diff(rows, axis=1), axis=2), axis=0))]
    rise = np.r_[0., np.cumsum(np.mean(np.linalg.norm(np.diff(rows, axis=0), axis=2), axis=1))]
    uv = np.stack(np.meshgrid(across / scale, rise / scale), axis=-1).reshape(-1, 2)
    write_part(name, points, faces, uv[faces], mat, binder(points))


def piping(name, paths, radius, material, binder, sides=6):
    vertices, faces, uv = [], [], []
    for path in paths:
        path = np.asarray(path)
        axis = unit(np.gradient(path, axis=0))
        guide = np.eye(3)[np.argmin(np.max(np.abs(axis), axis=0))]
        side = unit(np.cross(axis, guide))
        other = unit(np.cross(axis, side))
        azimuth = np.arange(sides) * math.tau / sides
        points = path[:, None] + radius * (side[:, None] * np.cos(azimuth)[None, :, None]
                                            + other[:, None] * np.sin(azimuth)[None, :, None])
        f = grid_tris(len(path), sides, cycle=True, reverse=True)
        faces.extend(f + len(vertices))
        vertices.extend(points.reshape(-1, 3))
        run = np.r_[0., np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
        around = f % sides
        wrap = np.ptp(around, axis=1) == sides - 1
        around[wrap] = np.where(around[wrap] == 0, sides, around[wrap])
        uv.extend(np.stack((around * (math.tau * radius / sides), run[f // sides]), axis=-1) / 12.)
    pts = np.asarray(vertices)
    write_part(name, pts, np.asarray(faces), np.asarray(uv), material, binder(pts))


def running_stitches(edge, pitch=.65):
    edge = np.asarray(edge)
    arc = np.r_[0., np.cumsum(np.linalg.norm(np.diff(edge, axis=0), axis=1))]
    count = max(1, round(arc[-1] / pitch))
    ends = (np.arange(count)[:, None] + [.12, .72]) * (arc[-1] / count)
    return np.stack([np.interp(ends, arc, axis) for axis in edge.T], axis=-1)


for side in (-1, 1):
    a, _, b, _ = source['parts']['Twice turned sleeve ' + str(side)]
    # The donor has fifteen cross sections around the rolled sleeve. Work along the
    # stitched edge of the outer turn and include the closing stitch around the arm.
    cuff = positions[a:b].reshape(15, -1, 3)
    axis = unit((cuff[9] - cuff[2]).mean(axis=0))
    radial = cuff[9] - cuff[9].mean(axis=0)
    radial -= (radial @ axis)[:, None] * axis
    ring = cuff[9] + .045 * unit(radial)
    piping('Rolled cuff lockstitch ' + str(side), running_stitches(np.vstack((ring, ring[0])), .77),
           .043, 'Thread', Bind(positions[a:b], source['weights'][a:b]), sides=4)


# Turn the low collar over the outside of its stand. Use the shirt's triangles to place
# the collar fall, especially across the shoulder where the body rises toward the neck.
a, _, b, _ = source['parts']['Soft collar stand with inner facing']
stand = positions[a:b].reshape(8, -1, 3)
top = stand[5].copy()
radial = unit(np.column_stack((top[:, 0], top[:, 1] + .55, np.zeros(len(top)))))
phase = np.linspace(0, 1, len(top))
near_front = np.minimum(phase, 1 - phase)
front = np.clip((.23 - near_front) / .23, 0, 1)
tip = np.exp(-((near_front - .034) / .036) ** 2)
fall = 2.75 + 2.1 * front + 1.5 * tip
rows = []
shirt_sections = shirt.points[shirt.faces][:, :, [2, 0, 1]]
for level in np.linspace(0, 1, 10):
    reach = (.27 + 3.4 * level + 1.2 * np.sin(level * np.pi)) * (1 + .12 * front)
    pts = top + radial * reach[:, None]
    pts[:, 2] += .16 - fall * level
    # Project an outward ray against the actual shirt using a horizontal section.
    for k, (x, y, z) in enumerate(pts):
        segments = rays_at_x(shirt_sections, z)
        hits = ray_dist(segments, np.array([0., -.55]), radial[k, :2])
        distance = np.linalg.norm([x, y + .55])
        if len(hits):
            new_radius = max(distance, min(hits, key=lambda h: abs(h - distance)) + .21)
            pts[k, :2] = np.array([0., -.55]) + radial[k, :2] * new_radius
    rows.append(pts)
grid('Turn-down flax collar with front points', rows, 'Linen', shirt.bind, flip=True)
piping('Turned collar edge', [rows[-1]], .093, 'Linen', shirt.bind)


def skirt_coordinates(side, t, across):
    """The gap at the hem closes 13 cm up, with one vent edge per thigh."""
    t, across = np.broadcast_arrays(t, across)
    width = 15.1 + 3.55 * np.sin(t * 1.95) + .7 * t
    split = 1.42 * np.clip((t - .59) / .41, 0, 1) ** .8
    x = side * (split + across * (width - split))
    z = 103.05 - t * (33.8 + .85 * side - 2.4 * across ** 8 - 1.3 * (1 - across) ** 10)
    y = apron.depth(x, z) - .14 + .35 * np.sin(t * 3.6 + across * 6.1) * np.sin(t * np.pi)
    return np.stack((x, y, z), axis=-1)


for side in (-1, 1):
    # Join the two upper panels with the sewn-in centre seam; separate below the vent.
    t, across = np.meshgrid(np.linspace(0, 1, 37), np.linspace(0, 1, 23), indexing='ij')
    panel = skirt_coordinates(side, t, across)
    grid('Split canvas skirt ' + str(side), panel, 'Canvas', apron.bind, flip=side > 0)
    hem = panel[-1]
    return_edge = np.stack([hem, hem + [0, .04, -.09], hem + [0, -.12, -.17], hem + [0, -.24, .55]])
    grid('Folded lower apron hem ' + str(side), return_edge, 'Canvas', apron.bind, flip=side > 0)
    hem_seam = skirt_coordinates(side, .977, np.linspace(.018, .982, 52)) + [0, .055, 0]
    piping('Apron hem lockstitch ' + str(side), running_stitches(hem_seam), .049, 'Thread', apron.bind, sides=4)
    for label, edge in [('outside', panel[:, -1]), ('vent', panel[22:, 0])]:
        piping(label + ' edge ' + str(side), [edge], .10, 'Canvas', apron.bind)


def pocket(name, surface, left, right, base, lip, mat, depth, angle=0., pencil_sleeve=False, binder=None):
    binder = binder or surface.bind

    def shape(u, v):
        u, v = np.broadcast_arrays(u, v)
        x = left + (right - left) * u
        taper = 1.35 * np.maximum(0, 1 - v * 5) * (2 * u - 1)
        x -= taper
        z = base + (lip - base) * v + angle * (u - .5) * v + .66 * np.abs(2 * u - 1) ** 7 * (1 - v)
        # A used patch pulls taut at its mouth corners and sags between the tacks.
        z -= .16 * depth * np.sin(math.pi * u) ** 2 * v ** 2
        roundness = np.sin(u * math.pi) ** .66 * (.14 + .86 * np.sin(v * math.pi / 2))
        # Ease at the turned bottom corners makes two short, tapered diagonal folds.
        corner = np.minimum(u, 1. - u)
        fold_start = .055 + .86 * corner + .032 * u
        fold = (.23 * np.exp(-((v - fold_start) / .089) ** 2)
                - .13 * np.exp(-((v - fold_start - .092) / .083) ** 2))
        height = surface.depth(x, z) + .18 + depth * (
            roundness + fold * np.sin(np.pi * u) ** .65 * np.exp(-(corner / .28) ** 2))
        if pencil_sleeve:
            # The narrow stitched channel tents over the flat stock while the divider lies flat.
            channel = .68 * np.exp(-((u - .865) / .081) ** 4) - .27 * np.exp(-((u - .75) / .045) ** 2)
            height += np.clip((v - .27) / .45, 0, 1) * channel
        return np.stack((x, height, z), axis=-1)
    v, u = np.meshgrid(np.linspace(0., 1., 19), np.linspace(0., 1., 33 if pencil_sleeve else 21), indexing='ij')
    pts = shape(u, v)
    grid(name, pts, mat, binder)
    piping(name + ' double turned lip', [pts[-1], shape(u[-1], .927)], .102, mat, binder)
    # Return the lining towards the body, leaving the mouth open and the sides sewn down.
    liprow = pts[-1]
    lining = np.stack([liprow, liprow + [0, -.12, -.09], liprow + [0, -.22, -.23],
                        liprow + [0, -.23, -1.05]])
    grid(name + ' lining return', lining, mat, binder)
    # Close the standing sides and bottom against the actual carrier. Leave the lip open.
    for label, edge, flip in [('left', pts[:, 0], False), ('right', pts[:, -1], True), ('base', pts[0], True)]:
        back = edge.copy()
        back[:, 1] = surface.depth(back[:, 0], back[:, 2]) - .03
        grid(name + ' turned allowance ' + label, [edge, back], mat, binder, flip=flip)
    uline = np.linspace(.035, .965, 32)
    vline = np.linspace(.05, .955, 25)
    seams = [shape(.035, vline), shape(.965, vline), shape(uline, .045)]
    stitch_runs = []
    for edge in seams:
        stitch_runs.extend(running_stitches(edge + [0., .065, 0.]))
    piping(name + ' side and base stitches', stitch_runs, .046, 'Thread', binder, sides=4)
    tacks = []
    for center in (.045, .955):
        for v_center in (.946, .957, .968):
            tacks.append(shape([center - .033, center + .033], [v_center - .007, v_center + .007])
                         + [0., .09, 0.])
    piping(name + ' mouth bar tacks', tacks, .058, 'Thread', binder, sides=5)
    return shape


ruler_panel = PatternSurface('Split canvas skirt -1', mesh)
nail_panel = PatternSurface('Split canvas skirt 1', mesh)
ruler_pocket = pocket('Carpenters folding-rule pocket', ruler_panel, -14.9, -2.0, 78.8, 92.1, 'Canvas', 2.1, 1.75)
pocket('Roomy nail pouch', nail_panel, 1.0, 15.6, 77.6, 90.8, 'Canvas', 2.45, -2.25)

channel_u = .865
channel_x = 4.4 + (13.9 - 4.4) * channel_u
channel_z = 138.0 - .86 * (channel_u - .5) - .16 * 1.05 * math.sin(math.pi * channel_u) ** 2
channel_skin = np.array([channel_x, shirt.depth(channel_x, channel_z), channel_z])
pencil_weights = shirt.bind(channel_skin[None])[0]


def sleeve_bind(points):
    # The stock and a stock-width strip at the mouth ride the same chest transform.
    # Feather that local reinforcement back into the shirt across the rest of the patch.
    weights = shirt.bind(points)
    x_blend = np.clip((2.5 - abs(points[:, 0] - channel_x)) / 1.65, 0., 1.)
    z_blend = np.clip((3.3 - abs(points[:, 2] - (channel_z - .45))) / 2., 0., 1.)
    influence = x_blend * z_blend
    for i in np.flatnonzero(influence):
        alpha = influence[i]
        if alpha >= 1.:
            weights[i] = pencil_weights
            continue
        mixed = {bone: value * (1. - alpha) for bone, value in weights[i]}
        for bone, value in pencil_weights:
            mixed[bone] = mixed.get(bone, 0.) + alpha * value
        pairs = sorted(mixed.items(), key=lambda pair: -pair[1])[:8]
        total = sum(value for _, value in pairs)
        weights[i] = [[bone, value / total] for bone, value in pairs]
    return weights


pencil_name = 'Chest pocket with pencil sleeve'
pencil_pocket = pocket(pencil_name, shirt, 4.4, 13.9, 126.8, 138.0, 'Linen', 1.05, -.86,
                       pencil_sleeve=True, binder=sleeve_bind)
v = np.linspace(.055, .99, 21)
divider = pencil_pocket(np.full_like(v, .75), v)
divider[:, 1] += .07
piping('Pencil pocket divider', [divider], .074, 'Linen', sleeve_bind)


def rigid_stick(name, center, right, up, widths, heights, depths, atlas, weights):
    """Closed, bevelled rectangular cross-sections for the rule leaves and flat pencil."""
    right, up = unit(right), unit(up)
    forward = unit(np.cross(up, right))
    if forward[1] < 0:
        forward *= -1
    ring = [(-.78, 1), (.78, 1), (1, .66), (1, -.66),
            (.78, -1), (-.78, -1), (-1, -.66), (-1, .66)]
    points = np.asarray([center + right * w * rx / 2 + forward * d * ry / 2 + up * h
                         for w, d, h in zip(widths, depths, heights) for rx, ry in ring])
    all_faces, all_uv = [], []
    u0, u1, v0, v1 = atlas
    for r in range(len(heights) - 1):
        for j in range(8):
            k = (j + 1) % 8
            corners = [r * 8 + j, r * 8 + k, (r + 1) * 8 + k, (r + 1) * 8 + j]
            for order in ((0, 1, 2), (0, 2, 3)):
                face = [corners[i] for i in order]
                q = points[face]; normal = np.cross(q[2] - q[0], q[1] - q[0])
                mean = q.mean(axis=0) - center
                if normal @ (mean - up * (mean @ up)) < 0:
                    face.reverse()
                all_faces.append(face)
                all_uv.append([[u0 + (ring[index % 8][0] / 2 + .5) * (u1 - u0),
                                v1 + (v0 - v1) * ((heights[index // 8] - heights[0]) / (heights[-1] - heights[0]))]
                               for index in face])
    for r in (0, len(heights) - 1):
        for j in range(1, 7):
            face = [r * 8, r * 8 + j, r * 8 + j + 1]
            q = points[face]
            if np.cross(q[2] - q[0], q[1] - q[0]) @ up * (-1 if r == 0 else 1) < 0:
                face.reverse()
            all_faces.append(face)
            all_uv.append([[(u0 + u1) / 2, v0 + .015]] * 3)
    faces = np.asarray(all_faces)
    q = points[faces]
    normals = np.repeat(unit(np.cross(q[:, 2] - q[:, 0], q[:, 1] - q[:, 0]))[:, None], 3, axis=1)
    write_part(name, points, faces, np.asarray(all_uv), 'Tools', [weights] * len(points), normals)


# Model only the portions inside and above the pockets, with both tools placed between
# the garment and the patch lip. The ruler's measured ticks are painted in its UV island.
anchor = ruler_pocket(.37, 1).copy()
anchor[1] -= .82
up = unit(np.array([-.16, -.08, 1.]))
right = unit(np.cross([0., 1., 0.], up))
ruler_weights = ruler_panel.bind(anchor[None])[0]
for j in range(2):
    c = anchor + np.array([.08 * j, -.31 * j, .23 * j])
    rigid_stick('Beech folding rule leaf ' + str(j), c, right, up, [1.72] * 4,
                [-1.6, -1.45, 6.5, 6.63], [.18, .25, .25, .19], (.03, .46, .08, .93), ruler_weights)

# Fit the flat pencil against the slope and transverse curvature of this particular
# shirt. Its visible shank and point extend from a short buried end inside the welt.
anchor = channel_skin.copy()
anchor[1] += .54
rise = np.linspace(1.35, 5.75, 8)
lean = .085
chest = shirt.depth(channel_x + lean * rise, channel_z + rise)
slope = np.max((chest + .27 - anchor[1]) / rise)
up = unit(np.array([lean, slope, 1.]))
chest_dx = float(shirt.depth(channel_x + .45, channel_z) - shirt.depth(channel_x - .45, channel_z))
tangent = np.array([.9, chest_dx, 0.])
right = unit(tangent - up * (up @ tangent))
forward = unit(np.cross(up, right))
if forward[1] < 0:
    forward *= -1

# Use the faces of the finished patch to seat the full width of the pencil behind
# the doubled mouth. The small sunk end follows the same rigid weights as the welt.
patch = PatternSurface(pencil_name, mesh)
stock_width, stock_depth = .82, .32
offsets = np.array([along * up + across * right + stock_depth / 2 * forward
                    for along in (-1.04, -.77, -.48, -.30)
                    for across in np.linspace(-stock_width / 2, stock_width / 2, 7)])
front = anchor + offsets
lining_y = patch.depth(front[:, 0], front[:, 2]) - .30
anchor[1] += min(0., float(np.min(lining_y - front[:, 1])))

rigid_stick('Flat oxblood carpenters pencil', anchor, right, up, [stock_width] * 2,
            [-1.04, 4.85], [stock_depth] * 2, (.56, .73, .1, .9), pencil_weights)
anchor_tip = anchor + 4.85 * up
rigid_stick('Pared cedar around graphite', anchor_tip, right, up, [stock_width, .24], [0, 1.12],
            [stock_depth, .13], (.78, .88, .1, .9), pencil_weights)
rigid_stick('Flat graphite point', anchor_tip, right, up, [.24, .075], [1.12, 1.44],
            [.13, .05], (.92, .97, .1, .9), pencil_weights)

OUT.mkdir(exist_ok=True, parents=True)
from garment_wear import bake_wear
bake_wear(mesh)
with gzip.open(OUT / 'workwear.json.gz', 'wt', encoding='utf-8', compresslevel=4) as stream:
    json.dump(mesh, stream, separators=(',', ':'), allow_nan=False)
print(f"Cut carpenter workwear: {len(mesh['positions'])} vertices, {len(mesh['triangles'])} triangles.")
