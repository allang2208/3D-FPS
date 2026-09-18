"""Probe what the two duplicate-band cut planes actually cut through.

Read-only diagnosis for the round-6 seam fix: the ring-to-ring registration came
out 6.8 mm off, which means the two planes do not carry one matching loop each.
This prints, per plane, every closed loop of vertices (count, centroid, bbox,
radius) and the nearest-neighbour distance from the lower ring to the upper one.

Run: blender -b -P probe_ring_structure.py
"""
import bmesh
import bpy
import json
import os
import numpy as np
from mathutils import Vector

SA = r"D:\FPS3D\FPSGAME\SourceAssets"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
BAND_BOTTOM = 0.018
BAND_HEIGHT = {"M4": 0.0606, "QBZ": 0.05736}
JOBS = {
    "M4": dict(source=os.path.join(SA, "M4HK416Replica20260910",
                                   "SK_M4_FoldingSights_HK416.fbx"), match="magazine"),
    "QBZ": dict(source=os.path.join(SA, "PhantomRearGripIntegration20260913",
                                    "QBZ191", "SK_QBZ191_Manny.fbx"), match="magazine"),
}


def keep_magazine_slot(ob, match):
    index = next(i for i, m in enumerate(ob.data.materials)
                 if m and match in m.name.lower())
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    drop = [face for face in bm.faces if face.material_index != index]
    if drop:
        bmesh.ops.delete(bm, geom=drop, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def loops_in_ring(bm, centroid, axis, value, tol=1e-4):
    verts = {v for v in bm.verts if abs((v.co - centroid).dot(axis) - value) < tol}
    seen, groups = set(), []
    for start in verts:
        if start in seen:
            continue
        stack, group = [start], []
        seen.add(start)
        while stack:
            current = stack.pop()
            group.append(current)
            for edge in current.link_edges:
                other = edge.other_vert(current)
                if other in verts and other not in seen:
                    seen.add(other)
                    stack.append(other)
        groups.append(group)
    return groups


report = {}
for gun, cfg in JOBS.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=cfg["source"])
    magazine = None
    for ob in bpy.context.scene.objects:
        if ob.type == "MESH" and any(m and cfg["match"] in m.name.lower()
                                     for m in ob.data.materials):
            magazine = ob
            break
    keep_magazine_slot(magazine, cfg["match"])
    bpy.context.view_layer.objects.active = magazine
    magazine.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    mesh = magazine.data
    points = [magazine.matrix_world @ v.co for v in mesh.vertices]
    lo = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    hi = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    centroid = (lo + hi) * 0.5
    size = hi - lo
    axis = Vector((0.0, 0.0, 0.0))
    axis[int(np.argmax(size))] = 1.0
    band_bottom = lo[2] + BAND_BOTTOM if int(np.argmax(size)) == 2 else lo + axis * BAND_BOTTOM
    band_bottom = (lo + axis * BAND_BOTTOM)
    cut = band_bottom + axis * BAND_HEIGHT[gun]

    bm = bmesh.new()
    bm.from_mesh(mesh)
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    for plane in (band_bottom, cut):
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=centroid + axis * (plane - centroid).dot(axis),
                               plane_no=axis, clear_inner=False, clear_outer=False)
        geom = list(bm.verts) + list(bm.edges) + list(bm.faces)

    low_value = (band_bottom - centroid).dot(axis)
    high_value = (cut - centroid).dot(axis)
    planes = {"low": low_value, "high": high_value}
    # Cross-section size against height: a flared floor plate shows up as a step
    # in the width profile, and a band that starts inside the flare can never be
    # repeated (its ring is not the body's ring).
    profile = []
    for step in range(16):
        value = (band_bottom - centroid).dot(axis) + 0.005 * step
        slab = np.array([[p.x, p.y, p.z] for p in points
                         if abs((p - centroid).dot(axis) - value) < 0.0035])
        if len(slab) < 6:
            profile.append({"cm_above_floor": round(0.5 * step + 1.8, 2), "verts": int(len(slab))})
            continue
        local = slab - slab.mean(axis=0)
        _, _, vt = np.linalg.svd(local, full_matrices=False)
        u, v = local @ vt[1], local @ vt[2]
        profile.append({"cm_above_floor": round(0.5 * step + 1.8, 2),
                        "verts": int(len(slab)),
                        "width_cm": round(float(u.max() - u.min()) * 100, 2),
                        "depth_cm": round(float(v.max() - v.min()) * 100, 2)})
    data = {}
    raw = {}
    for name, value in planes.items():
        groups = loops_in_ring(bm, centroid, axis, value)
        entry = []
        for group in groups:
            co = np.array([[v.co.x, v.co.y, v.co.z] for v in group])
            span = co.max(axis=0) - co.min(axis=0)
            entry.append({"verts": len(group),
                          "centroid": [round(float(c), 5) for c in co.mean(axis=0)],
                          "span": [round(float(c), 5) for c in span],
                          "open": sum(1 for v in group
                                      for e in v.link_edges if len(e.link_faces) == 1) // 2})
        entry.sort(key=lambda item: -item["verts"])
        data[name] = entry
        raw[name] = np.array([[v.co.x, v.co.y, v.co.z] for v in
                              [vert for group in groups for vert in group]])
    bm.free()

    # nearest neighbour from every low-ring vertex to the high ring
    low, high = raw["low"], raw["high"]
    d = np.sqrt(((low[:, None, :] - high[None, :, :]) ** 2).sum(axis=2)).min(axis=1)
    data["nearest_low_to_high_mm"] = {
        "mean": round(float(d.mean()) * 1000, 3),
        "max": round(float(d.max()) * 1000, 3),
        "min": round(float(d.min()) * 1000, 3)}
    data["width_profile"] = profile
    report[gun] = data
    print("RINGPROBE " + gun + " " + json.dumps(data), flush=True)

with open(os.path.join(ROOT, "Reference", "ring_structure_probe.json"), "w",
          encoding="utf-8") as handle:
    json.dump(report, handle, indent=1, ensure_ascii=False)
