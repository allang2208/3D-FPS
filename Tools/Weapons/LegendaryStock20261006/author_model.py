"""Original game prop: 可调式战术后托. Background modeling/export only.

The approved concept sets the silhouette; the unseen surfaces are authored here.
The front cap is a game attachment datum, not a real firearm interface design.
Blender metres, +X forward, +Z up; the stock extends towards -X.
"""
import json
import math
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Vector

P = Path(__file__).resolve().parents[3]
O = P / 'SourceAssets/LegendaryStock20261006'
attachment_definition = json.loads((O / 'attachment-definition.json').read_text(encoding='utf-8'))
for folder in ('Model', 'Exports', 'Textures'):
    (O / folder).mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
S = bpy.context.scene
S.unit_settings.system = 'METRIC'
S.unit_settings.scale_length = 1.0
groups = {key: [] for key in ('Body', 'Mount', 'CheekRest', 'ButtPad', 'Controls')}
collections = {}
for key in groups:
    coll = bpy.data.collections.new(key)
    S.collection.children.link(coll)
    collections[key] = coll
current = 'Body'

# Small repeating original surface maps, shared by material family. No photo,
# brand texture, text, or geometry from the real-world inspiration is copied.
texture_specs = {}
images = {}
rng = np.random.default_rng(61006)
size = 1024
yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)


def blur_periodic(a, passes):
    for _ in range(passes):
        a = (a * 4 + np.roll(a, 1, 0) + np.roll(a, -1, 0)
             + np.roll(a, 1, 1) + np.roll(a, -1, 1)) / 8
    return a


def molded_grain(cells=64):
    # Periodic, irregular molded cells at ~0.55 mm. The narrow valleys and broad
    # plateaus produce rubber grain, rather than a fine sand/noise surface.
    gx, gy = xx / size * cells, yy / size * cells
    ix, iy = gx.astype(np.int32), gy.astype(np.int32)
    jitter = rng.uniform(.18, .82, (cells, cells, 2)).astype(np.float32)
    nearest = np.full((size, size), 10., dtype=np.float32)
    second = nearest.copy()
    for ox in (-1, 0, 1):
        for oy in (-1, 0, 1):
            sx, sy = ix + ox, iy + oy
            delta = jitter[sy % cells, sx % cells]
            distance = np.sqrt((gx - sx - delta[:, :, 0])**2 + (gy - sy - delta[:, :, 1])**2)
            second = np.minimum(second, np.maximum(nearest, distance))
            nearest = np.minimum(nearest, distance)
    valley = np.exp(-np.maximum(second - nearest, 0) * 17.)
    micro = blur_periodic(rng.normal(0, 1, (size, size)).astype(np.float32), 2)
    return .8 - .55 * valley - .25 * np.clip(nearest, 0, 1) + .035 * micro


