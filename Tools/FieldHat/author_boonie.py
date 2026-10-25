"""Author the field boonie hat from the captured Jason head.

Coordinate convention follows Tools/BlueMageHat/author_hat.py: centimetres,
X right, Y back, Z up in the authored source; Blender converts Y on export.
The hat is a closed canvas crown, a double-sided wavy brim with a bound edge,
a leather band/buckle/chin cord and four brass vent eyelets.  Only the rear
brim carries a three-bone spring chain; the crown and band are root-bound.
"""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path("D:/FPS3D/FPSGAME")
SRC = ROOT / "SourceAssets/FieldHat20261019"
sys.path.insert(0, str(ROOT / "Tools/BlueMageRobe"))
from geometry import vertex, face, finish, tube  # noqa: E402

TAU = 2.0 * math.pi
SEG = 128
CROWN_ROWS = 38
BRIM_ROWS = 20
H = 9.6
BRIM = 7.4
THICK = 0.32
BRIM_THICK = 0.26
CAP_DOME = 0.12
CAP_RINGS = (0.75, 0.50, 0.25)
SLOTS = ["Canvas", "CanvasUnder", "Leather", "Brass", "Lining", "Thread"]
ROOT_W = {"HatRoot": 1.0}


def angular_distance(a, b):
    return abs(((a - b + math.pi) % TAU) - math.pi)


