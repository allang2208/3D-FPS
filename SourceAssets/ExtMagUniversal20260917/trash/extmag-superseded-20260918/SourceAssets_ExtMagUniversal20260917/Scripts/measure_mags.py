"""Measure the three rifles' factory magazines and validate against the
accepted drum placements.

For each gun (Blender world = real-size metres, matching the metre-valued
WPN bone frames used at runtime):
  - socket bone world matrix at REST,
  - factory magazine vertex cloud (named object, or nearest loose part for AKM),
  - insertion axis via PCA, neck (top) slice, cross-section extents per slice,
  - mount candidate: EXT frame -> socket frame transform.

Drums: verify that composing the runtime mounts in this frame math lands the
accepted drum geometry at the well (M4: root frame via mount; AKM: socket
identity; QBZ: compared to factory mag neck like build_models.py did).

Output: ../Reference/measure.json
Run: blender -b -P measure_mags.py
"""
import bpy
import json
import math
import os
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.normpath(os.path.join(HERE, "..", "Reference"))
SA = r"D:\FPS3D\FPSGAME\SourceAssets"

GUNS = {
    "M4": os.path.join(SA, r"M4HK416Replica20260910\SK_M4_FoldingSights_HK416.fbx"),
    "AKM": os.path.join(SA, r"AKMSoviet20260911\SK_AKM_MannyNative.fbx"),
    "QBZ": os.path.join(SA, r"QBZ191MagazineSeat20260913\SK_QBZ191_Manny.fbx"),
}
DRUMS = {
    "M4": os.path.join(SA, r"WeaponAttachmentFinish20260913\FBX\M4\drum.fbx"),
    "AKM": os.path.join(SA, r"WeaponAttachmentFinish20260913\FBX\AKM\drum.fbx"),
    "QBZ": os.path.join(SA, r"QBZ191Attachments20260913\SM_QBZ191_drum.fbx"),
}

try:
    import numpy as np
except ImportError:
    np = None


def import_file(path):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    return [o for o in bpy.context.scene.objects if o not in before]


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def socket_world(arm_obj):
    arm = arm_obj.data
    arm.pose_position = "REST"
    bpy.context.view_layer.update()
    bone = arm.bones["WPN_SOCKET_Magazine"]
    m = Matrix.Identity(4)
    chain = []
    b = bone
    while b:
        chain.append(b)
        b = b.parent
    for b in reversed(chain):
        m = m @ b.matrix_local
    return arm_obj.matrix_world @ m


def root_world(arm_obj):
    arm = arm_obj.data
    b = arm.bones["WPN_root"]
    return arm_obj.matrix_world @ b.matrix_local


def loose_parts(obj):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    seen = set()
    parts = []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack = [v]
        group = []
        seen.add(v.index)
        while stack:
            cur = stack.pop()
            group.append(cur)
            for e in cur.link_edges:
                o = e.other_vert(cur)
                if o.index not in seen:
                    seen.add(o.index)
                    stack.append(o)
        parts.append(group)
    out = []
    mw = obj.matrix_world
    for g in parts:
        pts = [mw @ v.co for v in g]
        out.append((len(g), pts))
    bm.free()
    return out


def pca_axes(pts):
    import numpy as np
    arr = np.array([[p.x, p.y, p.z] for p in pts])
    mean = arr.mean(axis=0)
    q = arr - mean
    cov = q.T @ q / len(arr)
    w, v = np.linalg.eigh(cov)
    order = np.argsort(w)[::-1]
    axes = [Vector(v[:, i]) for i in order]
    return Vector(mean), axes


def slice_extents(pts, axis, origin, t0, t1):
    """Extents of verts with t0 <= (p-origin).axis < t1, projected on the two
    perpendicular axes u,v."""
    sel = [p for p in pts if t0 <= (p - origin).dot(axis) < t1]
    if not sel:
        return None
    u = Vector((1, 0, 0))
    if abs(axis.dot(u)) > 0.9:
        u = Vector((0, 0, 1))
    v = axis.cross(u).normalized()
    u = v.cross(axis).normalized()
    us = [p.dot(u) for p in sel]
    vs = [p.dot(v) for p in sel]
    return {
        "n": len(sel),
        "u_min": min(us), "u_max": max(us),
        "v_min": min(vs), "v_max": max(vs),
        "u_center": (min(us) + max(us)) * 0.5,
        "v_center": (min(vs) + max(vs)) * 0.5,
        "u": [u.x, u.y, u.z], "v": [v.x, v.y, v.z],
    }