for family, amplitude, smoothing in [('Coating', .13, 3), ('Rubber', 1.15, 7), ('Metal', .07, 2)]:
    h = blur_periodic(rng.normal(0, 1, (size, size)).astype(np.float32), smoothing)
    h /= max(float(h.std()), .001)
    if family == 'Rubber':
        h = molded_grain()
    elif family == 'Metal':
        h = .25 * h + .6 * np.sin(yy * math.tau * 221 / size)
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * amplitude
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * amplitude
    normal = np.stack((-dx, -dy, np.ones_like(h)), axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    rgba_n = np.ones((size, size, 4), dtype=np.float32)
    rgba_n[:, :, :3] = normal * .5 + .5
    rgba_orm = np.ones((size, size, 4), dtype=np.float32)
    rgba_orm[:, :, 1] = np.clip(.90 + (h - .45) * .16 if family == 'Rubber' else .90 + h * .035, .72, 1.0)
    # B carries a subtle diffuse grain mask; metalness is the material scalar.
    rgba_orm[:, :, 2] = np.clip(.79 + h * .25, .78, 1.) if family == 'Rubber' else 1.
    for suffix, pixels in [('N', rgba_n), ('ORM', rgba_orm)]:
        name = 'T_TacticalStock_' + family + '_' + suffix
        image = bpy.data.images.new(name, width=size, height=size, alpha=True)
        image.colorspace_settings.name = 'Non-Color'
        image.pixels.foreach_set(pixels.ravel())
        image.filepath_raw = str(O / 'Textures' / (name + '.png'))
        image.file_format = 'PNG'
        image.save()
        image.pack()
        images[(family, suffix)] = image
        texture_specs[name] = {'file': image.filepath_raw, 'kind': suffix, 'size': size,
                               'normal_convention': 'OpenGL' if suffix == 'N' else None}

settings = [
    ('Stock_Graphite', (.041, .046, .052, 1), .0, .46, 'Coating'),
    ('Stock_Polymer', (.019, .022, .025, 1), .0, .55, 'Coating'),
    ('Stock_Rubber', (.021, .023, .024, 1), .0, .65, 'Rubber'),
    ('Stock_Champagne', (.49, .42, .31, 1), 1., .36, 'Metal'),
    ('Stock_Steel', (.10, .12, .14, 1), 1., .32, 'Metal'),
    ('Stock_RedInset', (.15, .011, .015, 1), .0, .40, 'Coating'),
]
M = {}
for name, color, metal, roughness, family in settings:
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bs = nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = color
    bs.inputs['Metallic'].default_value = metal
    bs.inputs['Specular IOR Level'].default_value = .28 if family == 'Rubber' else .5
    normal_tex = nodes.new('ShaderNodeTexImage')
    normal_tex.image = images[(family, 'N')]
    normal_map = nodes.new('ShaderNodeNormalMap')
    links.new(normal_tex.outputs['Color'], normal_map.inputs['Color'])
    links.new(normal_map.outputs['Normal'], bs.inputs['Normal'])
    orm = nodes.new('ShaderNodeTexImage')
    orm.image = images[(family, 'ORM')]
    sep = nodes.new('ShaderNodeSeparateColor')
    links.new(orm.outputs['Color'], sep.inputs['Color'])
    if family == 'Rubber':
        grain_color = nodes.new('ShaderNodeVectorMath')
        grain_color.operation = 'SCALE'
        grain_color.inputs[0].default_value = color[:3]
        links.new(sep.outputs['Blue'], grain_color.inputs['Scale'])
        links.new(grain_color.outputs['Vector'], bs.inputs['Base Color'])
    mul = nodes.new('ShaderNodeMath')
    mul.operation = 'MULTIPLY'
    mul.inputs[1].default_value = roughness / .9
    links.new(sep.outputs['Green'], mul.inputs[0])
    links.new(mul.outputs[0], bs.inputs['Roughness'])
    M[name] = mat


def select(ob):
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def register(ob, mat):
    for coll in list(ob.users_collection):
        coll.objects.unlink(ob)
    collections[current].objects.link(ob)
    groups[current].append(ob)
    ob.data.materials.append(M[mat])
    return ob


def finish_bevel(ob, amount, segments=4):
    if amount:
        select(ob)
        mod = ob.modifiers.new('Rounded manufactured edges', 'BEVEL')
        mod.width = amount / 1000
        mod.segments = segments
        mod.limit_method = 'ANGLE'
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return ob


def solid(name, verts_mm, faces, mat='Stock_Graphite', bevel=0):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(v / 1000 for v in pt) for pt in verts_mm], [], faces)
    mesh.update()
    ob = bpy.data.objects.new(name, mesh)
    collections[current].objects.link(ob)
    register(ob, mat)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    return finish_bevel(ob, bevel)


def side_prism(name, profile, y0, y1, mat='Stock_Graphite', bevel=0):
    # Profile coordinates are (distance rearwards, height), in authoring mm.
    n = len(profile)
    verts = [(-d, y, z) for y in (y0, y1) for d, z in profile]
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, n * 2))]
    faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    return solid(name, verts, faces, mat, bevel)


