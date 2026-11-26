"""Metric AAA hard-surface & craft geometry kernel for Blender 5.1 with helical braided rope & 3D vertex weathering."""
import math
import random
from pathlib import Path

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

# Physical UV repeat scale in metres per 1.0 UV unit, matched to each UE material's texture scale.
UV_SCALES_M = {
    'Oak': 1.00,
    'OiledOak': 1.00,
    'DarkWood': 1.00,
    'Sawn': 1.00,
    'Endgrain': 0.24,
    'Lime': 1.00,
    'Stone': 1.00,
    'ScaleIron': 0.55,
    'Iron': 0.55,
    'Steel': 0.40,
    'Brass': 0.40,
    'LeatherMain': 0.46,
    'LeatherDark': 0.44,
    'WaxedThread': 0.20,
    'Blanket': 0.62,
    'Linen': 0.35,
    'Rope': 0.24,
    'Hay': 0.85,
}

PREVIEW_COLORS = {
    'Oak': (0.28, 0.20, 0.12),
    'OiledOak': (0.34, 0.21, 0.10),
    'DarkWood': (0.15, 0.10, 0.06),
    'Sawn': (0.48, 0.35, 0.20),
    'Endgrain': (0.42, 0.30, 0.17),
    'Lime': (0.76, 0.72, 0.65),
    'Stone': (0.42, 0.41, 0.38),
    'ScaleIron': (0.09, 0.09, 0.10),
    'Iron': (0.15, 0.15, 0.16),
    'Steel': (0.44, 0.45, 0.47),
    'Brass': (0.54, 0.39, 0.14),
    'LeatherMain': (0.31, 0.14, 0.06),
    'LeatherDark': (0.16, 0.08, 0.04),
    'WaxedThread': (0.72, 0.60, 0.38),
    'Blanket': (0.36, 0.26, 0.18),
    'Linen': (0.58, 0.52, 0.40),
    'Rope': (0.34, 0.24, 0.13),
    'Hay': (0.58, 0.46, 0.20),
}


def cm(p):
    """Convert UE centimetre coordinate (X, Y, Z) to Blender metre coordinate (X, -Y, Z)."""
    return Vector((p[0] / 100.0, -p[1] / 100.0, p[2] / 100.0))


def ensure_materials():
    mats = {}
    for name, rgb in PREVIEW_COLORS.items():
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.diffuse_color = (*rgb, 1.0)
        mats[name] = m
    return mats


def eval_cubic(p0, p1, p2, p3, t):
    u = 1.0 - t
    return (u * u * u) * Vector(p0) + (3 * u * u * t) * Vector(p1) + (3 * u * t * t) * Vector(p2) + (t * t * t) * Vector(p3)


def sample_beziers(start, segs, steps_per_seg=10):
    pts = [Vector(start)]
    cur = Vector(start)
    for c1, c2, end in segs:
        for i in range(1, steps_per_seg + 1):
            pts.append(eval_cubic(cur, c1, c2, end, i / steps_per_seg))
        cur = Vector(end)
    return pts