def smoothstep(a, b, x):
    t = np.clip((x - a) / max(b - a, 1e-9), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def crown_radius_scale(t):
    t = float(np.clip(t, 0.0, 1.0))
    return 1.0 - 0.07 * t - 0.13 * float(smoothstep(0.58, 1.0, t))


def crown_point(t, a, inner=False):
    rs = crown_radius_scale(t)
    rs *= 1.0 + 0.006 * math.sin(6.0 * a + 1.3) * float(smoothstep(0.20, 0.80, t))
    rx = rs * RBX
    ry = rs * RBY
    x = rx * math.sin(a)
    y = -ry * math.cos(a)
    z = H * t
    z -= 0.35 * math.exp(-((x / 2.4) ** 2)) * float(smoothstep(0.55, 1.0, t))
    if inner:
        x = (rx - THICK) * math.sin(a)
        y = -(ry - THICK) * math.cos(a)
    return np.array([x, y, z])


def brim_point(u, a, lower=False):
    rx = (RBX - 0.45) + u * (BRIM + 0.45)
    ry = (RBY - 0.45) + u * (BRIM + 0.45)
    x = rx * math.sin(a)
    y = -ry * math.cos(a)
    z = -1.8 * (u ** 1.3)
    z += 0.20 * math.sin(2.0 * a + 0.6) * (u ** 2)
    z += 0.08 * math.sin(5.0 * a - 1.1) * (u ** 3)
    z += 0.45 * float(smoothstep(0.72, 1.0, u)) * math.exp(-((angular_distance(a, math.pi) / 0.55) ** 2))
    if lower:
        z -= BRIM_THICK
    return np.array([x, y, z])


def radial_normal(p, rx, ry):
    n = np.array([p[0] / max(rx * rx, 1e-6), p[1] / max(ry * ry, 1e-6), 0.0])
    return n / max(float(np.linalg.norm(n)), 1e-9)


def brim_weight(a, u):
    mask = 1.0 - float(smoothstep(0.55, 1.05, angular_distance(a, math.pi)))
    s = float(smoothstep(0.10, 0.95, u)) * mask
    q = float(np.clip((u - 0.10) / 0.85, 0.0, 1.0))
    weights = {"HatRoot": 1.0 - s}
    if s > 1e-6:
        if q < 0.40:
            weights["BrimBackBase"] = s * (q / 0.40)
        elif q < 0.72:
            k = (q - 0.40) / 0.32
            weights["BrimBackBase"] = s * (1.0 - k)
            weights["BrimBackMid"] = s * k
        else:
            k = (q - 0.72) / 0.28
            weights["BrimBackMid"] = s * (1.0 - k)
            weights["BrimBackEnd"] = s * k
    total = sum(weights.values())
    return {k: v / total for k, v in weights.items() if v > 1e-8}


def uv_crown(t, i):
    a = TAU * i / SEG
    return [a * (RBX + RBY) * 0.5 / 25.0, t * H / 25.0]


def uv_brim(u, i):
    a = TAU * i / SEG
    return [a * (RBX + BRIM) / 25.0, u * BRIM / 25.0]


def uv_band(z, i):
    a = TAU * i / SEG
    return [a * (RBX + RBY) * 0.5 / 12.0, z / 12.0]


def uv_cap(i):
    a = TAU * i / SEG
    return [a * (RBX + RBY) * 0.5 / 25.0, H / 25.0]


def uv_top(p):
    return [0.5 + float(p[0]) / 25.0, 0.5 + float(p[1]) / 25.0]


def add_surface(d, rows, position, weight_fn, material, uv_fn, out_fn):
    rings = []
    for t in rows:
        ring = [vertex(d, position(t, TAU * i / SEG), weight_fn(t, TAU * i / SEG)) for i in range(SEG)]
        rings.append(ring)
    for j in range(len(rows) - 1):
        for i in range(SEG):
            i2 = (i + 1) % SEG
            ids = [rings[j][i], rings[j][i2], rings[j + 1][i2], rings[j + 1][i]]
            uvs = [uv_fn(rows[j], i), uv_fn(rows[j], i2), uv_fn(rows[j + 1], i2), uv_fn(rows[j + 1], i)]
            out = out_fn(rows[j], TAU * (i + 0.5) / SEG)
            for tri in ((0, 1, 2), (0, 2, 3)):
                face(d, [ids[k] for k in tri], material, [uvs[k] for k in tri], out)
    return rings


def add_cap(d, rim, center, material, out):
    rim_pos = [np.array(d["positions"][i], dtype=float) for i in rim]
    ring_ids = [rim]
    ring_pos = [rim_pos]
    for r in CAP_RINGS:
        pos = [center + r * (p - center) + np.array([0.0, 0.0, CAP_DOME * (1.0 - r * r)]) for p in rim_pos]
        ring_pos.append(pos)
        ring_ids.append([vertex(d, p, ROOT_W) for p in pos])
    center_point = center + np.array([0.0, 0.0, CAP_DOME])
    center_id = vertex(d, center_point, ROOT_W)
    for j in range(len(ring_ids) - 1):
        for i in range(SEG):
            i2 = (i + 1) % SEG
            ids = [ring_ids[j][i], ring_ids[j][i2], ring_ids[j + 1][i2], ring_ids[j + 1][i]]
            uvs = [uv_top(ring_pos[j][i]), uv_top(ring_pos[j][i2]),
                   uv_top(ring_pos[j + 1][i2]), uv_top(ring_pos[j + 1][i])]
            for tri in ((0, 1, 2), (0, 2, 3)):
                face(d, [ids[k] for k in tri], material, [uvs[k] for k in tri], out)
    for i in range(SEG):
        i2 = (i + 1) % SEG
        face(d, [ring_ids[-1][i], ring_ids[-1][i2], center_id], material,
             [uv_top(ring_pos[-1][i]), uv_top(ring_pos[-1][i2]), uv_top(center_point)], out)


def band_outer_radius(z):
    return (RBX + RBY) * 0.5 * crown_radius_scale(z / H) + 0.10


def band_point(a, z):
    rs = crown_radius_scale(z / H)
    rx = RBX * rs + 0.10
    ry = RBY * rs + 0.10
    p = np.array([rx * math.sin(a), -ry * math.cos(a), z])
    t = np.array([rx * math.cos(a), ry * math.sin(a), 0.0])
    t /= max(float(np.linalg.norm(t)), 1e-9)
    n = radial_normal(p, rx, ry)
    return p, n, t, np.array([0.0, 0.0, 1.0])


def crown_point_at(a, z):
    rs = crown_radius_scale(z / H)
    rx = RBX * rs
    ry = RBY * rs
    p = np.array([rx * math.sin(a), -ry * math.cos(a), z])
    n = radial_normal(p, rx, ry)
    t = np.array([rx * math.cos(a), ry * math.sin(a), 0.0])
    t /= max(float(np.linalg.norm(t)), 1e-9)
    return p, n, t, np.cross(n, t)


def rounded_rectangle(center, axis_u, axis_v, width, height, radius, steps=6):
    half_w = width * 0.5 - radius
    half_h = height * 0.5 - radius
    points = []
    for cx, cy, start in ((half_w, half_h, 0.0), (-half_w, half_h, math.pi * 0.5),
                          (-half_w, -half_h, math.pi), (half_w, -half_h, math.pi * 1.5)):
        for k in range(steps):
            angle = start + (math.pi * 0.5) * k / steps
            points.append(center + axis_u * (cx + radius * math.cos(angle)) + axis_v * (cy + radius * math.sin(angle)))
    return points


def build_mesh(head):
    global RBX, RBY
    hp = np.array(head["positions"])
    z0 = float(hp[:, 2].max()) - 7.2
    sample = hp[(hp[:, 2] > z0 - 1.5) & (hp[:, 2] < z0 + 1.5)]
    center = (sample.min(0) + sample.max(0)) * 0.5
    center[2] = z0
    xy = sample[:, :2] - center[:2]
    radii = (sample[:, :2].max(0) - sample[:, :2].min(0)) * 0.5 + 0.45
    radii *= max(1.0, float(np.sqrt(((xy / radii) ** 2).sum(1)).max()) + 0.02)
    RX, RY = radii
    RBX, RBY = RX + 0.55, RY + 0.55

    d = dict(profile="FieldHat", positions=[], weights=[], triangles=[], uv=[],
             normals=[], triangle_materials=[], material_slots=SLOTS,
             contract="Fitted closed canvas crown; double-sided bound brim; leather band and stowed chin cord; root-bound with a three-bone rear-brim spring")

    def crown_weight(t, a):
        return dict(ROOT_W)

    def brim_weight_uv(t, a):
        return brim_weight(a, t)

    rows = np.linspace(0.0, 1.0, CROWN_ROWS)
    outer = add_surface(d, rows, lambda t, a: crown_point(t, a, False), crown_weight, 0,
                        uv_crown, lambda t, a: radial_normal(crown_point(t, a), RBX, RBY))
    inner = add_surface(d, rows, lambda t, a: crown_point(t, a, True), crown_weight, 4,
                        uv_crown, lambda t, a: -radial_normal(crown_point(t, a), RBX, RBY))

    # Crown top: soft concentric cap, outer canvas and inner lining.
    top_z = H - 0.45
    add_cap(d, outer[-1], np.array([0.0, 0.0, top_z]), 0, np.array([0.0, 0.0, 1.0]))
    add_cap(d, inner[-1], np.array([0.0, 0.0, top_z - THICK]), 4, np.array([0.0, 0.0, -1.0]))
    for i in range(SEG):
        i2 = (i + 1) % SEG
        ids = [outer[-1][i], outer[-1][i2], inner[-1][i2], inner[-1][i]]
        for tri in ((0, 1, 2), (0, 2, 3)):
            face(d, [ids[k] for k in tri], 2, [[0, 0], [1, 0], [1, 1]][:3], np.array([0.0, 0.0, 1.0]))

    # Opening edge: a leather-bound ring hiding the canvas/lining seam.
    for i in range(SEG):
        i2 = (i + 1) % SEG
        ids = [outer[0][i], inner[0][i], inner[0][i2], outer[0][i2]]
        for tri in ((0, 1, 2), (0, 2, 3)):
            face(d, [ids[k] for k in tri], 2, [[0, 0], [1, 0], [1, 1]], np.array([0.0, 0.0, -1.0]))

    # Brim top and underside, tucked 0.45 cm under the crown base.
    brim_rows = np.linspace(0.0, 1.0, BRIM_ROWS)
    add_surface(d, brim_rows, lambda u, a: brim_point(u, a, False), brim_weight_uv, 0,
                uv_brim, lambda u, a: np.array([0.0, 0.0, 1.0]))
    add_surface(d, brim_rows, lambda u, a: brim_point(u, a, True), brim_weight_uv, 1,
                uv_brim, lambda u, a: np.array([0.0, 0.0, -1.0]))

    # Closed outer edge and hidden inner edge.
    top_edge = [brim_point(1.0, TAU * i / SEG, False) for i in range(SEG)]
    bottom_edge = [brim_point(1.0, TAU * i / SEG, True) for i in range(SEG)]
    binding_path = [(top_edge[i] + bottom_edge[i]) * 0.5 for i in range(SEG)]
    tube(d, binding_path, 0.17, 1, lambda p: brim_weight(math.atan2(p[0], -p[1]) % TAU, 1.0), closed=True, sides=6)
    for i in range(SEG):
        i2 = (i + 1) % SEG
        ids = [vertex(d, brim_point(0.0, TAU * i / SEG, False), brim_weight(TAU * i / SEG, 0.0)),
               vertex(d, brim_point(0.0, TAU * i / SEG, True), brim_weight(TAU * i / SEG, 0.0)),
               vertex(d, brim_point(0.0, TAU * i2 / SEG, True), brim_weight(TAU * i2 / SEG, 0.0)),
               vertex(d, brim_point(0.0, TAU * i2 / SEG, False), brim_weight(TAU * i2 / SEG, 0.0))]
        for tri in ((0, 1, 2), (0, 2, 3)):
            face(d, [ids[k] for k in tri], 1, [[0, 0], [1, 0], [1, 1]], np.array([0.0, 0.0, 1.0]))

    # Band: leather strip around the crown, slightly proud of the canvas.
    band_rows = np.array([0.30, 3.20])
    add_surface(d, band_rows, lambda z, a: band_point(a, z)[0], lambda z, a: dict(ROOT_W), 2,
                uv_band, lambda z, a: band_point(a, z)[1])
    add_surface(d, band_rows, lambda z, a: band_point(a, z)[0] - band_point(a, z)[1] * 0.12,
                lambda z, a: dict(ROOT_W), 2, uv_band, lambda z, a: -band_point(a, z)[1])
    for i in range(SEG):
        i2 = (i + 1) % SEG
        for z, sign in ((0.30, -1.0), (3.20, 1.0)):
            p0, n0, _, _ = band_point(TAU * i / SEG, z)
            p1, n1, _, _ = band_point(TAU * i2 / SEG, z)
            ids = [vertex(d, p0, ROOT_W), vertex(d, p0 - n0 * 0.12, ROOT_W),
                   vertex(d, p1 - n1 * 0.12, ROOT_W), vertex(d, p1, ROOT_W)]
            for tri in ((0, 1, 2), (0, 2, 3)):
                face(d, [ids[k] for k in tri], 2, [[0, 0], [1, 0], [1, 1]], np.array([0.0, 0.0, sign]))

    # Rolled leather piping at the band edges reads as a finished strip.
    for z in (0.30, 3.20):
        piping = []
        for i in range(SEG):
            p, n, _, _ = band_point(TAU * i / SEG, z)
            piping.append(p + n * 0.02)
        tube(d, piping, 0.060, 2, ROOT_W, closed=True, sides=5)

    # Sweatband inside the opening.
    add_surface(d, np.array([0.15, 2.65]),
                lambda z, a: band_point(a, z)[0] - band_point(a, z)[1] * 0.50,
                lambda z, a: dict(ROOT_W), 2, uv_band, lambda z, a: -band_point(a, z)[1])

    # Brass buckle on the front-right, with a snug leather keeper.
    buckle_center, buckle_n, buckle_t, buckle_up = band_point(math.pi * 0.25, 1.75)
    frame_center = buckle_center + buckle_n * 0.16
    frame = rounded_rectangle(frame_center, buckle_t, buckle_up, 2.80, 1.90, 0.30, 6)
    tube(d, frame, 0.095, 3, ROOT_W, closed=True, sides=6)
    tube(d, [frame_center - buckle_t * 0.92 + buckle_n * 0.03, frame_center + buckle_t * 0.92 + buckle_n * 0.03],
         0.050, 3, ROOT_W, sides=6)
    tube(d, [frame_center + buckle_t * 0.15 + buckle_n * 0.03, frame_center + buckle_t * 0.15 + buckle_up * 0.66 + buckle_n * 0.03],
         0.042, 3, ROOT_W, sides=5)
    keeper_center, keeper_n, keeper_t, keeper_up = band_point(math.pi * 0.25 + 0.20, 1.75)
    keeper = rounded_rectangle(keeper_center + keeper_n * 0.10, keeper_n, keeper_up, 0.30, 3.02, 0.10, 4)
    tube(d, keeper, 0.050, 2, ROOT_W, closed=True, sides=5)

    # Brass vent eyelets with a dark interior disc.
    for a in (math.pi * 0.5 - 0.38, math.pi * 0.5 + 0.38, -math.pi * 0.5 - 0.38, -math.pi * 0.5 + 0.38):
        p, n, t, b = crown_point_at(a, 4.90)
        ring = [p + n * 0.05 + (t * math.cos(TAU * k / 20.0) + b * math.sin(TAU * k / 20.0)) * 0.30 for k in range(20)]
        tube(d, ring, 0.070, 3, ROOT_W, closed=True, sides=5)
        center_disc = vertex(d, p + n * 0.015, ROOT_W)
        disc = [vertex(d, p + n * 0.015 + (t * math.cos(TAU * k / 20.0) + b * math.sin(TAU * k / 20.0)) * 0.22, ROOT_W) for k in range(20)]
        for k in range(20):
            face(d, [center_disc, disc[k], disc[(k + 1) % 20]], 4, [[0, 0], [1, 0], [1, 1]], n)

    # Stowed leather chin cord around the back of the crown with a brass slider.
    cord = []
    for k in range(49):
        a = math.pi * 0.5 + math.pi * k / 48.0
        p, n, t, up = band_point(a, 1.75)
        cord.append(p + n * 0.18)
    tube(d, cord, 0.095, 2, ROOT_W, sides=6)
    slider_center = cord[24]
    slider_tangent = cord[25] - cord[23]
    slider_tangent /= max(float(np.linalg.norm(slider_tangent)), 1e-9)
    tube(d, [slider_center - slider_tangent * 0.45, slider_center + slider_tangent * 0.45], 0.130, 3, ROOT_W, sides=6)
    for endpoint in (cord[0], cord[-1]):
        p, n, t, up = band_point(math.pi * 0.5 if endpoint is cord[0] else math.pi * 1.5, 1.75)
        tube(d, [endpoint - t * 0.07, endpoint + t * 0.07], 0.115, 3, ROOT_W, sides=6)

    # Stitching: brim top line and band edges.
    edge_stitch = [brim_point(0.94, TAU * i / SEG, False) + np.array([0.0, 0.0, 0.035]) for i in range(SEG)]
    tube(d, edge_stitch, 0.032, 5, lambda p: brim_weight(math.atan2(p[0], -p[1]) % TAU, 0.94), closed=True, sides=4)
    for z in (0.40, 3.10):
        p0, n0, _, _ = band_point(0.0, z)
        stitch = []
        for i in range(SEG):
            p, n, _, _ = band_point(TAU * i / SEG, z)
            stitch.append(p + n * 0.015)
        tube(d, stitch, 0.028, 5, ROOT_W, closed=True, sides=4)

    # Rig: root, rear-brim spring chain, and a non-collinear left reference.
    back_inner = np.array([0.0, RBY - 0.45, 0.0])
    back_end = np.array([0.0, RBY - 0.45 + BRIM, -1.35])
    left_end = np.array([-(RBX - 0.45 + BRIM), 0.0, -1.8])
    bone_pos = [np.zeros(3), back_inner, (back_inner + back_end) * 0.5, back_end, left_end]
    names = ["HatRoot", "BrimBackBase", "BrimBackMid", "BrimBackEnd", "BrimLeft"]
    d["bones"] = {name: dict(index=i, parent=i - 1 if i < 3 else (0 if i == 4 else i - 1),
                             position=pos.tolist(), axes=np.eye(3).tolist())
                  for i, (name, pos) in enumerate(zip(names, bone_pos))}
    finish(d)
    return d, center, z0, RX, RY, names


def save_fit(head, d, center, z0, RX, RY):
    axes = np.array(head["bones"]["head"]["axes"]).T
    scale = np.linalg.norm(axes, axis=0)
    rot = axes / scale
    quat = Matrix(rot.T.tolist()).to_quaternion()
    w, x, y, z = quat
    pitch = math.asin(np.clip(2 * (z * x - w * y), -1, 1))
    yaw = math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
    roll = math.atan2(-2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
    fit = dict(location=np.linalg.solve(axes, center - np.array(head["bones"]["head"]["position"])).tolist(),
               rotation=[math.degrees(v) for v in (pitch, yaw, roll)],
               scale=(1 / scale).tolist())
    (SRC / "fit.json").write_text(json.dumps(dict(fits={"jason": fit}, native_head=head["source"],
                                                  brim_world_z=z0, opening_radii_cm=[RX, RY],
                                                  triangles=len(d["triangles"])), indent=2), encoding="utf-8")
    return fit


def make_materials():
    def image(name, non_color=False):
        im = bpy.data.images.load(str(SRC / "Textures" / name), check_existing=True)
        if non_color:
            im.colorspace_settings.name = "Non-Color"
        return im

    def textured(name, base_name, tint=(1.0, 1.0, 1.0), rough_bias=0.0):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        nodes = m.node_tree.nodes
        links = m.node_tree.links
        bsdf = nodes["Principled BSDF"]
        uv = nodes.new("ShaderNodeTexCoord")
        mapping = nodes.new("ShaderNodeMapping")
        links.new(uv.outputs["UV"], mapping.inputs["Vector"])
        tex = {}
        for channel, non_color in (("BaseColor", False), ("Normal", True), ("ORM", True)):
            node = nodes.new("ShaderNodeTexImage")
            node.image = image(f"T_FieldHat_{base_name}_{channel}.png", non_color)
            links.new(mapping.outputs["Vector"], node.inputs["Vector"])
            tex[channel] = node
        split = nodes.new("ShaderNodeSeparateColor")
        links.new(tex["ORM"].outputs["Color"], split.inputs[0])
        links.new(split.outputs["Green"], bsdf.inputs["Roughness"])
        links.new(split.outputs["Blue"], bsdf.inputs["Metallic"])
        normal = nodes.new("ShaderNodeNormalMap")
        links.new(tex["Normal"].outputs["Color"], normal.inputs["Color"])
        links.new(normal.outputs[0], bsdf.inputs["Normal"])
        colour = tex["BaseColor"].outputs["Color"]
        if tint != (1.0, 1.0, 1.0):
            mix = nodes.new("ShaderNodeMixRGB")
            mix.blend_type = "MULTIPLY"
            mix.inputs[0].default_value = 1.0
            mix.inputs[2].default_value = (*tint, 1.0)
            links.new(colour, mix.inputs[1])
            colour = mix.outputs[0]
        links.new(colour, bsdf.inputs["Base Color"])
        if rough_bias:
            add = nodes.new("ShaderNodeMath")
            add.operation = "ADD"
            add.inputs[1].default_value = rough_bias
            links.new(split.outputs["Green"], add.inputs[0])
            links.new(add.outputs[0], bsdf.inputs["Roughness"])
        return m

    def solid(name, colour, roughness, metallic=0.0):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = m.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = (*colour, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        return m

    return [
        textured("Canvas", "Canvas"),
        textured("CanvasUnder", "Canvas", tint=(0.62, 0.62, 0.60), rough_bias=0.06),
        textured("Leather", "Leather"),
        solid("Brass", (0.62, 0.43, 0.20), 0.30, 0.85),
        solid("Lining", (0.055, 0.040, 0.028), 0.86, 0.0),
        solid("Thread", (0.55, 0.48, 0.32), 0.62, 0.0),
    ]


def build_blender(d, names):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    materials = make_materials()
    mesh = bpy.data.meshes.new("FieldHat")
    mesh.from_pydata([(x * 0.01, -y * 0.01, z * 0.01) for x, y, z in d["positions"]], [], d["triangles"])
    mesh.update()
    obj = bpy.data.objects.new("FieldHat", mesh)
    bpy.context.collection.objects.link(obj)
    for material in materials:
        mesh.materials.append(material)
    uv = mesh.uv_layers.new(name="PhysicalGarmentUV")
    for fi, poly in enumerate(mesh.polygons):
        poly.material_index = d["triangle_materials"][fi]
        poly.use_smooth = True
        for ci, li in enumerate(poly.loop_indices):
            a, b = d["uv"][fi][ci]
            uv.data[li].uv = (a, 1.0 - b)
    mesh.normals_split_custom_set([(x, -y, z) for row in d["normals"] for x, y, z in row])

    arm = bpy.data.armatures.new("FieldHatRig")
    rig = bpy.data.objects.new("FieldHatRig", arm)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for i, name in enumerate(names):
        bone = arm.edit_bones.new(name)
        pos = d["bones"][name]["position"]
        bone.head = (pos[0] * 0.01, -pos[1] * 0.01, pos[2] * 0.01)
        bone.tail = bone.head + Vector((0.0, 0.025, 0.0))
        bone.use_deform = True
        if i:
            bone.parent = arm.edit_bones[names[d["bones"][name]["parent"]]]
    bpy.ops.object.mode_set(mode="OBJECT")
    groups = {name: obj.vertex_groups.new(name=name) for name in names}
    for vi, weights in enumerate(d["weights"]):
        for name, value in weights.items():
            if value > 0.0:
                groups[name].add([vi], value, "REPLACE")
    obj.parent = rig
    obj.modifiers.new("FieldHatSkin", "ARMATURE").object = rig
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(filepath=str(SRC / "Exports/FieldHat.fbx"), use_selection=True,
                             object_types={"MESH", "ARMATURE"}, add_leaf_bones=False,
                             use_armature_deform_only=True, bake_anim=False,
                             axis_forward="-Y", axis_up="Z", mesh_smooth_type="FACE")
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(SRC / "Exports/FieldHat.blend"))
    return obj


def main():
    head = json.loads((SRC / "native_head_jason.json").read_text(encoding="utf-8"))
    d, center, z0, RX, RY, names = build_mesh(head)
    (SRC / "Authored/hat.json").write_text(json.dumps(d, separators=(",", ":")), encoding="utf-8")
    fit = save_fit(head, d, center, z0, RX, RY)
    obj = build_blender(d, names)
    sys.path.insert(0, str(ROOT / "Tools/FieldHat"))
    from render_icon import render_current
    item = dict(grid_w=2, grid_h=2, ue_icon="Icons/FieldHat20261019/ue_field_hat.png")
    result = render_current("ue_field_hat", obj, item=item, camera_offset=(0.75, 3.0, 1.15))
    (SRC / "authored.json").write_text(json.dumps(dict(completed=True, triangles=len(d["triangles"]),
                                                       bones=names, fit=fit,
                                                       fbx=str(SRC / "Exports/FieldHat.fbx"),
                                                       blend=str(SRC / "Exports/FieldHat.blend"),
                                                       icon=str(SRC / "ue_field_hat.png"),
                                                       icon_fill=result["fill"], runtime_tested=False),
                                                  indent=2), encoding="utf-8")
    print("FIELD_HAT_AUTHORED", len(d["triangles"]), "fill", result["fill"], flush=True)


if __name__ == "__main__":
    main()
