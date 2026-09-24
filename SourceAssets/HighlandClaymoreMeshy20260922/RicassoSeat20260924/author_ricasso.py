"""Replace the Highland blade-guard neck with one shared short ricasso.

Keeps the blade above 6.2 cm and every guard wing. The tang seats 3 mm
into the guard. New faces get their own normals after smooth is enabled.
"""
import json
import math
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils import Vector

P = Path(__file__).resolve().parent
OUT = P / "Export"
OUT.mkdir(exist_ok=True)
MODULAR = P.parent / "Integration" / "HighlandClaymore_Modular_Editable.blend"
BROAD = P.parent / "BroadbladeThicknessV2_20260922" / "Highland_Broadblade_ThickV2_Editable.blend"
CLOVEN = P.parent / "ClovenGuard20260922" / "Highland_ClovenGuard_Editable.blend"
FREEZE = 0.062
TANG_BOTTOM = 0.003
TANG_TOP = 0.020
STEP_TOP = 0.026
TANG_X = 0.0115
TANG_Y = 0.0052
COLLAR_Z0 = 0.001
COLLAR_Z1 = 0.016
COLLAR_X = 0.0172
COLLAR_Y = 0.0092
HOLE_X = 0.0104
HOLE_Y = 0.0043

def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)

def loops_of(bm):
    graph = {}
    for edge in bm.edges:
        if not edge.is_boundary:
            continue
        a, b = edge.verts
        graph.setdefault(a, []).append(b)
        graph.setdefault(b, []).append(a)
    unused = set(graph)
    found = []
    while unused:
        start = min(unused, key=lambda v: (v.co.z, v.co.x, v.co.y))
        current = start
        previous = None
        loop = []
        for _ in range(len(graph) + 2):
            loop.append(current)
            unused.discard(current)
            nxt = [v for v in graph[current] if v != previous and v not in loop]
            if not nxt:
                break
            previous, current = current, nxt[0]
            if current == start:
                break
        if len(loop) >= 8:
            found.append(loop)
    return found

def ellipse(z, hx, hy, n=48):
    return [Vector((math.cos(i / n * math.tau) * hx, math.sin(i / n * math.tau) * hy, z)) for i in range(n)]

def resample(loop, n=48):
    pts = [v.co.copy() for v in loop]
    center = sum(pts, Vector()) / len(pts)
    pts.sort(key=lambda p: math.atan2(p.y - center.y, p.x - center.x))
    # Roll so index 0 sits on +X, matching ellipse().
    shift = min(range(len(pts)), key=lambda i: abs(math.atan2(pts[i].y - center.y, pts[i].x - center.x)))
    pts = pts[shift:] + pts[:shift]
    out = []
    for i in range(n):
        t = i / n * len(pts)
        a = pts[int(t) % len(pts)]
        b = pts[(int(t) + 1) % len(pts)]
        out.append(a.lerp(b, t - int(t)))
    return out

def bridge(bm, lower, upper):
    n = len(lower)
    faces = []
    for i in range(n):
        a, b = lower[i], lower[(i + 1) % n]
        c, d = upper[(i + 1) % n], upper[i]
        face = bm.faces.new((a, b, c, d))
        face.smooth = True
        faces.append(face)
    return faces

def capture_surface_uvs(bm, uv_layer):
    if not uv_layer:
        return None
    points = []
    coords = []
    for face in bm.faces:
        for loop in face.loops:
            points.append(tuple(loop.vert.co))
            coords.append((loop[uv_layer].uv.x, loop[uv_layer].uv.y))
    return np.array(points, dtype=np.float64), np.array(coords, dtype=np.float64)

def apply_surface_uvs(faces, uv_layer, donor):
    if not uv_layer or donor is None:
        return
    points, coords = donor
    for face in faces:
        face.material_index = 0
        for loop in face.loops:
            delta = points - np.array(loop.vert.co, dtype=np.float64)
            index = int(np.argmin(np.einsum("ij,ij->i", delta, delta)))
            loop[uv_layer].uv = (float(coords[index, 0]), float(coords[index, 1]))

def capture_normals(mesh):
    found = {}
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            co = mesh.vertices[mesh.loops[li].vertex_index].co
            normal = mesh.corner_normals[li].vector
            if normal.length <= 1e-8:
                continue
            found[(round(co.x, 5), round(co.y, 5), round(co.z, 5))] = normal.copy()
    return found