def _active(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def _apply_mod(obj, mod):
    _active(obj)
    bpy.ops.object.modifier_apply(modifier=mod.name)


def _hash3(x, y, z):
    """Smooth deterministic pseudo-noise in [0, 1] for organic vertex weathering."""
    v = (
        math.sin(x * 7.3 + y * 5.1 + z * 6.7) * 0.42
        + math.cos(x * 13.7 - y * 11.3 + z * 9.2) * 0.33
        + math.sin(x * 23.1 + y * 19.7 - z * 17.5) * 0.25
    )
    return 0.5 + 0.5 * v


def bake_weathering_vcol(obj, ground_mud_height_cm=46.0, is_wall_mounted=False):
    """Bake 3D physical wear/grime into FBX vertex color layer 'Col':
       R = cavity dirt & crevice grime (0 clean .. 1 dark crevice)
       G = ground mud splash & lower dampness (0 dry .. 1 earthy mud near Z=0)
       B = edge wear & hand-rubbed polish (0 unrubbed .. 1 worn convex edge)
    """
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    # Compute mesh height span for relative contact/wear cues
    zs = [vv.co.z for vv in bm.verts]
    z_min = min(zs) if zs else 0.0
    z_max = max(zs) if zs else 1.0
    z_span = max(0.05, z_max - z_min)

    v_rgb = {}
    for vv in bm.verts:
        co = vv.co
        n_v = vv.normal
        # Measure signed convexity & concavity against adjacent face normals
        convex_sum = 0.0
        concave_sum = 0.0
        n_edges = 0
        for e in vv.link_edges:
            if len(e.link_faces) == 2:
                f0, f1 = e.link_faces[0], e.link_faces[1]
                ang = e.calc_face_angle(0.0)
                if ang > 0.12:
                    # Signed test: vector from f0 center to f1 center dotted with f0 normal
                    d = (f1.calc_center_median() - f0.calc_center_median()).dot(f0.normal)
                    norm_a = min(1.0, ang / 1.57)
                    if d < 0.0:
                        convex_sum += norm_a
                    else:
                        concave_sum += norm_a
                    n_edges += 1
        noise_m = _hash3(co.x * 1.4, co.y * 1.4, co.z * 1.4)
        noise_f = _hash3(co.x * 4.5 + 2.1, co.y * 4.5 - 1.3, co.z * 4.5 + 0.7)

        # R: Cavity grime + downward-facing underside grime + organic blotch
        cav = min(1.0, concave_sum / max(1.0, n_edges * 0.65))
        underside = max(0.0, -n_v.z) * 0.45
        r_grime = min(1.0, max(0.0, cav * 0.85 + underside + (noise_m - 0.38) * 0.32 + 0.08 * noise_f))

        # G: Ground mud splash & lower dampness near Z = 0 (disabled on wall-mounted racks)
        if is_wall_mounted:
            g_mud = min(1.0, max(0.0, 0.12 * noise_m * (1.0 - (co.z - z_min) / z_span)))
        else:
            z_cm = co.z * 100.0
            h_frac = max(0.0, 1.0 - (z_cm - 2.0) / max(10.0, ground_mud_height_cm))
            g_mud = min(1.0, max(0.0, (h_frac ** 1.45) * (0.68 + 0.48 * noise_m)))

        # B: Convex edge wear & upward high-touch scuffing
        conv = min(1.0, convex_sum / max(1.0, n_edges * 0.55))
        top_touch = max(0.0, n_v.z) * 0.25 * ((co.z - z_min) / z_span)
        b_wear = min(1.0, max(0.0, conv * 0.82 + top_touch + (noise_f - 0.45) * 0.22))

        v_rgb[vv.index] = (r_grime, g_mud, b_wear, 1.0)

    bm.free()

    # Write into Blender 5.1 Float Color Attribute (domain CORNER) named 'Col'
    for attr in list(mesh.color_attributes):
        mesh.color_attributes.remove(attr)
    col_attr = mesh.color_attributes.new(name='Col', type='BYTE_COLOR', domain='CORNER')
    mesh.color_attributes.active_color = col_attr
    mesh.color_attributes.render_color_index = 0
    loops = mesh.loops
    for i, lp in enumerate(loops):
        col_attr.data[i].color = v_rgb[lp.vertex_index]


class AssetBuilder:
    """Accumulates cleanly beveled, watertight parts for one UE StaticMesh."""

    def __init__(self, name, seed=4301, ground_mud_cm=46.0, is_wall_mounted=False):
        self.name = name
        self.rng = random.Random(seed)
        self.ground_mud_cm = ground_mud_cm
        self.is_wall_mounted = is_wall_mounted
        self.mats = ensure_materials()
        self.parts = []
        self.colliders = []
        self.xform_stack = [Matrix.Identity(4)]

    def push_xform(self, loc_cm=(0, 0, 0), rot_deg=(0, 0, 0)):
        m = Matrix.Translation(Vector(loc_cm)) @ Euler(
            (math.radians(rot_deg[0]), math.radians(rot_deg[1]), math.radians(rot_deg[2])), 'XYZ'
        ).to_matrix().to_4x4()
        self.xform_stack.append(self.xform_stack[-1] @ m)

    def pop_xform(self):
        self.xform_stack.pop()

    def to_asset_cm(self, p):
        q = self.xform_stack[-1] @ Vector(p)
        return (q.x, q.y, q.z)

    def add_collider(self, center_cm, size_cm, yaw_deg=0.0):
        c = self.to_asset_cm(center_cm)
        self.colliders.append(dict(
            center=[round(float(c[0]), 2), round(float(c[1]), 2), round(float(c[2]), 2)],
            size=[round(float(size_cm[0]), 2), round(float(size_cm[1]), 2), round(float(size_cm[2]), 2)],
            yaw=round(float(yaw_deg), 2),
        ))

    def _new_mesh_obj(self, label, verts_cm, faces, mat_name, face_mats=None):
        verts_m = [cm(self.to_asset_cm(p)) for p in verts_cm]
        data = bpy.data.meshes.new(label)
        data.from_pydata(verts_m, [], faces)
        data.update()
        obj = bpy.data.objects.new(label, data)
        bpy.context.collection.objects.link(obj)
        if face_mats is None:
            data.materials.append(self.mats[mat_name])
        else:
            ordered = []
            idx_map = {}
            for fm in face_mats:
                if fm not in idx_map:
                    idx_map[fm] = len(ordered)
                    ordered.append(fm)
                    data.materials.append(self.mats[fm])
            for poly, fm in zip(data.polygons, face_mats):
                poly.material_index = idx_map[fm]
        bm = bmesh.new()
        bm.from_mesh(data)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(data)
        bm.free()
        self.parts.append(obj)
        return obj

    def _uv_box(self, obj, long_axis=2, offset=None):
        if offset is None:
            offset = (self.rng.random() * 0.7, self.rng.random() * 0.7)
        data = obj.data
        uv_layer = data.uv_layers.get('UV0') or data.uv_layers.new(name='UV0')
        uv_layer.active_render = True
        data.uv_layers.active = uv_layer
        mats = list(data.materials)
        for poly in data.polygons:
            mat_name = mats[poly.material_index].name if poly.material_index < len(mats) else 'Oak'
            scale_m = UV_SCALES_M.get(mat_name, 1.0)
            n = poly.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            other = [i for i in range(3) if i != long_axis]
            trans = next((i for i in other if i != ax), other[0])
            for li in poly.loop_indices:
                co = data.vertices[data.loops[li].vertex_index].co
                if ax == long_axis:
                    u, v = co[other[0]] / scale_m + 0.5, co[other[1]] / scale_m + 0.5
                else:
                    u, v = co[trans] / scale_m + offset[0], co[long_axis] / scale_m + offset[1]
                uv_layer.data[li].uv = (u, v)

    def _soften(self, obj, bevel_cm=0.22, segments=2, smooth_deg=48.0):
        if bevel_cm > 0.0:
            mod = obj.modifiers.new('Bevel', 'BEVEL')
            mod.width = bevel_cm / 100.0
            mod.segments = segments
            mod.limit_method = 'ANGLE'
            mod.angle_limit = math.radians(35.0)
            mod.use_clamp_overlap = True
            _apply_mod(obj, mod)
        for poly in obj.data.polygons:
            poly.use_smooth = True
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        thresh = math.radians(smooth_deg)
        for e in bm.edges:
            if e.is_manifold:
                e.smooth = e.calc_face_angle() < thresh
        bm.to_mesh(obj.data)
        bm.free()
        wn = obj.modifiers.new('WeightedNormal', 'WEIGHTED_NORMAL')
        wn.keep_sharp = True
        wn.weight = 45
        _apply_mod(obj, wn)

    def _bake_smooth(self, obj, smooth_deg=55.0):
        for poly in obj.data.polygons:
            poly.use_smooth = True
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        thresh = math.radians(smooth_deg)
        for e in bm.edges:
            if e.is_manifold:
                e.smooth = e.calc_face_angle() < thresh
        bm.to_mesh(obj.data)
        bm.free()

    def block(self, label, center_cm, size_cm, mat='Oak', rot_deg=(0, 0, 0), bevel_cm=0.25,
              segments=2, endgrain_axis=None):
        sx, sy, sz = size_cm[0] * 0.5, size_cm[1] * 0.5, size_cm[2] * 0.5
        local_pts = [
            (-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
            (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz),
        ]
        rot_m = Euler((math.radians(rot_deg[0]), math.radians(rot_deg[1]), math.radians(rot_deg[2])), 'XYZ').to_matrix()
        c = Vector(center_cm)
        verts = [tuple(c + rot_m @ Vector(p)) for p in local_pts]
        faces = [
            (0, 3, 2, 1), (4, 5, 6, 7),
            (0, 1, 5, 4), (2, 3, 7, 6),
            (0, 4, 7, 3), (1, 2, 6, 5),
        ]
        face_mats = None
        if endgrain_axis is not None:
            eg_faces = {0: (4, 5), 1: (2, 3), 2: (0, 1)}[endgrain_axis]
            face_mats = ['Endgrain' if idx in eg_faces else mat for idx in range(6)]
        obj = self._new_mesh_obj(label, verts, faces, mat, face_mats=face_mats)
        if bevel_cm > 0:
            self._soften(obj, min(bevel_cm, min(size_cm) * 0.24), segments=segments)
        else:
            self._bake_smooth(obj, 42.0)
        long_ax = max(range(3), key=lambda i: size_cm[i])
        self._uv_box(obj, long_axis=long_ax)
        return obj

    def plank(self, label, center_cm, size_cm, mat='Oak', rot_deg=(0, 0, 0), wear=0.14, endgrain=True):
        axis = max(range(3), key=lambda i: size_cm[i])
        cross = [i for i in range(3) if i != axis]
        a, b = size_cm[cross[0]] * 0.5, size_cm[cross[1]] * 0.5
        r = min(0.42, a * 0.17, b * 0.25)
        ring = [(-a + r, -b), (a - r, -b), (a, -b + r), (a, b - r),
                (a - r, b), (-a + r, b), (-a, b - r), (-a, -b + r)]
        rings = max(3, min(12, int(size_cm[axis] / 16.0)))
        rot_m = Euler((math.radians(rot_deg[0]), math.radians(rot_deg[1]), math.radians(rot_deg[2])), 'XYZ').to_matrix()
        c = Vector(center_cm)
        verts = []
        for j in range(rings + 1):
            t = j / rings
            drift = math.sin(t * math.pi) * self.rng.uniform(-wear, wear)
            for aa, bb in ring:
                p = [0.0, 0.0, 0.0]
                p[axis] = (t - 0.5) * size_cm[axis]
                p[cross[0]] = aa + drift + math.sin(t * math.pi) * self.rng.uniform(-wear * 0.35, wear * 0.35)
                p[cross[1]] = bb + math.sin(t * math.pi) * self.rng.uniform(-wear * 0.35, wear * 0.35)
                verts.append(tuple(c + rot_m @ Vector(p)))
        faces = []
        face_mats = []
        for j in range(rings):
            for k in range(8):
                faces.append((j * 8 + k, j * 8 + (k + 1) % 8, (j + 1) * 8 + (k + 1) % 8, (j + 1) * 8 + k))
                face_mats.append(mat)
        cap_mat = 'Endgrain' if (endgrain and mat in ('Oak', 'OiledOak', 'DarkWood', 'Sawn')) else mat
        faces.append(tuple(reversed(range(8))))
        face_mats.append(cap_mat)
        faces.append(tuple(rings * 8 + k for k in range(8)))
        face_mats.append(cap_mat)
        obj = self._new_mesh_obj(label, verts, faces, mat, face_mats=face_mats)
        self._bake_smooth(obj, 42.0)
        self._uv_box(obj, long_axis=axis)
        return obj

    def beam(self, label, a_cm, b_cm, w_cm, d_cm, mat='Oak', wear=0.09, endgrain=True):
        va, vb = Vector(a_cm), Vector(b_cm)
        delta = vb - va
        length = delta.length
        if length < 1e-4:
            return None
        axis = delta.normalized()
        ref = Vector((0, 0, 1)) if abs(axis.z) < 0.94 else Vector((1, 0, 0))
        side = ref.cross(axis).normalized()
        up = axis.cross(side).normalized()
        hw, hd = w_cm * 0.5, d_cm * 0.5
        r = min(0.35, hw * 0.22, hd * 0.22)
        sec = [(-hw + r, -hd), (hw - r, -hd), (hw, -hd + r), (hw, hd - r),
               (hw - r, hd), (-hw + r, hd), (-hw, hd - r), (-hw, -hd + r)]
        segs = max(2, min(8, int(length / 20.0)))
        verts = []
        for j in range(segs + 1):
            t = j / segs
            ctr = va.lerp(vb, t)
            bend = math.sin(t * math.pi) * self.rng.uniform(-wear, wear)
            for s, u in sec:
                p = ctr + (s + bend) * side + u * up
                verts.append((p.x, p.y, p.z))
        faces = []
        face_mats = []
        n = len(sec)
        for j in range(segs):
            for k in range(n):
                faces.append((j * n + k, j * n + (k + 1) % n, (j + 1) * n + (k + 1) % n, (j + 1) * n + k))
                face_mats.append(mat)
        cap_mat = 'Endgrain' if (endgrain and mat in ('Oak', 'OiledOak', 'DarkWood', 'Sawn')) else mat
        faces.append(tuple(reversed(range(n))))
        face_mats.append(cap_mat)
        faces.append(tuple(segs * n + k for k in range(n)))
        face_mats.append(cap_mat)
        obj = self._new_mesh_obj(label, verts, faces, mat, face_mats=face_mats)
        self._bake_smooth(obj, 42.0)
        long_ax = max(range(3), key=lambda i: abs(delta[i]))
        self._uv_box(obj, long_axis=long_ax)
        return obj

    def lathe(self, label, center_cm, profile_rz, mat='OiledOak', axis='Z', rot_deg=(0, 0, 0),
              sides=24, cap_mat=None):
        rot_m = Euler((math.radians(rot_deg[0]), math.radians(rot_deg[1]), math.radians(rot_deg[2])), 'XYZ').to_matrix()
        if axis == 'X':
            ax_m = Matrix(((0, 0, 1), (0, 1, 0), (-1, 0, 0)))
        elif axis == 'Y':
            ax_m = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))
        else:
            ax_m = Matrix.Identity(3)
        full_m = rot_m @ ax_m
        c = Vector(center_cm)
        verts = []
        ring_indices = []
        for z_val, rad in profile_rz:
            if rad <= 1e-4:
                idx = len(verts)
                p = c + full_m @ Vector((0.0, 0.0, z_val))
                verts.append((p.x, p.y, p.z))
                ring_indices.append([idx])
            else:
                ring = []
                for k in range(sides):
                    ang = k * math.tau / sides
                    p = c + full_m @ Vector((rad * math.cos(ang), rad * math.sin(ang), z_val))
                    ring.append(len(verts))
                    verts.append((p.x, p.y, p.z))
                ring_indices.append(ring)
        faces = []
        face_mats = []
        for j in range(len(ring_indices) - 1):
            r0, r1 = ring_indices[j], ring_indices[j + 1]
            if len(r0) == 1 and len(r1) == sides:
                for k in range(sides):
                    faces.append((r0[0], r1[(k + 1) % sides], r1[k]))
                    face_mats.append(mat)
            elif len(r0) == sides and len(r1) == 1:
                for k in range(sides):
                    faces.append((r0[k], r0[(k + 1) % sides], r1[0]))
                    face_mats.append(mat)
            elif len(r0) == sides and len(r1) == sides:
                for k in range(sides):
                    k2 = (k + 1) % sides
                    faces.append((r0[k], r0[k2], r1[k2], r1[k]))
                    face_mats.append(mat)
        cm_mat = cap_mat or ('Endgrain' if mat in ('Oak', 'OiledOak', 'DarkWood', 'Sawn') else mat)
        if len(ring_indices[0]) == sides:
            faces.append(tuple(reversed(ring_indices[0])))
            face_mats.append(cm_mat)
        if len(ring_indices[-1]) == sides:
            faces.append(tuple(ring_indices[-1]))
            face_mats.append(cm_mat)
        obj = self._new_mesh_obj(label, verts, faces, mat, face_mats=face_mats)
        self._bake_smooth(obj, 52.0)
        data = obj.data
        uv_layer = data.uv_layers.new(name='UV0')
        uv_layer.active_render = True
        data.uv_layers.active = uv_layer
        mats = list(data.materials)
        for poly in data.polygons:
            mname = mats[poly.material_index].name
            sc = UV_SCALES_M.get(mname, 1.0)
            for li in poly.loop_indices:
                v_bl = data.vertices[data.loops[li].vertex_index].co
                ax = max(range(3), key=lambda i: abs(poly.normal[i]))
                axes = [i for i in range(3) if i != ax]
                uv_layer.data[li].uv = (v_bl[axes[0]] / sc + 0.5, v_bl[axes[1]] / sc + 0.5)
        return obj

    def sweep_section(self, label, points_cm, section_2d, mat='Iron', cyclic=False,
                      up_hint=None, cap_mat=None, uv_scale_override=None, twist_per_cm=0.0):
        """Sweep a closed 2D section along a 3D polyline (with optional helical twist for 3-strand braided rope!)."""
        pts = [Vector(p) for p in points_cm]
        if len(pts) < 2:
            return None
        n_pts = len(pts)
        tangents = []
        for i in range(n_pts):
            if cyclic:
                t_vec = pts[(i + 1) % n_pts] - pts[(i - 1) % n_pts]
            elif i == 0:
                t_vec = pts[1] - pts[0]
            elif i == n_pts - 1:
                t_vec = pts[-1] - pts[-2]
            else:
                t_vec = pts[i + 1] - pts[i - 1]
            tangents.append(t_vec.normalized() if t_vec.length > 1e-6 else Vector((1, 0, 0)))

        t0 = tangents[0]
        if up_hint is not None:
            hint = Vector(up_hint).normalized()
            if abs(t0.dot(hint)) > 0.96:
                hint = Vector((1, 0, 0)) if abs(t0.x) < 0.8 else Vector((0, 1, 0))
            side = hint.cross(t0).normalized()
            up = t0.cross(side).normalized()
        else:
            ref = Vector((0, 0, 1)) if abs(t0.z) < 0.92 else Vector((1, 0, 0))
            side = ref.cross(t0).normalized()
            up = t0.cross(side).normalized()

        frames = [(side, up)]
        for i in range(1, n_pts):
            prev_t = tangents[i - 1]
            cur_t = tangents[i]
            dot_v = max(-1.0, min(1.0, prev_t.dot(cur_t)))
            if dot_v < 0.99999:
                rot_axis = prev_t.cross(cur_t)
                if rot_axis.length > 1e-6:
                    rot_q = Matrix.Rotation(math.acos(dot_v), 3, rot_axis.normalized())
                    side = (rot_q @ side).normalized()
                    up = cur_t.cross(side).normalized()
                    side = up.cross(cur_t).normalized()
            frames.append((side, up))

        if cyclic and n_pts >= 3:
            last_side, _ = frames[-1]
            first_side, first_up = frames[0]
            proj = last_side - last_side.dot(tangents[0]) * tangents[0]
            if proj.length > 1e-5:
                proj.normalize()
                twist = math.atan2(proj.dot(first_up), proj.dot(first_side))
                for i in range(n_pts):
                    ang = -twist * (i / n_pts)
                    ca, sa = math.cos(ang), math.sin(ang)
                    s0, u0 = frames[i]
                    frames[i] = (ca * s0 + sa * u0, -sa * s0 + ca * u0)

        per_point = isinstance(section_2d[0][0], (tuple, list))
        m_sec = len(section_2d[0]) if per_point else len(section_2d)

        arc_len = [0.0]
        for i in range(1, n_pts):
            arc_len.append(arc_len[-1] + (pts[i] - pts[i - 1]).length)
        total_len = arc_len[-1] + ((pts[0] - pts[-1]).length if cyclic else 0.0)

        # Snap cyclic twist to exact integer multiples of 2*pi/3 so braided rope meets seamlessly!
        actual_twist = twist_per_cm
        if cyclic and abs(twist_per_cm) > 1e-6 and total_len > 1e-4:
            turns = max(1, round(twist_per_cm * total_len / (math.tau / 3.0)))
            actual_twist = turns * (math.tau / 3.0) / total_len

        verts = []
        for i in range(n_pts):
            s_vec, u_vec = frames[i]
            if abs(actual_twist) > 1e-6:
                ang = arc_len[i] * actual_twist
                ca, sa = math.cos(ang), math.sin(ang)
                s_vec, u_vec = ca * s_vec + sa * u_vec, -sa * s_vec + ca * u_vec
            sec = section_2d[i] if per_point else section_2d
            for sv, tv in sec:
                p = pts[i] + sv * s_vec + tv * u_vec
                verts.append((p.x, p.y, p.z))

        faces = []
        face_mats = []
        seg_count = n_pts if cyclic else n_pts - 1
        for i in range(seg_count):
            i2 = (i + 1) % n_pts
            for k in range(m_sec):
                k2 = (k + 1) % m_sec
                faces.append((i * m_sec + k, i * m_sec + k2, i2 * m_sec + k2, i2 * m_sec + k))
                face_mats.append(mat)
        if not cyclic:
            cmat = cap_mat or mat
            faces.append(tuple(reversed(range(m_sec))))
            face_mats.append(cmat)
            faces.append(tuple((n_pts - 1) * m_sec + k for k in range(m_sec)))
            face_mats.append(cmat)

        obj = self._new_mesh_obj(label, verts, faces, mat, face_mats=face_mats)
        self._bake_smooth(obj, 56.0)

        sc_cm = (uv_scale_override or UV_SCALES_M.get(mat, 0.5)) * 100.0
        data = obj.data
        uv_layer = data.uv_layers.new(name='UV0')
        uv_layer.active_render = True
        data.uv_layers.active = uv_layer
        base_sec = section_2d[0] if per_point else section_2d
        perim = [0.0]
        for k in range(m_sec):
            a2, b2 = base_sec[k], base_sec[(k + 1) % m_sec]
            perim.append(perim[-1] + math.hypot(b2[0] - a2[0], b2[1] - a2[1]))
        f_idx = 0
        for i in range(seg_count):
            u0 = arc_len[i] / sc_cm
            u1 = (arc_len[i + 1] if i + 1 < n_pts else total_len) / sc_cm
            for k in range(m_sec):
                v0 = perim[k] / sc_cm
                v1 = perim[k + 1] / sc_cm
                poly = data.polygons[f_idx]
                v_map = {
                    i * m_sec + k: (u0, v0),
                    i * m_sec + (k + 1) % m_sec: (u0, v1),
                    ((i + 1) % n_pts) * m_sec + (k + 1) % m_sec: (u1, v1),
                    ((i + 1) % n_pts) * m_sec + k: (u1, v0),
                }
                for li in poly.loop_indices:
                    uv_layer.data[li].uv = v_map.get(data.loops[li].vertex_index, (u0, v0))
                f_idx += 1
        if not cyclic:
            for poly in data.polygons[f_idx:]:
                for li in poly.loop_indices:
                    co = data.vertices[data.loops[li].vertex_index].co
                    uv_layer.data[li].uv = (co.x / (sc_cm / 100.0) + 0.5, co.z / (sc_cm / 100.0) + 0.5)
        return obj

    def tube(self, label, points_cm, radius_cm, mat='Iron', sides=10, cyclic=False, up_hint=None):
        if isinstance(radius_cm, (list, tuple)):
            secs = [[(r * math.cos(k * math.tau / sides), r * math.sin(k * math.tau / sides))
                     for k in range(sides)] for r in radius_cm]
        else:
            secs = [(radius_cm * math.cos(k * math.tau / sides), radius_cm * math.sin(k * math.tau / sides))
                    for k in range(sides)]
        return self.sweep_section(label, points_cm, secs, mat=mat, cyclic=cyclic, up_hint=up_hint)

    def rope_braid(self, label, points_cm, radius_cm=1.35, mat='Rope', cyclic=False,
                   pitch_cm=7.5, sample_step_cm=2.2):
        """True 3-strand helical twisted hemp rope geometry! Resamples curve finely so spiral silhouette is crisp."""
        raw = [Vector(p) for p in points_cm]
        if len(raw) < 2:
            return None
        # Uniform arc-length resampling so helical twist never aliases on long straight segments
        pts = [raw[0]]
        n_segs = len(raw) if cyclic else len(raw) - 1
        for i in range(n_segs):
            a, b = raw[i], raw[(i + 1) % len(raw)]
            dist = (b - a).length
            steps = max(1, int(math.ceil(dist / sample_step_cm)))
            for s in range(1, steps + 1):
                if cyclic and i == n_segs - 1 and s == steps:
                    continue
                pts.append(a.lerp(b, s / steps))
        # 12-point 3-lobed trefoil cross-section (3 distinct rounded hemp strands!)
        m_pts = 12
        sec = []
        for k in range(m_pts):
            ang = k * math.tau / m_pts
            lobe = 0.84 + 0.24 * math.cos(3.0 * ang)
            sec.append((radius_cm * lobe * math.cos(ang), radius_cm * lobe * math.sin(ang)))
        twist = math.tau / max(2.5, pitch_cm)
        return self.sweep_section(label, pts, sec, mat=mat, cyclic=cyclic,
                                  uv_scale_override=0.22, twist_per_cm=twist)

    def strap(self, label, points_cm, width_cm, thick_cm, mat='LeatherDark', cyclic=False, up_hint=None):
        hw, ht = width_cm * 0.5, thick_cm * 0.5
        c = min(hw * 0.25, ht * 0.35, 0.22)
        sec = [(-hw + c, -ht), (hw - c, -ht), (hw, -ht + c), (hw, ht - c),
               (hw - c, ht), (-hw + c, ht), (-hw, ht - c), (-hw, -ht + c)]
        return self.sweep_section(label, points_cm, sec, mat=mat, cyclic=cyclic, up_hint=up_hint)

    def ring_torus(self, label, center_cm, major_r, minor_r, mat='Steel', axis='Y',
                   rot_deg=(0, 0, 0), major_segs=24, minor_segs=10):
        rot_m = Euler((math.radians(rot_deg[0]), math.radians(rot_deg[1]), math.radians(rot_deg[2])), 'XYZ').to_matrix()
        ctr = Vector(center_cm)
        pts = []
        for i in range(major_segs):
            a = i * math.tau / major_segs
            if axis == 'Y':
                p = Vector((major_r * math.cos(a), 0.0, major_r * math.sin(a)))
            elif axis == 'X':
                p = Vector((0.0, major_r * math.cos(a), major_r * math.sin(a)))
            else:
                p = Vector((major_r * math.cos(a), major_r * math.sin(a), 0.0))
            pts.append(ctr + rot_m @ p)
        return self.tube(label, pts, minor_r, mat=mat, sides=minor_segs, cyclic=True)

    def thick_grid(self, label, grid_pts, thick_cm, mat='LeatherMain', rim_mat=None, uv_scale_cm=None):
        nu = len(grid_pts)
        nv = len(grid_pts[0])
        pts = [[Vector(grid_pts[i][j]) for j in range(nv)] for i in range(nu)]
        norms = [[Vector((0, 0, 1)) for _ in range(nv)] for _ in range(nu)]
        for i in range(nu):
            for j in range(nv):
                du = pts[min(nu - 1, i + 1)][j] - pts[max(0, i - 1)][j]
                dv = pts[i][min(nv - 1, j + 1)] - pts[i][max(0, j - 1)]
                n = du.cross(dv)
                norms[i][j] = n.normalized() if n.length > 1e-6 else Vector((0, 0, 1))
        half_t = thick_cm * 0.5
        verts = []
        for i in range(nu):
            for j in range(nv):
                p = pts[i][j] + norms[i][j] * half_t
                verts.append((p.x, p.y, p.z))
        off = nu * nv
        for i in range(nu):
            for j in range(nv):
                p = pts[i][j] - norms[i][j] * half_t
                verts.append((p.x, p.y, p.z))

        def idx(i, j):
            return i * nv + j

        faces = []
        face_mats = []
        for i in range(nu - 1):
            for j in range(nv - 1):
                faces.append((idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)))
                face_mats.append(mat)
                faces.append((off + idx(i, j), off + idx(i, j + 1), off + idx(i + 1, j + 1), off + idx(i + 1, j)))
                face_mats.append(mat)
        rmat = rim_mat or mat
        for j in range(nv - 1):
            faces.append((idx(0, j), idx(0, j + 1), off + idx(0, j + 1), off + idx(0, j)))
            face_mats.append(rmat)
            faces.append((idx(nu - 1, j + 1), idx(nu - 1, j), off + idx(nu - 1, j), off + idx(nu - 1, j + 1)))
            face_mats.append(rmat)
        for i in range(nu - 1):
            faces.append((idx(i + 1, 0), idx(i, 0), off + idx(i, 0), off + idx(i + 1, 0)))
            face_mats.append(rmat)
            faces.append((idx(i, nv - 1), idx(i + 1, nv - 1), off + idx(i + 1, nv - 1), off + idx(i, nv - 1)))
            face_mats.append(rmat)

        obj = self._new_mesh_obj(label, verts, faces, mat, face_mats=face_mats)
        self._bake_smooth(obj, 62.0)
        sc_cm = uv_scale_cm or (UV_SCALES_M.get(mat, 0.5) * 100.0)
        u_acc = [[0.0] * nv for _ in range(nu)]
        v_acc = [[0.0] * nv for _ in range(nu)]
        for i in range(1, nu):
            for j in range(nv):
                u_acc[i][j] = u_acc[i - 1][j] + (pts[i][j] - pts[i - 1][j]).length
        for i in range(nu):
            for j in range(1, nv):
                v_acc[i][j] = v_acc[i][j - 1] + (pts[i][j] - pts[i][j - 1]).length
        # For woven Blanket, normalize V to [0, 1] across the drape so woven border stripes align symmetrically on both flanks!
        norm_v = (mat == 'Blanket')
        data = obj.data
        uv_layer = data.uv_layers.new(name='UV0')
        uv_layer.active_render = True
        data.uv_layers.active = uv_layer
        for poly in data.polygons:
            for li in poly.loop_indices:
                vi = data.loops[li].vertex_index
                local_vi = vi - off if vi >= off else vi
                ii, jj = divmod(local_vi, nv)
                u_coord = u_acc[ii][jj] / sc_cm
                v_coord = (jj / max(1, nv - 1)) if norm_v else (v_acc[ii][jj] / sc_cm)
                uv_layer.data[li].uv = (u_coord, v_coord)
        return obj

    def peg(self, center_cm, axis='Y', radius_cm=0.65, length_cm=1.8):
        return self.lathe('OakPeg', center_cm, [(-length_cm * 0.5, radius_cm), (length_cm * 0.5, radius_cm * 0.92)],
                          mat='Endgrain', axis=axis, sides=8, cap_mat='Endgrain')

    def bolt(self, center_cm, axis='Y', radius_cm=0.72, height_cm=0.65, mat='Iron'):
        return self.lathe('ForgedBolt', center_cm,
                          [(0.0, radius_cm), (height_cm * 0.65, radius_cm * 0.85), (height_cm, radius_cm * 0.25)],
                          mat=mat, axis=axis, sides=6, cap_mat=mat)

    def rivet(self, center_cm, axis='Z', radius_cm=0.55, height_cm=0.42, mat='Brass'):
        return self.lathe('Rivet', center_cm,
                          [(0.0, radius_cm), (height_cm * 0.55, radius_cm * 0.88),
                           (height_cm * 0.92, radius_cm * 0.45), (height_cm, 0.0)],
                          mat=mat, axis=axis, sides=10, cap_mat=mat)

    def finish(self, out_dir: Path, lod_ratios=(1.0, 0.50, 0.22)):
        assert self.parts, f'No geometry parts built for {self.name}'
        bpy.ops.object.select_all(action='DESELECT')
        for p in self.parts:
            p.select_set(True)
        bpy.context.view_layer.objects.active = self.parts[0]
        if len(self.parts) > 1:
            bpy.ops.object.join()
        obj = self.parts[0]
        obj.name = self.name
        obj.data.name = self.name
        obj.data.transform(obj.matrix_world)
        obj.matrix_world = Matrix.Identity(4)

        for layer in list(obj.data.uv_layers):
            if layer.name != 'UV0':
                obj.data.uv_layers.remove(layer)
        uv0 = obj.data.uv_layers.get('UV0') or obj.data.uv_layers.new(name='UV0')
        uv0.active_render = True
        obj.data.uv_layers.active = uv0

        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.dissolve_degenerate(bm, dist=5e-5, edges=list(bm.edges))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(obj.data)
        bm.free()

        slot_names = [m.name for m in obj.data.materials]
        face_names = [slot_names[p.material_index] for p in obj.data.polygons]
        used_order = list(dict.fromkeys(face_names))
        obj.data.materials.clear()
        for mname in used_order:
            obj.data.materials.append(self.mats[mname])
        new_idx = {mname: i for i, mname in enumerate(used_order)}
        for poly, mname in zip(obj.data.polygons, face_names):
            poly.material_index = new_idx[mname]

        # Bake 3D curvature / cavity grime / ground mud / edge wear into vertex color 'Col'!
        bake_weathering_vcol(obj, ground_mud_height_cm=self.ground_mud_cm, is_wall_mounted=self.is_wall_mounted)

        tri = obj.modifiers.new('Triangulate', 'TRIANGULATE')
        tri.keep_custom_normals = True
        _apply_mod(obj, tri)
        obj.data.calc_loop_triangles()

        uv_data = obj.data.uv_layers['UV0'].data
        mats_final = list(obj.data.materials)
        fixed_uvs = 0
        for poly in obj.data.polygons:
            loops = list(poly.loop_indices)
            if len(loops) != 3:
                continue
            a, b, c = [uv_data[k].uv for k in loops]
            if abs((b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)) >= 1e-10:
                continue
            mname = mats_final[poly.material_index].name
            sc = UV_SCALES_M.get(mname, 0.5)
            ax = max(range(3), key=lambda i: abs(poly.normal[i]))
            axes = [i for i in range(3) if i != ax]
            for k in loops:
                co = obj.data.vertices[obj.data.loops[k].vertex_index].co
                uv_data[k].uv = (co[axes[0]] / sc + 0.5, co[axes[1]] / sc + 0.5)
            fixed_uvs += 1

        zero_area = [p.index for p in obj.data.polygons if p.area < 1e-11]
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        open_edges = sum(1 for e in bm.edges if len(e.link_faces) == 1)
        non_manifold = sum(1 for e in bm.edges if len(e.link_faces) > 2)
        bm.free()
        slot_counts = {m.name: 0 for m in obj.data.materials}
        for p in obj.data.polygons:
            slot_counts[obj.data.materials[p.material_index].name] += 1
        assert not zero_area, f'{self.name}: {len(zero_area)} zero-area faces'
        assert open_edges == 0, f'{self.name}: {open_edges} open boundary edges!'
        assert all(cnt > 0 for cnt in slot_counts.values()), f'{self.name}: empty material slot {slot_counts}'

        out_dir.mkdir(parents=True, exist_ok=True)
        lods = []
        for lod_i, ratio in enumerate(lod_ratios):
            target = obj if lod_i == 0 else obj.copy()
            if lod_i > 0:
                target.data = obj.data.copy()
                bpy.context.collection.objects.link(target)
                target.name = f'{self.name}_LOD{lod_i}'
                dec = target.modifiers.new('LODDecimate', 'DECIMATE')
                dec.ratio = ratio
                dec.delimit = {'MATERIAL', 'UV'}
                _apply_mod(target, dec)
                t_uv = target.data.uv_layers['UV0'].data
                t_mats = list(target.data.materials)
                for poly in target.data.polygons:
                    loops = list(poly.loop_indices)
                    if len(loops) != 3:
                        continue
                    a, b, c = [t_uv[k].uv for k in loops]
                    if abs((b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)) >= 1e-10:
                        continue
                    sc = UV_SCALES_M.get(t_mats[poly.material_index].name, 0.5)
                    ax = max(range(3), key=lambda i: abs(poly.normal[i]))
                    axes = [i for i in range(3) if i != ax]
                    for k in loops:
                        co = target.data.vertices[target.data.loops[k].vertex_index].co
                        t_uv[k].uv = (co[axes[0]] / sc + 0.5, co[axes[1]] / sc + 0.5)
            _active(target)
            target.data.calc_loop_triangles()
            fbx_path = out_dir / (f'{self.name}_LOD{lod_i}.fbx' if lod_i else f'{self.name}.fbx')
            bpy.ops.export_scene.fbx(
                filepath=str(fbx_path),
                use_selection=True,
                object_types={'MESH'},
                axis_forward='-Y',
                axis_up='Z',
                mesh_smooth_type='FACE',
                use_tspace=True,
                colors_type='LINEAR',
                bake_anim=False,
                add_leaf_bones=False,
            )
            lods.append(dict(
                level=lod_i,
                triangles=len(target.data.loop_triangles),
                file=str(fbx_path),
            ))
            if lod_i > 0:
                bpy.data.objects.remove(target, do_unlink=True)

        pts_ue = [(vv.co.x * 100.0, -vv.co.y * 100.0, vv.co.z * 100.0) for vv in obj.data.vertices]
        bmin = [round(min(p[i] for p in pts_ue), 2) for i in range(3)]
        bmax = [round(max(p[i] for p in pts_ue), 2) for i in range(3)]
        bsize = [round(bmax[i] - bmin[i], 2) for i in range(3)]

        self.parts = []
        return dict(
            name=self.name,
            lods=lods,
            materials=list(slot_counts.keys()),
            slot_polys=slot_counts,
            bounds_min_cm=bmin,
            bounds_max_cm=bmax,
            size_cm=bsize,
            open_edges=open_edges,
            non_manifold_edges=non_manifold,
            zero_area_faces=len(zero_area),
            repaired_uv_tris=fixed_uvs,
            vertex_color_layer='Col',
            colliders=self.colliders,
        )
