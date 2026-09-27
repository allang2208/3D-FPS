"""Open the current detail blend read-only, measure slots, render three orthos."""
from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

import bpy
import bmesh

HERE = Path(__file__).resolve().parent
BLEND = HERE / "RiserDetail_Editable.blend"
PREVIEW = HERE / "InspectPreview"
OUT = HERE / "structure_inspect_blender.json"
NOCKS = ((-0.2146, -0.00935, 0.6411), (-0.2146, -0.00935, -0.6404))
SLOT_NAMES = {0: "Body", 1: "Limb", 2: "Inlay"}


def hard_stats(mesh):
    angles = []
    hard = 0
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.normal_update()
    for v in bm.verts:
        ns = [f.normal.copy() for f in v.link_faces]
        mx = 0.0
        for i in range(len(ns)):
            for j in range(i + 1, len(ns)):
                d = max(-1.0, min(1.0, ns[i].dot(ns[j])))
                mx = max(mx, math.degrees(math.acos(d)))
        angles.append(mx)
        if mx > 25.0:
            hard += 1
    bm.free()
    angles.sort()
    return {
        "hard_verts_25": hard,
        "verts": len(angles),
        "p50": round(angles[len(angles) // 2], 2) if angles else 0,
        "p90": round(angles[int((len(angles) - 1) * 0.9)], 2) if angles else 0,
    }


def world_pts(obj):
    return [obj.matrix_world @ v.co for v in obj.data.vertices]


def slot_rows(obj):
    rows = defaultdict(lambda: {"tris": 0, "xs": [], "ys": [], "zs": []})
    mesh = obj.data
    for poly in mesh.polygons:
        row = rows[int(poly.material_index)]
        row["tris"] += 1
        for vi in poly.vertices:
            p = obj.matrix_world @ mesh.vertices[vi].co
            row["xs"].append(p.x * 100)
            row["ys"].append(p.y * 100)
            row["zs"].append(p.z * 100)
    out = {}
    for slot, row in sorted(rows.items()):
        out[SLOT_NAMES.get(slot, str(slot))] = {
            "index": slot,
            "tris": row["tris"],
            "bbox_cm": {
                "x": [round(min(row["xs"]), 3), round(max(row["xs"]), 3)],
                "y": [round(min(row["ys"]), 3), round(max(row["ys"]), 3)],
                "z": [round(min(row["zs"]), 3), round(max(row["zs"]), 3)],
                "size": [
                    round(max(row["xs"]) - min(row["xs"]), 3),
                    round(max(row["ys"]) - min(row["ys"]), 3),
                    round(max(row["zs"]) - min(row["zs"]), 3),
                ],
            },
        }
    return out


def bands(obj):
    pts = [(p.x * 100, p.y * 100, p.z * 100) for p in world_pts(obj)]
    out = []
    for lo, hi, name in (
        (-4, 4, "grip"),
        (8, 20, "fade_low"),
        (20, 45, "limb_mid"),
        (55, 62, "tip"),
        (62, 66, "nock"),
    ):
        sel = [p for p in pts if lo <= abs(p[2]) <= hi]
        if not sel:
            out.append({"name": name, "count": 0})
            continue
        xs, ys, zs = zip(*sel)
        out.append(
            {
                "name": name,
                "count": len(sel),
                "x_span_cm": round(max(xs) - min(xs), 3),
                "y_span_cm": round(max(ys) - min(ys), 3),
                "x_min": round(min(xs), 3),
            }
        )
    return out


def nock_gap(obj):
    pts = list(world_pts(obj))
    out = []
    for target in NOCKS:
        best = 1e9
        nearest = None
        for p in pts:
            d = math.dist((p.x, p.y, p.z), target)
            if d < best:
                best = d
                nearest = [round(p.x * 100, 3), round(p.y * 100, 3), round(p.z * 100, 3)]
        out.append(
            {
                "key_cm": [round(c * 100, 3) for c in target],
                "nearest_cm": nearest,
                "gap_cm": round(best * 100, 3),
            }
        )
    return out


def render_views(obj):
    PREVIEW.mkdir(exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 1400
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = True
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "MATERIAL"
    shading.show_specular_highlight = False
    cam = bpy.data.cameras.new("InspectCam")
    cam.type = "ORTHO"
    cam_obj = bpy.data.objects.new("InspectCam", cam)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj
    xs, ys, zs = zip(*[(p.x, p.y, p.z) for p in world_pts(obj)])
    cx = (min(xs) + max(xs)) * 0.5
    cy = (min(ys) + max(ys)) * 0.5
    cz = (min(zs) + max(zs)) * 0.5
    span = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
    cam.ortho_scale = span * 1.15
    views = {
        "side": ((cx + span, cy, cz), (0.0, 0.0, 0.0)),
        "front": ((cx, cy - span, cz), (90.0, 0.0, 0.0)),
        "top": ((cx, cy, cz + span), (0.0, 0.0, 0.0)),
    }
    # side = looking -X so the recurve profile is visible
    files = {}
    for name, (loc, rot) in (
        ("side_profile", ((cx + span, cy, cz), (math.radians(90), 0.0, math.radians(90)))),
        ("string_face", ((cx, cy - span, cz), (math.radians(90), 0.0, 0.0))),
        ("grip_top", ((cx, cy, cz + span), (0.0, 0.0, 0.0))),
    ):
        cam_obj.location = loc
        cam_obj.rotation_euler = rot
        path = PREVIEW / ("riser_" + name + ".png")
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        files[name] = str(path)
    return files


def main():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    obj = next(o for o in bpy.data.objects if o.type == "MESH")
    receipt = {
        "blend": str(BLEND),
        "object": obj.name,
        "tris": len(obj.data.polygons),
        "verts": len(obj.data.vertices),
        "hard": hard_stats(obj.data),
        "slots": slot_rows(obj),
        "thickness_bands_cm": bands(obj),
        "nock_keys": nock_gap(obj),
        "previews": render_views(obj),
    }
    OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print("RISER_BLEND_INSPECT", json.dumps({k: receipt[k] for k in ("tris", "verts", "slots", "nock_keys")}), flush=True)


if __name__ == "__main__":
    main()
