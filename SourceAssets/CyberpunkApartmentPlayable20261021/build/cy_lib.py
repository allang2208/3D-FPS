"""cy_lib — geometry / material / UV toolkit for the Cyberpunk Apartment build.

Everything is deterministic (seeded RNG), idempotent (collections are rebuilt),
and expressed in metres with Z up.

Convention: the facade faces -Y. Interior floor at Z=0, ceiling at Z=2.95.
"""
from __future__ import annotations

import math
import os
import random
from typing import Iterable, Sequence

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

PROJ = r"D:\CyberpunkApartment"
TEX = os.path.join(PROJ, "textures")
ROOT = "CP"

# material key -> (bpy material, metres covered by one texture tile)
MATS: dict[str, tuple] = {}


# ---------------------------------------------------------------------------
# collections
# ---------------------------------------------------------------------------


def col(name: str, parent: str | None = ROOT) -> bpy.types.Collection:
    """Get-or-create a collection (optionally nested under `parent`)."""
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        scene = bpy.context.scene
        if parent:
            p = bpy.data.collections.get(parent) or scene.collection
            p.children.link(c)
        else:
            scene.collection.children.link(c)
    return c


def reset_col(name: str) -> bpy.types.Collection:
    """Remove every object in a collection (recursively) and return it."""
    c = bpy.data.collections.get(name)
    if c is None:
        return col(name)
    for ob in list(c.all_objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for child in list(c.children):
        for ob in list(child.all_objects):
            bpy.data.objects.remove(ob, do_unlink=True)
    return c


def purge_meshes() -> None:
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)


# ---------------------------------------------------------------------------
# materials
# ---------------------------------------------------------------------------


def tex(name: str) -> str:
    return os.path.join(TEX, name)


def mat(key: str) -> bpy.types.Material:
    """Material by registry key, with lazy registry rebuild."""
    if key in MATS:
        return MATS[key][0]
    m = bpy.data.materials.get(key)
    if m is not None:
        MATS[key] = (m, 2.0)
        return m
    m = bpy.data.materials.new(key)
    m.use_nodes = True
    MATS[key] = (m, 2.0)
    return m


def tile_of(key: str) -> float:
    return MATS.get(key, (None, 2.0))[1]


def reg(key: str, material, tile: float) -> None:
    MATS[key] = (material, tile)


