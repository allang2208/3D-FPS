"""Round 2: corrected socket matrix, AKM region extraction, upper-segment
axis fit, and per-gun accepted-drum neck data.

Blender world = real-size metres = the metre-valued WPN bone frame numbers.
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
import numpy as np


def import_file(path):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    return [o for o in bpy.context.scene.objects if o not in before]


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def bone_world(arm_obj, name):
    arm = arm_obj.data
    arm.pose_position = "REST"
    bpy.context.view_layer.update()
    return arm_obj.matrix_world @ arm.bones[name].matrix_local


def mag_verts(gun, objs, socket):
    meshes = [o for o in objs if o.type == "MESH"]
    if gun == "M4":
        mo = next(o for o in meshes if o.name.startswith("M4_Magazine"))
        mw = mo.matrix_world
        return [mw @ v.co for v in mo.data.vertices], mo.name
    if gun == "QBZ":
        mo = next(o for o in meshes if o.name.startswith("QBZ191_Magazine"))
        mw = mo.matrix_world
        return [mw @ v.co for v in mo.data.vertices], mo.name
    # AKM: welded into the receiver shell. Take verts in a cylinder below the
    # socket along -Z (the AKM mag hangs nearly straight down), radius 9 cm,
    # down to 26 cm below the socket top.
    mo = next(o for o in meshes if o.name.startswith("AKM_"))
    mw = mo.matrix_world
    s = socket.translation
    pts = []
    for v in mo.data.vertices:
        p = mw @ v.co
        d = p - s
        if d.z < 0.005 and d.z > -0.26 and d.x * d.x + d.y * d.y < 0.0081:
            pts.append(p)
    return pts, mo.name + " region"


def fit_axis_upper(pts):
    """Fit insertion axis from slice centroids of the upper half (the part
    that must align with the well)."""
    arr = np.array([[p.x, p.y, p.z] for p in pts])
    z = arr[:, 2]
    top = z.max()
    sel = arr[z > top - (top - z.min()) * 0.5]
    # slice along z, centroid per 1 cm bin, then least-squares direction.
    order = np.argsort(sel[:, 2])
    sel = sel[order]
    bins = []
    z0 = sel[0, 2]
    cur = [sel[0]]
    for row in sel[1:]:
        if row[2] - z0 > 0.01:
            bins.append(np.mean(cur, axis=0))
            cur = [row]
            z0 = row[2]
        else:
            cur.append(row)
    bins.append(np.mean(cur, axis=0))
    bins = np.array(bins)
    c = bins.mean(axis=0)
    u, s, vt = np.linalg.svd(bins - c)
    axis = Vector(vt[0])
    if axis.z < 0:
        axis = -axis
    return axis, Vector(c)


def cross(pts, axis, origin, t0, t1):
    sel = [p for p in pts if t0 <= (p - origin).dot(axis) < t1]
    if len(sel) < 4:
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
        "u_min": round(min(us), 4), "u_max": round(max(us), 4),
        "v_min": round(min(vs), 4), "v_max": round(max(vs), 4),
    }


report = {}
for gun, path in GUNS.items():
    clear()
    objs = import_file(path)
    arm = next(o for o in objs if o.type == "ARMATURE")
    sw = bone_world(arm, "WPN_SOCKET_Magazine")
    rw = bone_world(arm, "WPN_root")
    pts, src = mag_verts(gun, objs, sw)
    axis, c_up = fit_axis_upper(pts)
    st = sw.translation
    lo = min((p - st).dot(axis) for p in pts)
    hi = max((p - st).dot(axis) for p in pts)
    neck = cross(pts, axis, st, hi - 0.012, hi + 0.001)
    mid = cross(pts, axis, st, hi - 0.08, hi - 0.06)
    entry = {
        "socket_head": [round(v, 4) for v in st],
        "root_head": [round(v, 4) for v in rw.translation],
        "source": src, "n": len(pts),
        "top_extent_along_axis": round(hi, 4), "bottom_extent": round(lo, 4),
        "axis_world": [round(v, 4) for v in axis],
        "tilt_deg": round(math.degrees(math.acos(max(-1, min(1, axis.z)))), 2),
        "neck": neck, "mid": mid,
    }
    # how far below the socket origin does the mag extend, and where does the
    # mag's top sit relative to the socket origin along the axis
    report[gun] = entry

# accepted drum necks per gun: place drum with its runtime mount, take the top
# slice (the part inside the well) and record center/axis/cross-section.
for gun, dpath in DRUMS.items():
    clear()
    objs = import_file(dpath)
    mo = next(o for o in objs if o.type == "MESH")
    mw = mo.matrix_world
    raw = [mw @ v.co for v in mo.data.vertices]
    gobjs = import_file(GUNS[gun])
    arm = next(o for o in gobjs if o.type == "ARMATURE")
    sw = bone_world(arm, "WPN_SOCKET_Magazine")
    rw = bone_world(arm, "WPN_root")
    if gun == "AKM":
        placed = [sw @ v for v in raw]
    elif gun == "M4":
        placed = [rw @ v for v in raw]
    else:
        mag0_t = Vector((2.8564492822624743e-05, -0.08145000040531158, -0.07817225158214569))
        placed = [sw @ (v + mag0_t) for v in raw]
    zs = [p.z for p in placed]
    top = max(zs)
    neck_pts = [p for p in placed if p.z > top - 0.012]
    cx = sum(p.x for p in neck_pts) / len(neck_pts)
    cy = sum(p.y for p in neck_pts) / len(neck_pts)
    cz = top
    report.setdefault("drum_necks", {})[gun] = {
        "mount": "socket" if gun != "M4" else "root",
        "top_z": round(top, 4),
        "neck_center": [round(cx, 4), round(cy, 4), round(cz, 4)],
        "neck_in_socket": [round(v, 4) for v in (sw.inverted() @ Vector((cx, cy, cz)))] if gun != "M4"
        else [round(v, 4) for v in (rw.inverted() @ Vector((cx, cy, cz)))],
        "n_neck": len(neck_pts),
        "placed_bbox_min": [round(v, 4) for v in (min(p.x for p in placed), min(p.y for p in placed), min(p.z for p in placed))],
        "placed_bbox_max": [round(v, 4) for v in (max(p.x for p in placed), max(p.y for p in placed), max(p.z for p in placed))],
    }

out = os.path.join(REF, "measure2.json")
with open(out, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=1)
print("MEASURE2_DONE", out)