def harden(mesh, captured, hard_z):
    for face in mesh.polygons:
        face.use_smooth = True
    mesh.update()
    normals = []
    for face in mesh.polygons:
        face_normal = face.normal if face.normal.length > 1e-8 else Vector((0, 0, 1))
        for li in face.loop_indices:
            co = mesh.vertices[mesh.loops[li].vertex_index].co
            key = (round(co.x, 5), round(co.y, 5), round(co.z, 5))
            kept = captured.get(key)
            use = kept if kept is not None else face_normal
            normals.append(tuple(use.normalized()))
    mesh.normals_split_custom_set(normals)
    angles = []
    by_vert = {}
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            vi = mesh.loops[li].vertex_index
            by_vert.setdefault(vi, []).append(mesh.corner_normals[li].vector)
    for vi, group in by_vert.items():
        if abs(mesh.vertices[vi].co.z - hard_z) > 0.0015 or len(group) < 2:
            continue
        for a in group:
            for b in group:
                if a.length <= 1e-8 or b.length <= 1e-8:
                    continue
                angles.append(math.degrees(a.angle(b)))
    return max(angles) if angles else 0.0

def add_blade_seat(obj):
    mesh = obj.data
    captured = capture_normals(mesh)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    uv_layer = bm.loops.layers.uv.active
    donor = capture_surface_uvs(bm, uv_layer)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, FREEZE), plane_no=(0, 0, 1), clear_inner=True)
    boundary = max(loops_of(bm), key=len)
    ordered = sorted(boundary, key=lambda v: math.atan2(v.co.y, v.co.x))
    def ring(z, hx, hy):
        made = []
        for vert in ordered:
            angle = math.atan2(vert.co.y, vert.co.x)
            made.append(bm.verts.new((math.cos(angle) * hx, math.sin(angle) * hy, z)))
        return made
    lip = [bm.verts.new((vert.co.x * 0.97, vert.co.y * 0.97, 0.034)) for vert in ordered]
    tang_top = ring(TANG_TOP, TANG_X, TANG_Y)
    tang_bottom = ring(TANG_BOTTOM, TANG_X * 0.92, TANG_Y * 0.92)
    made = []
    made.extend(bridge(bm, lip, ordered))
    made.extend(bridge(bm, tang_top, lip))
    made.extend(bridge(bm, tang_bottom, tang_top))
    cap_center = bm.verts.new((0, 0, TANG_BOTTOM))
    for i in range(len(tang_bottom)):
        face = bm.faces.new((cap_center, tang_bottom[(i + 1) % len(tang_bottom)], tang_bottom[i]))
        face.smooth = True
        made.append(face)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    apply_surface_uvs(made, uv_layer, donor)
    bm.to_mesh(mesh)
    bm.free()
    return harden(mesh, captured, TANG_TOP)

def hide_guard_throat(obj):
    """Thin only the central seat to the blade shoulder. Wings stay put."""
    mesh = obj.data
    before = [(v.co.x, v.co.y, v.co.z) for v in mesh.vertices if abs(v.co.x) > 0.06]
    co = np.array([tuple(v.co) for v in mesh.vertices], dtype=np.float64)
    center = np.abs(co[:, 0]) < 0.03
    half = float(np.max(np.abs(co[center, 1]))) if np.any(center) else 0.02
    target = 0.005
    scale = target / max(half, 1e-4)
    weight = np.clip((0.055 - np.abs(co[:, 0])) / 0.025, 0, 1)
    weight = weight * weight * (3 - 2 * weight)
    sy = 1 + (scale - 1) * weight
    gem = (np.abs(co[:, 0]) < 0.016) & (co[:, 2] > -0.022) & (co[:, 2] < 0.008)
    grown = gem.copy()
    for poly in mesh.polygons:
        ids = list(poly.vertices)
        if any(gem[i] for i in ids):
            for i in ids:
                if abs(co[i, 0]) < 0.030 and -0.028 < co[i, 2] < 0.012:
                    grown[i] = True
    gem = grown
    sy[gem] = 1
    sign = np.sign(co[:, 1])
    sign[sign == 0] = 1
    co[:, 1] *= sy
    cz, rx, rz = -0.0064, 0.013, 0.012
    radial = np.sqrt((co[:, 0] / rx) ** 2 + ((co[:, 2] - cz) / rz) ** 2)
    t = np.clip(radial, 0, 1)
    # Entire stone stands proud of the 5 mm steel: rim +3 mm, center +9 mm.
    co[gem, 1] = sign[gem] * (0.008 + 0.006 * (1 - t[gem] ** 2))
    loops = np.array([loop.vertex_index for loop in mesh.loops], dtype=np.int32)
    normals = np.array([tuple(n.vector) for n in mesh.corner_normals], dtype=np.float64)
    normals[:, 1] /= np.maximum(sy[loops], 1e-4)
    dhdx = -0.012 * co[loops, 0] / (rx * rx)
    dhdz = -0.012 * (co[loops, 2] - cz) / (rz * rz)
    on_gem = gem[loops]
    normals[on_gem, 0] = -dhdx[on_gem]
    normals[on_gem, 1] = sign[loops][on_gem]
    normals[on_gem, 2] = -dhdz[on_gem]
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-10)
    mesh.vertices.foreach_set("co", co.astype(np.float32).ravel())
    for face in mesh.polygons:
        face.use_smooth = True
    mesh.update()
    mesh.normals_split_custom_set([tuple(n) for n in normals])
    gem_y = co[gem, 1]
    if len(gem_y) == 0 or float(np.max(np.abs(gem_y))) < 0.012:
        raise RuntimeError("Gem thickness was not preserved on " + obj.name)
    after = [(v.co.x, v.co.y, v.co.z) for v in mesh.vertices if abs(v.co.x) > 0.06]
    if before != after:
        raise RuntimeError("Guard wing vertices moved: " + obj.name)