def box(name, d, y, z, length, width, height, mat='Stock_Graphite', bevel=.6):
    return side_prism(name, [(d-length/2, z-height/2), (d+length/2, z-height/2),
                            (d+length/2, z+height/2), (d-length/2, z+height/2)],
                      y-width/2, y+width/2, mat, bevel)


def strip(name, path, width, side, mat='Stock_Champagne'):
    points = [Vector(p) for p in path]
    left, right = [], []
    for i, p in enumerate(points):
        before = (p - points[i-1]).normalized() if i else (points[1]-p).normalized()
        after = (points[i+1]-p).normalized() if i < len(points)-1 else before
        n0, n1 = Vector((-before.y, before.x)), Vector((-after.y, after.x))
        normal = (n0+n1).normalized()
        off = normal * (width/2 / max(.4, normal.dot(n0)))
        left.append(tuple(p+off))
        right.append(tuple(p-off))
    return side_prism(name, left+list(reversed(right)),
                      min(side*16.85, side*17.55), max(side*16.85, side*17.55), mat, .20)


def cylinder(name, d, y, z, radius, depth, mat='Stock_Steel', count=40):
    bpy.ops.mesh.primitive_cylinder_add(vertices=count, radius=radius/1000,
                                      depth=depth/1000, location=(-d/1000, y/1000, z/1000))
    ob = bpy.context.object
    ob.name = name
    ob.rotation_euler.x = math.pi/2
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    register(ob, mat)
    return finish_bevel(ob, .22, 3)


def ring_loft(name, rings, mat, bevel=0):
    n = len(rings[0])
    verts = [v for row in rings for v in row]
    faces = [tuple(range(n-1, -1, -1)), tuple(range((len(rings)-1)*n, len(rings)*n))]
    for i in range(len(rings)-1):
        for j in range(n):
            k = (j+1) % n
            faces.append((i*n+j, i*n+k, (i+1)*n+k, (i+1)*n+j))
    ob = solid(name, verts, faces, mat, bevel)
    if not bevel:
        # Arc-length UVs wrap the cushion continuously; seam stays on its
        # inside/front. No dominant-axis flips across the rounded shoulder.
        uv = ob.data.uv_layers.new(name='SurfaceUV')
        centers = [sum((Vector(v) for v in ring), Vector()) / n for ring in rings]
        longitudinal = [0.]
        arcs = []
        for i, row in enumerate(rings):
            if i:
                longitudinal.append(longitudinal[-1] + (centers[i] - centers[i-1]).length)
            cumulative = [0.]
            for j in range(n):
                cumulative.append(cumulative[-1] + (Vector(row[(j+1) % n]) - Vector(row[j])).length)
            arcs.append(cumulative)
        for face in ob.data.polygons:
            js = [ob.data.loops[li].vertex_index % n for li in face.loop_indices]
            wraps = 0 in js and n-1 in js
            for li in face.loop_indices:
                vi = ob.data.loops[li].vertex_index
                row, j = divmod(vi, n)
                if face.index < 2:
                    p = ob.data.vertices[vi].co
                    axes = [a for a in range(3) if a != max(range(3), key=lambda a: abs(face.normal[a]))]
                    uv.data[li].uv = (p[axes[0]]/.035, p[axes[1]]/.035)
                else:
                    uv.data[li].uv = (arcs[row][n if wraps and j == 0 else j]/35, longitudinal[row]/35)
    return ob


def rounded_path(points, radius=2., steps=5):
    result = []
    for i, p in enumerate(points):
        p, a, b = Vector(p), Vector(points[i-1]), Vector(points[(i+1) % len(points)])
        da, db = (a-p), (b-p)
        entry = p + da.normalized() * min(radius, da.length*.3)
        leave = p + db.normalized() * min(radius, db.length*.3)
        for j in range(steps):
            t = j/(steps-1)
            result.append(tuple(entry*(1-t)**2 + p*(2*t*(1-t)) + leave*t*t))
    return result