def analyze_mag(name, pts, socket):
    mean, axes = pca_axes(pts)
    axis = axes[0]
    # orient insertion axis "up" (toward receiver): +Z world has positive dot.
    if axis.z < 0:
        axis = -axis
    lo = min((p - mean).dot(axis) for p in pts)
    hi = max((p - mean).dot(axis) for p in pts)
    length = hi - lo
    # neck slice near the top.
    neck = slice_extents(pts, axis, mean, hi - 0.008, hi + 0.0001)
    # slope of insertion axis vs world up.
    tilt = math.degrees(math.acos(max(-1.0, min(1.0, axis.z))))
    lean_az = math.degrees(math.atan2(axis.y, axis.x))
    slices = {}
    for t in range(0, int(length / 0.02) + 1):
        t0 = hi - (t + 1) * 0.02
        s = slice_extents(pts, axis, mean, t0, t0 + 0.02)
        if s:
            slices[t] = {
                "width_u": round(s["u_max"] - s["u_min"], 4),
                "depth_v": round(s["v_max"] - s["v_min"], 4),
                "cu": round(s["u_center"], 4), "cv": round(s["v_center"], 4),
            }
    # neck top center in world.
    top_pts = [p for p in pts if (p - mean).dot(axis) > hi - 0.006]
    top_center = Vector((sum(p.x for p in top_pts) / len(top_pts),
                         sum(p.y for p in top_pts) / len(top_pts),
                         sum(p.z for p in top_pts) / len(top_pts)))
    rel = socket.inverted() @ top_center
    return {
        "n_verts": len(pts),
        "length_m": round(length, 4),
        "axis_world": [round(c, 4) for c in axis],
        "tilt_from_up_deg": round(tilt, 2),
        "lean_azimuth_deg": round(lean_az, 2),
        "neck_slice": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in neck.items()} if neck else None,
        "top_center_world": [round(c, 4) for c in top_center],
        "top_center_in_socket": [round(c, 4) for c in rel],
        "slices_every_2cm": slices,
    }


def bbox(pts):
    xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
    return {"min": [round(min(xs), 4), round(min(ys), 4), round(min(zs), 4)],
            "max": [round(max(xs), 4), round(max(ys), 4), round(max(zs), 4)]}


report = {}

for gun, path in GUNS.items():
    clear()
    objs = import_file(path)
    arm = next(o for o in objs if o.type == "ARMATURE")
    sw = socket_world(arm)
    rw = root_world(arm)
    entry = {
        "socket_world_head": [round(c, 4) for c in sw.translation],
        "root_world_head": [round(c, 4) for c in rw.translation],
    }
    meshes = [o for o in objs if o.type == "MESH"]
    mag_pts = None
    if gun == "M4":
        mo = next(o for o in meshes if o.name.startswith("M4_Magazine"))
        mw = mo.matrix_world
        mag_pts = [mw @ v.co for v in mo.data.vertices]
        entry["mag_source"] = mo.name
    elif gun == "QBZ":
        mo = next(o for o in meshes if o.name.startswith("QBZ191_Magazine"))
        mw = mo.matrix_world
        mag_pts = [mw @ v.co for v in mo.data.vertices]
        entry["mag_source"] = mo.name
    else:
        mo = next(o for o in meshes if o.name.startswith("AKM_"))
        best = None
        probe = sw.translation + Vector((0, 0, -0.05))
        for n, pts in loose_parts(mo):
            xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
            inside = (min(xs) <= probe.x <= max(xs) and min(ys) <= probe.y <= max(ys)
                      and min(zs) <= probe.z <= max(zs))
            center = Vector((sum(xs) / n, sum(ys) / n, sum(zs) / n))
            d = (center - probe).length
            if best is None or (inside and not best[0]) or (inside == best[0] and d < best[1]):
                best = (inside, d, n, pts, center)
        inside, d, n, mag_pts, center = best
        entry["mag_source"] = f"{mo.name} loose part n={n} inside={inside} dist={round(d,4)}"
    entry["mag_bbox"] = bbox(mag_pts)
    entry["mag"] = analyze_mag("mag", mag_pts, sw)
    report[gun] = entry

# Drum validation: where does each accepted drum sit under its runtime mount?
for gun, path in DRUMS.items():
    clear()
    objs = import_file(path)
    mo = next(o for o in objs if o.type == "MESH")
    mw = mo.matrix_world
    raw = [mw @ v.co for v in mo.data.vertices]
    # re-import the gun to get bones in a fresh scene together with the drum
    gobjs = import_file(GUNS[gun])
    arm = next(o for o in gobjs if o.type == "ARMATURE")
    swm = socket_world(arm)
    rwm = root_world(arm)
    entry = {"asset_bbox": bbox(raw)}
    if gun == "AKM":
        placed = [swm @ (Vector((v.x * 0.01, v.y * 0.01, v.z * 0.01))) for v in raw]
        entry["mount"] = "socket @ identity, scale .01"
    elif gun == "M4":
        placed = [rwm @ (Vector((v.x * 0.01, v.y * 0.01, v.z * 0.01))) for v in raw]
        entry["mount"] = "gun-root frame @ scale .01 (DrumMount math)"
    else:
        # QBZ drum was baked into the factory mag frame (mag0): attached at
        # socket identity. mag0 frame origin from geometry_inputs.json.
        mag0_t = Vector((2.8564492822624743e-05, -0.08145000040531158, -0.07817225158214569))
        placed = [swm @ (v + mag0_t) for v in raw]
        entry["mount"] = "socket @ mag0 offset (baked), no extra scale (already metre-scale asset)"
    entry["placed_bbox"] = bbox(placed)
    report.setdefault("drums", {})[gun] = entry

out = os.path.join(REF, "measure.json")
with open(out, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=1)
print("MEASURE_DONE", out)