def add_collar(obj):
    mesh = obj.data
    captured = capture_normals(mesh)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    uv_layer = bm.loops.layers.uv.active
    donor = capture_surface_uvs(bm, uv_layer)
    outer_top = [bm.verts.new(p) for p in ellipse(COLLAR_Z1, COLLAR_X, COLLAR_Y)]
    outer_bot = [bm.verts.new(p) for p in ellipse(COLLAR_Z0, COLLAR_X * 0.96, COLLAR_Y * 0.96)]
    inner_top = [bm.verts.new(p) for p in ellipse(COLLAR_Z1, HOLE_X, HOLE_Y)]
    inner_bot = [bm.verts.new(p) for p in ellipse(COLLAR_Z0, HOLE_X * 0.96, HOLE_Y * 0.96)]
    made = []
    made.extend(bridge(bm, outer_bot, outer_top))
    made.extend(bridge(bm, inner_top, inner_bot))
    made.extend(bridge(bm, outer_top, inner_top))
    made.extend(bridge(bm, inner_bot, outer_bot))
    bmesh.ops.recalc_face_normals(bm, faces=made)
    apply_surface_uvs(made, uv_layer, donor)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return harden(mesh, captured, COLLAR_Z1)

def thickness_gain(name):
    if "Broadblade" in name:
        return 2.0
    if "heavy" in name:
        return 1.35
    if "feather" in name:
        return 0.85
    return 1.0

def squeeze_existing_blade(obj):
    """Normalize spine thickness along the whole blade. Width and UVs stay."""
    mesh = obj.data
    co = np.array([tuple(v.co) for v in mesh.vertices], dtype=np.float64)
    gain = thickness_gain(obj.name)
    tip_band = co[co[:, 2] > 0.84]
    tip_half = float(np.max(np.abs(tip_band[:, 1]))) if len(tip_band) else 0.0015
    stations = np.linspace(float(co[:, 2].min()), float(co[:, 2].max()), 40)
    half_y = []
    for station in stations:
        band = co[np.abs(co[:, 2] - station) <= 0.012]
        spine = band[np.abs(band[:, 0]) < 0.008] if len(band) else band
        use = spine if len(spine) else band
        half_y.append(float(np.max(np.abs(use[:, 1]))) if len(use) else np.nan)
    known = np.isfinite(half_y)
    half_y = np.interp(stations, stations[known], np.array(half_y)[known])
    shoulder = 0.004 * gain
    mid = max(0.002, 0.00275 * gain)
    tip = min(tip_half, mid)

    def target(z):
        extra = 0.01
        if z <= 0.03:
            return shoulder + extra
        if z <= 0.10:
            t = (z - 0.03) / 0.07
            t = t * t * (3 - 2 * t)
            return shoulder + (mid - shoulder) * t + extra
        if z <= 0.62:
            return mid + extra
        t = np.clip((z - 0.62) / 0.24, 0, 1)
        t = t * t * (3 - 2 * t)
        return mid + (tip - mid) * t + extra

    current = np.interp(co[:, 2], stations, half_y)
    wanted = np.array([target(z) for z in co[:, 2]])
    sy = wanted / np.maximum(current, 1e-4)
    co[:, 1] *= sy
    loops = np.array([loop.vertex_index for loop in mesh.loops], dtype=np.int32)
    normals = np.array([tuple(n.vector) for n in mesh.corner_normals], dtype=np.float64)
    normals[:, 1] /= np.maximum(sy[loops], 1e-4)
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-10)
    mesh.vertices.foreach_set("co", co.astype(np.float32).ravel())
    for face in mesh.polygons:
        face.use_smooth = True
    mesh.update()
    mesh.normals_split_custom_set([tuple(n) for n in normals])
    return obj