def seam_tube(name, points, radius=.24, mat='Stock_Polymer'):
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '3D'; curve.resolution_u = 10
    curve.bevel_depth = radius/1000; curve.bevel_resolution = 2
    curve.use_fill_caps = True
    spline = curve.splines.new('BEZIER'); spline.bezier_points.add(len(points)-1)
    for knot, p in zip(spline.bezier_points, points):
        knot.co = Vector(p)/1000
        knot.handle_left_type = 'AUTO'; knot.handle_right_type = 'AUTO'
    ob = bpy.data.objects.new(name, curve); collections[current].objects.link(ob)
    select(ob); bpy.ops.object.convert(target='MESH'); ob = bpy.context.object
    register(ob, mat)
    return ob


def round_rect(a, b, radius, count=6):
    radius = min(radius, a*.85, b*.85)
    points = []
    for ca, cb, theta in [(a-radius, b-radius, 0), (-a+radius, b-radius, 90),
                           (-a+radius, -b+radius, 180), (a-radius, -b+radius, 270)]:
        for j in range(count):
            angle = math.radians(theta + j*90/(count-1))
            points.append((ca+radius*math.cos(angle), cb+radius*math.sin(angle)))
    return points


# One continuous closed truss chassis. The opening is geometry, not transparency.
outer = [(27, 12), (36, 14), (45, 13), (53, 9), (89, 3), (128, -6),
         (169, -4), (209, 3), (233, 17), (246, 20), (253, 15),
         (269, -91), (263, -97), (252, -90), (135, -38),
         (120, -30), (104, -21), (62, -16), (54, -23), (31, -23)]
opening = rounded_path([(143, -23), (192, -19), (207, -18), (226, -37),
                        (240, -72), (239, -77), (151, -39)], 4., 6)
body = side_prism('Continuous triangular open chassis', outer, -17, 17)
cutter = side_prism('Temporary opening cutter', opening, -35, 35)
select(body)
mod = body.modifiers.new('True through opening', 'BOOLEAN')
mod.operation = 'DIFFERENCE'
mod.solver = 'EXACT'
mod.object = cutter
bpy.ops.object.modifier_apply(modifier=mod.name)
groups[current].remove(cutter)
bpy.data.objects.remove(cutter, do_unlink=True)
finish_bevel(body, 2.4, 6)

# Long restrained trim matches the approved silhouette on both sides.
for side in (-1, 1):
    strip('Recessed continuous champagne sweep', [(28, 9), (40, 9), (48, 0), (96, -9),
                                                (135, -15), (205, -8), (232, -4), (240, 14)], 3.8, side)
    strip('Rear champagne return', [(240, 14), (241, -8), (246, -40), (255, -78), (262, -92)], 3.4, side)
    # The red inset sits inside the solid upper rear gusset, outside the hole.
    side_prism('Triangular rear gusset rim', [(205, -12), (237, -10), (242, -41)],
               min(side*16.7, side*17.55), max(side*16.7, side*17.55), 'Stock_Champagne', .7)
    side_prism('Recess bezel for red rarity inset', [(212, -14), (235, -13), (238, -34)],
               min(side*17.45, side*17.85), max(side*17.45, side*17.85), 'Stock_Polymer', .6)
    side_prism('Dark red identity inset', [(216, -16), (233.5, -15), (235.8, -29.5)],
               min(side*17.75, side*17.95), max(side*17.75, side*17.95), 'Stock_RedInset', .45)

# Closed master mount; fit_models.py adds the separate per-weapon receiver adapters.
current = 'Mount'
side_prism('Closed front adapter', [(0, 10), (5, 13), (26, 13), (39, 7),
                                  (42, -19), (35, -25), (8, -23), (0, -16)],
           -13.5, 13.5, 'Stock_Graphite', 1.4)
side_prism('Protected length slide', [(18, 8), (58, 12), (64, 7), (64, -13), (21, -16)],
           -12, 12, 'Stock_Steel', .9)
for side in (-1, 1):
    side_prism('Adapter inset grip panel', [(5, 6), (20, 7), (27, 3), (29, -15), (7, -17)],
               min(side*13.2, side*14.0), max(side*13.2, side*14.0), 'Stock_Polymer', .8)