def principled(key: str, color, rough=0.5, metal=0.0, emit=None, emit_str=0.0,
               alpha=1.0, tile=2.0, ior=1.45) -> bpy.types.Material:
    """Simple flat PBR material (no textures)."""
    m = bpy.data.materials.get(key) or bpy.data.materials.new(key)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (300, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (0, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = ior
    if emit is not None:
        bsdf.inputs["Emission Color"].default_value = (*emit, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emit_str
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        m.blend_method = "BLEND"
        try:
            m.shadow_method = "HASHED"
        except Exception:
            pass
    reg(key, m, tile)
    return m


def emission(key: str, color, strength=5.0, base=(0.02, 0.02, 0.02)) -> bpy.types.Material:
    return principled(key, base, rough=0.35, emit=color, emit_str=strength, tile=1.0)


def node(mat_key: str, bl_idname: str, loc=(0, 0), name=None):
    nt = mat(mat_key).node_tree
    n = nt.nodes.new(bl_idname)
    n.location = loc
    if name:
        n.name = name
    return n


# ---------------------------------------------------------------------------
# mesh accumulation
# ---------------------------------------------------------------------------


def rot_matrix(rot) -> Matrix:
    if rot is None:
        return Matrix.Identity(4)
    if isinstance(rot, Matrix):
        return rot.to_4x4()
    return Euler(rot, "XYZ").to_matrix().to_4x4()


class MB:
    """Mesh accumulator: many primitives -> one object with material slots."""

    def __init__(self, name: str, collection: str, bevel: float = 0.0,
                 bevel_seg: int = 2, shade_smooth: bool = False):
        self.name = name
        self.coll = collection
        self.verts: list[tuple[float, float, float]] = []
        self.faces: list[tuple[int, ...]] = []
        self.fmat: list[int] = []
        self.keys: list[str] = []
        self.bevel = bevel
        self.bevel_seg = bevel_seg
        self.smooth = shade_smooth
        self._stack: list[Matrix] = [Matrix.Identity(4)]

    # -- local frame stack -------------------------------------------------
    def push(self, loc=(0, 0, 0), rot=0.0):
        M = Matrix.Translation(Vector(loc)) @ Matrix.Rotation(rot, 4, "Z")
        self._stack.append(self._stack[-1] @ M)
        return self

    def pop(self):
        if len(self._stack) > 1:
            self._stack.pop()
        return self

    def _xf(self, verts):
        M = self._stack[-1]
        if M == Matrix.Identity(4):
            return [tuple(v) for v in verts]
        return [tuple(M @ Vector(v)) for v in verts]

    # -- internals ---------------------------------------------------------
    def _slot(self, key: str) -> int:
        if key not in self.keys:
            self.keys.append(key)
        return self.keys.index(key)

    def add(self, verts, faces, key: str) -> None:
        base = len(self.verts)
        self.verts.extend(self._xf(verts))
        idx = self._slot(key)
        for f in faces:
            self.faces.append(tuple(base + i for i in f))
            self.fmat.append(idx)

    # -- primitives --------------------------------------------------------
    def box(self, size, loc=(0, 0, 0), rot=None, key="concrete_wall", taper=None):
        sx, sy, sz = (size if isinstance(size, (tuple, list)) else (size, size, size))
        hx, hy, hz = sx / 2, sy / 2, sz / 2
        v = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
             (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)]
        if taper:
            tx, ty = taper
            for i in (4, 5, 6, 7):
                v[i] = (v[i][0] * tx, v[i][1] * ty, v[i][2])
        f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        M = rot_matrix(rot)
        T = Matrix.Translation(Vector(loc))
        v = [tuple((T @ M @ Vector(p))) for p in v]
        self.add(v, f, key)

    def prism(self, profile, depth, loc=(0, 0, 0), rot=None, key="metal_dark"):
        """profile: list of (x,z) in local XY->XZ, extruded along Y by `depth`."""
        hd = depth / 2
        n = len(profile)
        v = [(p[0], -hd, p[1]) for p in profile] + [(p[0], hd, p[1]) for p in profile]
        f = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
        for i in range(n):
            j = (i + 1) % n
            f.append((i, j, j + n, i + n))
        M = rot_matrix(rot)
        T = Matrix.Translation(Vector(loc))
        v = [tuple((T @ M @ Vector(p))) for p in v]
        self.add(v, f, key)

    def cyl(self, r, h, loc=(0, 0, 0), rot=None, seg=24, key="metal_dark",
            r2=None, caps=True):
        r2 = r if r2 is None else r2
        v = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            v.append((r * math.cos(a), r * math.sin(a), -h / 2))
        for i in range(seg):
            a = 2 * math.pi * i / seg
            v.append((r2 * math.cos(a), r2 * math.sin(a), h / 2))
        f = []
        for i in range(seg):
            j = (i + 1) % seg
            f.append((i, j, j + seg, i + seg))
        if caps:
            f.append(tuple(range(seg - 1, -1, -1)))
            f.append(tuple(range(seg, 2 * seg)))
        M = rot_matrix(rot)
        T = Matrix.Translation(Vector(loc))
        v = [tuple((T @ M @ Vector(p))) for p in v]
        self.add(v, f, key)

    def tube(self, points: Sequence[Sequence[float]], r: float, key="metal_dark", seg=8):
        """Polyline tube (no caps) built from ring extrusion."""
        pts = [Vector(p) for p in points]
        rings = []
        for i, p in enumerate(pts):
            if i == 0:
                d = (pts[1] - pts[0])
            elif i == len(pts) - 1:
                d = (pts[-1] - pts[-2])
            else:
                d = (pts[i + 1] - pts[i - 1])
            if d.length < 1e-9:
                d = Vector((0, 0, 1))
            d.normalize()
            up = Vector((0, 0, 1)) if abs(d.z) < 0.95 else Vector((1, 0, 0))
            side = d.cross(up).normalized()
            up2 = side.cross(d).normalized()
            ring = []
            for k in range(seg):
                a = 2 * math.pi * k / seg
                ring.append(tuple(p + side * (r * math.cos(a)) + up2 * (r * math.sin(a))))
            rings.append(ring)
        v = [p for ring in rings for p in ring]
        f = []
        for i in range(len(rings) - 1):
            for k in range(seg):
                k2 = (k + 1) % seg
                a0 = i * seg + k
                b0 = i * seg + k2
                a1 = (i + 1) * seg + k
                b1 = (i + 1) * seg + k2
                f.append((a0, b0, b1, a1))
        self.add(v, f, key)

    def quad(self, p0, p1, p2, p3, key):
        self.add([p0, p1, p2, p3], [(0, 1, 2, 3)], key)

    def plane(self, w, h, loc=(0, 0, 0), rot=None, key="plaster"):
        hw, hh = w / 2, h / 2
        v = [(-hw, 0, -hh), (hw, 0, -hh), (hw, 0, hh), (-hw, 0, hh)]
        M = rot_matrix(rot)
        T = Matrix.Translation(Vector(loc))
        v = [tuple((T @ M @ Vector(p))) for p in v]
        self.add(v, [(0, 1, 2, 3)], key)

    def disc(self, r, loc=(0, 0, 0), rot=None, seg=24, key="metal_dark", r2=0.0):
        v = [(0, 0, 0)]
        for i in range(seg):
            a = 2 * math.pi * i / seg
            v.append((r * math.cos(a), r * math.sin(a), 0))
        f = [(0, i + 2, i + 1) if False else (0, (i + 1) % seg + 1, (i + 2) % seg + 1)
             for i in range(seg)]
        M = rot_matrix(rot)
        T = Matrix.Translation(Vector(loc))
        v = [tuple((T @ M @ Vector(p))) for p in v]
        self.add(v, f, key)

    def sphere(self, r, loc=(0, 0, 0), seg=16, rings=10, key="metal_dark", squash=1.0):
        v = [(0, 0, r * squash)]
        for i in range(1, rings):
            ph = math.pi * i / rings
            for k in range(seg):
                th = 2 * math.pi * k / seg
                v.append((r * math.sin(ph) * math.cos(th),
                          r * math.sin(ph) * math.sin(th),
                          r * math.cos(ph) * squash))
        v.append((0, 0, -r * squash))
        f = []
        for k in range(seg):
            f.append((0, 1 + k, 1 + (k + 1) % seg))
        for i in range(rings - 2):
            for k in range(seg):
                a = 1 + i * seg + k
                b = 1 + i * seg + (k + 1) % seg
                c = 1 + (i + 1) * seg + (k + 1) % seg
                d = 1 + (i + 1) * seg + k
                f.append((a, b, c, d))
        last = len(v) - 1
        base = 1 + (rings - 2) * seg
        for k in range(seg):
            f.append((last, base + (k + 1) % seg, base + k))
        T = Matrix.Translation(Vector(loc))
        v = [tuple((T @ Vector(p))) for p in v]
        self.add(v, f, key)

    # -- finalise ----------------------------------------------------------
    def build(self, uv_world: bool = True):
        me = bpy.data.meshes.new(self.name)
        me.from_pydata(self.verts, [], [f for f in self.faces])
        me.validate(verbose=False)
        ob = bpy.data.objects.new(self.name, me)
        col(self.coll).objects.link(ob)

        for key in self.keys:
            ob.data.materials.append(mat(key))

        # material index per polygon
        if len(self.fmat) == len(me.polygons):
            for p, mi in zip(me.polygons, self.fmat):
                p.material_index = mi

        if uv_world:
            uv_box_project(ob, self.keys)
        if self.bevel > 0:
            bevel_obj(ob, self.bevel, self.bevel_seg)
        if self.smooth:
            smooth_obj(ob)
        me.update()
        return ob


def uv_box_project(ob: bpy.types.Object, keys: list[str]) -> None:
    """World-space box projection, scaled by each material's physical tile size."""
    me = ob.data
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    me.calc_loop_triangles()
    tiles = [tile_of(k) for k in keys]
    mw = ob.matrix_world
    for poly in me.polygons:
        n = poly.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        tile = tiles[poly.material_index] if poly.material_index < len(tiles) else 2.0
        tile = tile or 2.0
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            if ax == 0:
                u, w = v.y, v.z
            elif ax == 1:
                u, w = v.x, v.z
            else:
                u, w = v.x, v.y
            uv.data[li].uv = (u / tile, w / tile)


def bevel_obj(ob, width=0.006, segments=2, angle=35.0) -> None:
    mod = ob.modifiers.new("bev", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(angle)
    mod.harden_normals = False
    for attr in ("use_clamp_overlap", "clamp_overlap"):
        if hasattr(mod, attr):
            setattr(mod, attr, True)
            break
    bpy.context.view_layer.objects.active = ob
    try:
        bpy.ops.object.modifier_apply(modifier=mod.name)
    except Exception:
        ob.modifiers.remove(mod)


def smooth_obj(ob) -> None:
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    try:
        bpy.ops.object.shade_auto_smooth(angle=math.radians(32))
    except Exception:
        for p in ob.data.polygons:
            p.use_smooth = True
    ob.select_set(False)


def select_only(ob) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def apply_mods(ob) -> None:
    select_only(ob)
    for m in list(ob.modifiers):
        try:
            bpy.ops.object.modifier_apply(modifier=m.name)
        except Exception:
            pass


def join(objs, name: str):
    objs = [o for o in objs if o is not None]
    if not objs:
        return None
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    ob.data.name = name + "_mesh"
    return ob


# ---------------------------------------------------------------------------
# high level builders
# ---------------------------------------------------------------------------


def text_mesh(name: str, body: str, size: float, loc, rot=(math.pi / 2, 0, 0),
              key="neon_cyan", extrude=0.02, align="CENTER", col_name="DETAIL"):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.extrude = extrude
    cu.align_x = align
    cu.align_y = "CENTER"
    cu.resolution_u = 2
    ob = bpy.data.objects.new(name, cu)
    col(col_name).objects.link(ob)
    ob.location = loc
    ob.rotation_euler = rot
    select_only(ob)
    bpy.ops.object.convert(target="MESH")
    ob = bpy.context.view_layer.objects.active
    ob.data.materials.append(mat(key))
    return ob


def tube_curve(name: str, points, radius: float, key: str, col_name="DETAIL",
               resolution=6, cyclic=False):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 2
    cu.resolution_u = resolution
    sp = cu.splines.new("POLY")
    sp.points.add(len(points) - 1)
    for i, p in enumerate(points):
        sp.points[i].co = (p[0], p[1], p[2], 1.0)
    sp.use_cyclic_u = cyclic
    ob = bpy.data.objects.new(name, cu)
    col(col_name).objects.link(ob)
    ob.data.materials.append(mat(key))
    return ob


def catenary(p0, p1, sag=0.3, n=12):
    p0, p1 = Vector(p0), Vector(p1)
    out = []
    for i in range(n + 1):
        t = i / n
        p = p0.lerp(p1, t)
        p.z -= math.sin(math.pi * t) * sag
        out.append(tuple(p))
    return out


def warn(text: str) -> None:
    print(f"[cy_lib] {text}", flush=True)


def rng(seed: int) -> random.Random:
    return random.Random(seed)


# ---------------------------------------------------------------------------
# arch primitives with openings
# ---------------------------------------------------------------------------


def wall_run(mb: MB, axis: str, a0: float, a1: float, fixed: float, z0: float, z1: float,
             thick: float, key: str, openings: Iterable[tuple] = ()) -> None:
    """Build a wall along X (axis='x') or Y (axis='y') with rectangular openings.

    openings: (start, end, z_bottom, z_top) in the same axis (start/end) domain.
    """
    ops = sorted(openings, key=lambda o: o[0])
    cursor = a0
    for (s, e, zb, zt) in ops:
        if s > cursor:
            _wall_seg(mb, axis, cursor, s, fixed, z0, z1, thick, key)
        # below opening
        if zb > z0:
            _wall_seg(mb, axis, s, e, fixed, z0, zb, thick, key)
        # above opening
        if zt < z1:
            _wall_seg(mb, axis, s, e, fixed, zt, z1, thick, key)
        cursor = e
    if cursor < a1:
        _wall_seg(mb, axis, cursor, a1, fixed, z0, z1, thick, key)


def _wall_seg(mb: MB, axis, s, e, fixed, z0, z1, thick, key):
    if e - s < 1e-4 or z1 - z0 < 1e-4:
        return
    if axis == "x":
        mb.box((e - s, thick, z1 - z0), ((s + e) / 2, fixed, (z0 + z1) / 2), key=key)
    else:
        mb.box((thick, e - s, z1 - z0), (fixed, (s + e) / 2, (z0 + z1) / 2), key=key)