def cut_blade_above_gem(obj):
    """Drop the blade root that passes through the gem and cap the flat seat."""
    mesh = obj.data
    captured = capture_normals(mesh)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    uv = bm.loops.layers.uv.active
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, 0.007), plane_no=(0, 0, 1), clear_inner=True)
    boundary = max(loops_of(bm), key=len)
    known = {}
    if uv:
        for vert in boundary:
            for loop in vert.link_loops:
                known[vert] = loop[uv].uv.copy()
                break
    center = bm.verts.new(sum((vert.co for vert in boundary), Vector()) / len(boundary))
    center.co.z = 0.007
    made = []
    for a, b in zip(boundary, boundary[1:] + boundary[:1]):
        face = bm.faces.new((center, b, a))
        face.smooth = True
        made.append(face)
        if uv and a in known and b in known:
            face.loops[1][uv].uv = known[b]
            face.loops[2][uv].uv = known[a]
            face.loops[0][uv].uv = (known[a] + known[b]) * 0.5
    bmesh.ops.recalc_face_normals(bm, faces=made)
    bm.to_mesh(mesh)
    bm.free()
    harden(mesh, captured, 0.007)
    return obj

def export_obj(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    kept = obj.location.copy()
    obj.location = Vector()
    bpy.ops.export_scene.fbx(
        filepath=str(OUT / (obj.name + ".fbx")),
        use_selection=True,
        object_types={"MESH"},
        axis_forward="-Y",
        axis_up="Z",
        add_leaf_bones=False,
        bake_anim=False,
        mesh_smooth_type="FACE",
        use_tspace=True,
    )
    obj.location = kept

def section(obj, z0, z1):
    points = np.array([tuple(obj.matrix_world @ v.co) for v in obj.data.vertices], dtype=np.float64)
    band = points[(points[:, 2] >= z0) & (points[:, 2] <= z1)]
    band = band[(np.abs(band[:, 0]) < 0.08) & (np.abs(band[:, 1]) < 0.05)]
    if len(band) == 0:
        return None
    return {
        "x_cm": round(float(np.max(np.abs(band[:, 0])) * 100), 2),
        "y_cm": round(float(np.max(np.abs(band[:, 1])) * 100), 2),
        "z_cm": [round(float(band[:, 2].min()) * 100, 2), round(float(band[:, 2].max()) * 100, 2)],
        "n": int(len(band)),
    }

def run_blend(path, blades, guards):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    report = {"source": str(path), "parts": []}
    for name in blades:
        obj = bpy.data.objects[name]
        squeeze_existing_blade(obj)
        seat = section(obj, 0.003, 0.020)
        body = section(obj, 0.075, 0.085)
        if seat is None or seat["x_cm"] < 0.8 or not (1.20 <= seat["y_cm"] <= 2.10):
            raise RuntimeError(name + " thickness out of range " + str(seat))
        if body and "Broadblade" not in name and body["y_cm"] > 1.60:
            raise RuntimeError(name + " mid blade still thick " + str(body))
        report["parts"].append({"mesh": name, "method": "deform-original-surface", "tang": seat, "body_8cm": body, "faces": len(obj.data.polygons)})
        export_obj(obj)
    for name in guards:
        obj = bpy.data.objects[name]
        hide_guard_throat(obj)
        report["parts"].append({"mesh": name, "method": "deform-original-surface", "faces": len(obj.data.polygons)})
        export_obj(obj)
    return report

bpy.context.preferences.filepaths.save_version = 0
reports = []
reports.append(run_blend(
    MODULAR,
    ["SM_Highland_Blade_factory", "SM_Highland_Blade_extended_edge", "SM_Highland_Blade_heavy_spine", "SM_Highland_Blade_feather_edge"],
    ["SM_Highland_Guard_factory", "SM_Highland_Guard_bastion_guard", "SM_Highland_Guard_riposte_guard", "SM_Highland_Guard_light_guard"],
))
stem = bpy.data.filepath
bpy.ops.wm.save_as_mainfile(filepath=str(P / "HighlandClaymore_Ricasso_Editable.blend"))
if BROAD.exists():
    reports.append(run_blend(BROAD, ["SM_Highland_Blade_Broadblade_ThickV2"], []))
    bpy.ops.wm.save_as_mainfile(filepath=str(P / "Broadblade_Ricasso_Editable.blend"))
if CLOVEN.exists():
    reports.append(run_blend(CLOVEN, [], ["SM_Highland_Guard_Cloven"]))
    bpy.ops.wm.save_as_mainfile(filepath=str(P / "Cloven_Ricasso_Editable.blend"))
receipt = {"freeze_m": FREEZE, "tang_bottom_m": TANG_BOTTOM, "tang_top_m": TANG_TOP, "seat_overlap_mm": round((COLLAR_Z1 - TANG_BOTTOM) * 1000, 1), "reports": reports, "note": "Original blend left untouched: " + stem}
(P / "author_receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print("RICASSO_AUTHOR_COMPLETE")