box('Front upper stop', 8, 0, 12, 12, 24, 3, 'Stock_Polymer', .6)

# A separate carrier and fully rounded cushion; the lower carrier overlaps the
# upper chassis along its actual support surface instead of hanging above it.
current = 'CheekRest'
side_prism('Sculpted cheek carrier following the lower sweep',
           rounded_path([(43, 15), (57, 12), (92, 1), (134, -9), (177, -6),
                         (198, 0), (212, 12), (217, 9), (204, -4), (178, -11),
                         (135, -13), (94, -5), (54, 7), (42, 11)], 1.4, 4),
           -19, 19, 'Stock_Polymer', .9)
# Section tuple: rearward distance, half width, top, bottom. The deep middle
# and swept lower edge are the defining reference feature, not a level tube.
cheek_sections = [(43, 2, 21, 16), (45, 10, 28, 12), (50, 17, 31, 9),
                  (60, 21, 31, 7), (79, 22, 29.5, 2), (102, 22, 28, -4),
                  (132, 22, 26.5, -9), (157, 21.7, 25, -8),
                  (177, 21, 23, -5), (192, 20, 21, -1),
                  (201, 17.5, 19, 4), (208, 11, 17, 9), (212, 2, 13, 11)]
rings = []
for d, w, top, bottom in cheek_sections:
    ring = []
    for j in range(48):
        t = j*math.tau/48
        y = w * math.copysign(abs(math.cos(t))**.70, math.cos(t))
        height = math.copysign(abs(math.sin(t))**.76, math.sin(t))
        ring.append((-d, y, (top+bottom)/2 + (top-bottom)/2*height))
    rings.append(ring)
cheek = ring_loft('Continuous textured cheek cushion', rings, 'Stock_Rubber')
select(cheek)
sub = cheek.modifiers.new('Cushion contour smoothing', 'SUBSURF')
sub.levels = 2
bpy.ops.object.modifier_apply(modifier=sub.name)
for face in cheek.data.polygons:
    face.use_smooth = True
cheek['SoftSurface'] = True
for side in (-1, 1):
    welt = []
    for d, w, top, bottom in cheek_sections[1:-1]:
        # Lower-side molded seam follows the changing section instead of a
        # straight line drawn across the tapered cushion.
        t = -.78
        y = side * w * abs(math.cos(t))**.70
        z = (top+bottom)/2 - (top-bottom)/2*abs(math.sin(t))**.76
        welt.append((-d, y, z))
    seam_tube('Cheek cushion lower molded seam', welt, .26, 'Stock_Polymer')

# Curved leaning shoulder plate and a thick, closed rubber pad.
current = 'ButtPad'
pad_sections = [(25, 2), (24, 8), (21, 15), (16, 20), (7, 22), (-15, 23),
                (-43, 23.5), (-68, 23), (-86, 21), (-95, 16), (-99, 8), (-100, 2)]


def shoulder_layer(name, rear_offset, half_depth, width_delta, mat):
    rings = []
    for z, w in pad_sections:
        center_d = 243 + (22-z)*.17 + rear_offset
        profile = round_rect(half_depth, w+width_delta, min(half_depth*.75, 2.8), 7)
        rings.append([(-(center_d+da), y, z) for da, y in profile])
    return ring_loft(name, rings, mat, .65)


shoulder_layer('Shoulder structural back plate', 0, 3.3, 0, 'Stock_Graphite')
shoulder_layer('Champagne shoulder perimeter', 3.1, 1.3, .45, 'Stock_Champagne')


def smoothstep(low, high, value):
    t = max(0., min(1., (value-low)/(high-low)))
    return t*t*(3-2*t)


# Dense axial samples form recessed tread grooves in one closed rubber skin.
# The edge roll and thick convex back remain continuous around every groove.
pad_rings = []
knots = list(reversed(pad_sections))
def pad_width(z):
    for i in range(len(knots)-1):
        a, b = knots[i], knots[i+1]
        if a[0] <= z <= b[0]:
            before, after = knots[max(0, i-1)], knots[min(len(knots)-1, i+2)]
            m0 = (b[1]-before[1])/(b[0]-before[0])
            m1 = (after[1]-a[1])/(after[0]-a[0])
            dt = b[0]-a[0]; t = (z-a[0])/dt
            return (2*t**3-3*t*t+1)*a[1] + (t**3-2*t*t+t)*dt*m0 + (-2*t**3+3*t*t)*b[1] + (t**3-t*t)*dt*m1
    return knots[-1][1]

for i in range(251):
    z = -100 + i*.5
    w = pad_width(z)
    end = min(smoothstep(-101, -89, z), 1-smoothstep(16, 26, z))
    half_depth = 1.2 + 6.7 * end
    # Keep the pad front seated in the backing plate even at the rounded tips;
    # only the rear surface bulges. A fixed center leaves floating end caps.
    center_d = 243 + (22-z)*.17 + 3.3 + half_depth
    row = []
    for j in range(64):
        # Start at the inner face so the UV seam is concealed against the plate.
        angle = math.pi + j*math.tau/64
        cs, sn = math.cos(angle), math.sin(angle)
        y = w * math.copysign(abs(sn)**.76, sn)
        depth = half_depth * math.copysign(abs(cs)**.72, cs)
        facing = smoothstep(.25, .65, cs)
        center_mask = 1-smoothstep(.72, .86, abs(y)/max(w, .01))
        row_mask = smoothstep(-94, -87, z)*(1-smoothstep(12, 18, z))
        # Fine recessed channels split the contact face into molded bands.
        groove = sum(math.exp(-((z-level)/.70)**2) for level in range(-84, 13, 10))
        # An inset rounded border joins all bands; it is not a separate block.
        border = math.exp(-((abs(y)/max(w, .01)-.82)/.034)**2)
        depth -= facing*row_mask*(.82*groove*center_mask + .48*border)
        row.append((-(center_d+depth), y, z))
    pad_rings.append(row)
pad = ring_loft('Sculpted rubber shoulder pad with recessed molded tread', pad_rings, 'Stock_Rubber')
pad['SoftSurface'] = True
for face in pad.data.polygons:
    face.use_smooth = True

current = 'Controls'
for side in (-1, 1):
    # Controls stay inside the front lower recess; keep the long flank clean.
    cylinder('Flush adjustment collar', 52, side*16.8, -10.5, 3.5, 1.0, 'Stock_Polymer')
    cylinder('Recessed cheek adjustment dial', 52, side*17.4, -10.5, 2.7, .65, 'Stock_Steel')
    box('Dial thumb slot', 52, side*17.8, -10.5, 3, .15, .55, 'Stock_Polymer', .15)
    for d, z in [(34, -16), (252, -48)]:
        cylinder('Captive chassis screw', d, side*17.05, z, 1.7, 1.2, 'Stock_Steel', 24)
        box('Recessed screw head slot', d, side*17.72, z, 2.0, .2, .5, 'Stock_Polymer', .12)
box('Underside length release', 56, 0, -22, 19, 19, 5, 'Stock_Polymer', 1.2)
for d in (50, 54, 58, 62):
    box('Release tactile rib', d, 0, -24.5, 1, 15, 1, 'Stock_Rubber', .3)


def shoulder_recess(z_mm):
    # The side-view contact line scoops towards the receiver at mid-height.
    # End tangents stay continuous with the rolled heel and toe of the pad.
    t = max(0., min(1., (25.-z_mm)/125.))
    return 17.5 * math.sin(math.pi*t)**2


def curve_shoulder_assembly(ob):
    mesh = ob.data
    if max(-v.co.x for v in mesh.vertices) <= .192:
        return
    # The long rigid struts/trim originally had only end vertices. Add actual
    # cross-sections so the backing and chassis follow the same curved seam
    # as the dense rubber skin, instead of bridging it with straight edges.
    if not ob.get('SoftSurface', False):
        bm = bmesh.new(); bm.from_mesh(mesh)
        z_min = min(v.co.z for v in bm.verts)
        z_max = max(v.co.z for v in bm.verts)
        for z_mm in range(-98, 25, 2):
            z = z_mm/1000
            if z_min+.00001 < z < z_max-.00001:
                bmesh.ops.bisect_plane(bm, geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
                    dist=1e-8, plane_co=(0,0,z), plane_no=(0,0,1),
                    clear_inner=False, clear_outer=False)
        bm.to_mesh(mesh); bm.free()
    for vertex in mesh.vertices:
        d, z = -vertex.co.x*1000, vertex.co.z*1000
        blend = smoothstep(192., 237., d)
        vertex.co.x += shoulder_recess(z)*blend/1000
    mesh.update()


for part in groups.values():
    for ob in part:
        curve_shoulder_assembly(ob)

# Follow the newly curved spine in texture space as well: sidewall grain and
# the contact bands retain their physical pitch through the concave section.
pad_centers = [sum((pad.data.vertices[i*64+j].co for j in range(64)), Vector())/64
               for i in range(251)]
pad_distances = [0.]
for i in range(1, 251):
    pad_distances.append(pad_distances[-1]+(pad_centers[i]-pad_centers[i-1]).length)
pad_uv = pad.data.uv_layers.active
for face in pad.data.polygons:
    if face.index < 2:
        continue
    for li in face.loop_indices:
        row = pad.data.loops[li].vertex_index//64
        pad_uv.data[li].uv.y = pad_distances[row]/.035


def author_uv_and_normals(ob):
    select(ob)
    # Projection charts use a common physical texture repeat to keep grain size
    # consistent across the steel, flat cheeks and the rounded rubber surfaces.
    mesh = ob.data
    if not mesh.uv_layers:
        uv = mesh.uv_layers.new(name='SurfaceUV')
        for face in mesh.polygons:
            axis = max(range(3), key=lambda i: abs(face.normal[i]))
            axes = [i for i in range(3) if i != axis]
            for li in face.loop_indices:
                v = mesh.vertices[mesh.loops[li].vertex_index].co
                uv.data[li].uv = (v[axes[0]]/.035, v[axes[1]]/.035)
    if not ob.get('SoftSurface', False):
        for face in mesh.polygons:
            face.use_smooth = True
        bm = bmesh.new()
        bm.from_mesh(mesh)
        for edge in bm.edges:
            edge.smooth = len(edge.link_faces) == 2 and edge.calc_face_angle(0) < math.radians(55)
        bm.to_mesh(mesh)
        bm.free()
        mod = ob.modifiers.new('Weighted planar normals', 'WEIGHTED_NORMAL')
        mod.keep_sharp = True
        mod.weight = 45
        bpy.ops.object.modifier_apply(modifier=mod.name)
    tri = ob.modifiers.new('Final tangent triangulation', 'TRIANGULATE')
    tri.keep_custom_normals = True
    bpy.ops.object.modifier_apply(modifier=tri.name)


for part in groups.values():
    for ob in part:
        author_uv_and_normals(ob)

SOCKETS = {'Mount': (0, 0, 0), 'Forward': (.02, 0, 0),
           'CheekRest': (-.13, 0, .024),
           'ShoulderContact': (-(243+58*.17+3.3+2*7.9-shoulder_recess(-36))/1000, 0, -.036)}
for name, location in SOCKETS.items():
    marker = bpy.data.objects.new(name, None)
    S.collection.objects.link(marker)
    marker.location = location
    marker.empty_display_size = .01
    marker['Purpose'] = 'Game asset attachment datum, not a manufactured interface'
S['DisplayName'] = '可调式战术后托'
S['Rarity'] = 'legendary'
S['Stage'] = 'ModelOnly'
S['Reference'] = 'Design/concept-02.png; original image title is retained as design history'
S['AxisContract'] = '+X forward; stock extends -X; mount origin 0,0,0'
S['HostFit'] = 'Master geometry; per-weapon adapters are authored separately by fit_models.py'
S['VisualRevision'] = 'V3: concave shoulder contact, curved backing and continuous trim'
bpy.ops.wm.save_as_mainfile(filepath=str(O / 'Model/TacticalStock_Editable.blend'))


def combine(name, objects):
    copies = []
    for original in objects:
        ob = original.copy()
        ob.data = original.data.copy()
        S.collection.objects.link(ob)
        copies.append(ob)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in copies:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = copies[0]
    if len(copies) > 1:
        bpy.ops.object.join()
    ob = bpy.context.object
    ob.name = name
    S.cursor.location = (0, 0, 0)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    return ob


def export(ob, sockets):
    select(ob)
    path = O / 'Exports' / (ob.name + '.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={'MESH'},
                            axis_forward='-Y', axis_up='Z', add_leaf_bones=False,
                            bake_anim=False, mesh_smooth_type='FACE', use_tspace=True)
    ob.data.calc_loop_triangles()
    return {'fbx': str(path), 'triangles': len(ob.data.loop_triangles),
            'slots': [m.name for m in ob.data.materials],
            'sockets_ue_cm': {name: [x*100, -y*100, z*100] for name, (x,y,z) in sockets.items()}}


models = {}
assembly = combine('SM_TacticalStock_Assembly', [ob for group in groups.values() for ob in group])
models[assembly.name] = export(assembly, SOCKETS)
select(assembly)
bpy.ops.export_scene.gltf(filepath=str(O / 'Model/TacticalStock_Assembly.glb'),
                          export_format='GLB', use_selection=True, export_yup=True)
bpy.data.objects.remove(assembly, do_unlink=True)
for name, objects in groups.items():
    ob = combine('SM_TacticalStock_' + name, objects)
    models[ob.name] = export(ob, SOCKETS if name == 'Body' else {})
    bpy.data.objects.remove(ob, do_unlink=True)

integration = attachment_definition.get('integration', {})
report = {'display_name': attachment_definition['option']['name'], 'id': attachment_definition['option']['id'],
          'visual_revision': 'V3_concave_shoulder_contact',
          'shoulder_curve': {'profile': '17.5 * sin(pi * clamp((25-z)/125, 0, 1))^2 mm forward scoop',
                             'scope': 'Rubber pad, backing plates, rear chassis, trim and inset deform together',
                             'mount_preserved': True, 'reference': 'RefinementV3/user-shoulder-curve-reference.png'},
          'rarity': attachment_definition['rarity'], 'card_color': attachment_definition['card_color'],
          'stage': integration.get('status', 'model_and_stats_defined'),
          'attachment_definition': str(O / 'attachment-definition.json'),
          'stats': attachment_definition['option']['stats'],
          'reference': str(O / 'Design/concept-02.png'),
          'source': str(O / 'Model/TacticalStock_Editable.blend'),
          'forward_axis': '+X', 'units': 'Blender metres; UE centimetres',
          'mount_origin': 'Closed front adapter contact plane, 0,0,0',
          'part_frame': 'All parts share assembly origin; no additional offsets',
          'models': models, 'textures': texture_specs,
          'materials': [dict(name=n, color=c, metallic=m, roughness=r, family=f)
                        for n,c,m,r,f in settings],
          'provenance': 'Original Blender geometry and procedural PBR maps, authored from the approved AI concept. No third-party mesh or brand art copied.',
          'host_fitted': bool(integration.get('supported_definitions')),
          'runtime_integrated': integration.get('runtime_enabled', False), 'game_tested': False,
          'fitted_models': integration.get('fitted_models'),
          'supported_definitions': integration.get('supported_definitions', []),
          'adjustment_stage': 'Separate geometric parts only; no gameplay or adjustment animation implemented',
          'lod_policy': 'Authored close-up geometry only; no automatic decimation applied'}
(O / 'authoring.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('TACTICAL_STOCK_MODEL_EXPORTED ' + json.dumps({k:v['triangles'] for k,v in models.items()}))
