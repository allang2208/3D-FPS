"""Re-author the three extended magazines in each rifle's own weapon frame.

Why: the accepted large drum carries its mounting position in its own vertices
and is attached at the weapon mesh origin (`Identity.GetRelativeTransform(Bone)`
in M4DrumVisual.cpp). The 2026-09-18 magazine instead assumed the asset was
authored in the runtime WPN_SOCKET_Magazine frame and mounted it with an
identity seat. That skips the socket-to-well offset (measured 5.7-12.1 cm on
the three rifles) and the well tilt (7.1-22.5 deg), so no rifle seated
correctly. This script reproduces the drum's scheme: put the geometry where the
factory magazine sits, in the weapon frame, and let the drum's proven mount do
the rest.

Method: each mesh IS the factory magazine with everything more than 10 cm below
the throat moved down 6 cm, so the untouched upper part gives an exact
index-wise correspondence with the factory magazine's own vertices. A trimmed
Kabsch fit recovers the rigid transform from the authored coordinates back onto
the factory magazine (M4, QBZ). The AKM magazine is the shared PMAG, so it is
first fitted onto the M4 magazine's shape and then moved to the AKM magazine's
own throat height and measured well axis.

Outputs: FBX/SM_ExtMag_{M440,QBZ40,AKM40}_inframe.fbx + Reference/weapon_frame_fit.json
Run: blender -b -P rebuild_in_weapon_frame.py
"""
import bpy, bmesh, json, math, os
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
REF = os.path.join(ROOT, "Reference")
FBXDIR = os.path.join(ROOT, "FBX")
SA = r"D:\FPS3D\FPSGAME\SourceAssets"

SRC = {
    "M4": os.path.join(SA, r"M4HK416Replica20260910\SK_M4_FoldingSights_HK416.fbx"),
    "AKM": os.path.join(SA, r"AKMSoviet20260911\SK_AKM_MannyNative.fbx"),
    "QBZ": os.path.join(SA, r"QBZ191MagazineSeat20260913\SK_QBZ191_Manny.fbx"),
}
AUTHORED = {
    "M4": ("SM_ExtMag_M440.fbx", "SM_ExtMag_M440_inframe.fbx"),
    "AKM": ("SM_ExtMag_AKM40.fbx", "SM_ExtMag_AKM40_inframe.fbx"),
    "QBZ": ("SM_ExtMag_QBZ40.fbx", "SM_ExtMag_QBZ40_inframe.fbx"),
}
# Same box the previous round used to pull the welded AKM magazine out of the
# receiver shell (measure_seat_final.py).
AKM_MAG_BOX = ((0.02, 0.12), (0.14, 0.34), (-0.34, -0.07))


def world_verts(obj):
    mw = np.array(obj.matrix_world)
    co = np.array([v.co[:] for v in obj.data.vertices], dtype=float)
    return (mw[:3, :3] @ co.T).T + mw[:3, 3]


def loose_parts(obj):
    bm = bmesh.new(); bm.from_mesh(obj.data); bm.verts.ensure_lookup_table()
    seen, out = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, group = [v], []
        seen.add(v.index)
        while stack:
            cur = stack.pop(); group.append(cur.index)
            for e in cur.link_edges:
                o = e.other_vert(cur)
                if o.index not in seen:
                    seen.add(o.index); stack.append(o)
        out.append(group)
    bm.free()
    return [sorted(g) for g in out]


def kabsch(p, q, weights=None):
    """Rigid transform T with q ~= T(p)."""
    if weights is None:
        weights = np.ones(len(p))
    w = weights / weights.sum()
    pc = (p * w[:, None]).sum(0)
    qc = (q * w[:, None]).sum(0)
    h = ((p - pc) * w[:, None]).T @ (q - qc)
    u, s, vt = np.linalg.svd(h)
    d = np.sign(np.linalg.det(vt.T @ u.T))
    r = vt.T @ np.diag([1.0, 1.0, d]) @ u.T
    t = qc - r @ pc
    return r, t


def fit_ransac(p, q, iters=4000, thr=0.002, seed=7):
    """Index-wise RANSAC + refinement, resolved by the throat criterion.

    Only the top 10 cm is untouched geometry (measured: 52% of the vertices on
    both the M4 and the QBZ, residual 0.000 mm). The extended lower part is a
    rigid 6 cm shift, so it has to be rejected as an outlier instead of being
    averaged into the fit - a plain Kabsch lands between the two regions and
    reads ~29 mm, which is what the first attempt did.

    Both regions align exactly, so RANSAC alone can pick either: on the M4 the
    larger set is the wrong one, on the QBZ the smaller one is. The physical
    tie-break is the throat - the magazine's feed lips must sit at the factory
    magazine's top, and the added 6 cm must hang below the factory's floor
    plate. Whichever candidate pokes above the factory top is rejected."""
    rng = np.random.default_rng(seed)
    n = len(p)
    best = None
    for _ in range(iters):
        idx = rng.choice(n, 3, replace=False)
        r, t = kabsch(p[idx], q[idx])
        err = np.linalg.norm((r @ p.T).T + t - q, axis=1)
        count = int((err < thr).sum())
        if best is None or count > best[0]:
            best = (count, r, t)
    _, r, t = best
    for _ in range(3):
        err = np.linalg.norm((r @ p.T).T + t - q, axis=1)
        sel = err < thr
        r, t = kabsch(p[sel], q[sel])
    err = np.linalg.norm((r @ p.T).T + t - q, axis=1)
    sel = err < thr

    # The throat end is +Z on every one of these source rigs: the receiver sits
    # above the magazine and the magazine body hangs into -Z (M4 z -21.8..-4.2,
    # QBZ -23.8..-5.0, AKM -28.0..-8.9 cm). A PCA axis cannot be signed - its
    # mean projection is zero by construction - so the sign has to come from the
    # weapon frame, not from the cloud.
    up = np.array([0.0, 0.0, 1.0])
    top_q = float((q @ up).max())

    candidates = []
    for tag, mask in (("larger", sel), ("complement", ~sel)):
        if mask.sum() < 12:
            continue
        rr, tt = kabsch(p[mask], q[mask])
        fitted = (rr @ p.T).T + tt
        overshoot = float((fitted @ up).max()) - top_q
        e = np.linalg.norm(fitted - q, axis=1)
        candidates.append({
            "tag": tag, "r": rr, "t": tt, "inliers": int(mask.sum()),
            "overshoot_above_throat_mm": round(overshoot * 1000, 2),
            "rms_mm": round(float(e[mask].mean() * 1000), 3),
        })
    chosen = min(candidates, key=lambda c: c["overshoot_above_throat_mm"])
    report = {
        "total": int(n), "inliers": int(chosen["inliers"]),
        "inlier_share": round(chosen["inliers"] / float(n), 3),
        "rms_kept_mm": chosen["rms_mm"],
        "overshoot_above_throat_mm": chosen["overshoot_above_throat_mm"],
        "candidates": [{"tag": c["tag"], "inliers": c["inliers"],
                        "overshoot_above_throat_mm": c["overshoot_above_throat_mm"],
                        "rms_mm": c["rms_mm"]} for c in candidates],
    }
    return chosen["r"], chosen["t"], report


def import_fbx(path):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    return [o for o in bpy.context.scene.objects if o not in before]


def factory_magazine(gun, meshes):
    if gun == "M4":
        mag = next(o for o in meshes if o.name.startswith("M4_Magazine"))
        return mag, world_verts(mag)
    if gun == "QBZ":
        mag = next(o for o in meshes if o.name.startswith("QBZ191_Magazine"))
        return mag, world_verts(mag)
    body = next(o for o in meshes if o.name.startswith("AKM_"))
    mw = np.array(body.matrix_world)
    co = np.array([v.co[:] for v in body.data.vertices], dtype=float)
    pts = (mw[:3, :3] @ co.T).T + mw[:3, 3]
    (x0, x1), (y0, y1), (z0, z1) = AKM_MAG_BOX
    best = None
    for grp in loose_parts(body):
        if len(grp) < 100:
            continue
        sel = pts[grp]
        ov = (min(sel[:, 0].max(), x1) - max(sel[:, 0].min(), x0)) * \
             (min(sel[:, 1].max(), y1) - max(sel[:, 1].min(), y0)) * \
             (min(sel[:, 2].max(), z1) - max(sel[:, 2].min(), z0))
        if ov > 0 and (best is None or ov > best[0]):
            best = (ov, grp)
    _, grp = best
    me = bpy.data.meshes.new("AKM_MAG_FACTORY")
    bm = bmesh.new()
    verts = [bm.verts.new(pts[i]) for i in grp]
    remap = {vi: k for k, vi in enumerate(grp)}
    for poly in body.data.polygons:
        try:
            bm.faces.new([verts[remap[vi]] for vi in poly.vertices])
        except (ValueError, KeyError):
            pass
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new("AKM_MAG_FACTORY", me)
    bpy.context.scene.collection.objects.link(ob)
    return ob, pts[grp]


def install_frame(points):
    """Throat-top frame of a magazine: origin on the top slice centre,
    Z up along the magazine's own length axis, X across the body (thin axis)."""
    mean = points.mean(0)
    _, _, vt = np.linalg.svd(points - mean, full_matrices=False)
    axis_len = vt[0]
    # orient so the body hangs below: the throat end is the smaller cluster
    t = (points - mean) @ axis_len
    if abs(t.min()) < abs(t.max()):
        up = axis_len
    else:
        up = -axis_len
    t = (points - mean) @ up
    top = points[t > t.max() - 0.004]
    origin = top.mean(0)
    # thin axis = width; make it orthogonal to up
    ext = points.max(0) - points.min(0)
    width_guess = np.zeros(3); width_guess[int(np.argmin(ext))] = 1.0
    xax = width_guess - up * float(up @ width_guess)
    xax /= np.linalg.norm(xax)
    yax = np.cross(up, xax); yax /= np.linalg.norm(yax)
    return np.stack([xax, yax, up], axis=1), origin


def frame_matrix(rot, origin):
    m = np.eye(4)
    m[:3, :3] = rot
    m[:3, 3] = origin
    return m


report = {}

# --- M4 / QBZ: fit straight onto that rifle's own factory magazine -----------
for gun in ("M4", "QBZ"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    src_objs = import_fbx(SRC[gun])
    mag_ob, factory = factory_magazine(gun, [o for o in src_objs if o.type == "MESH"])

    bpy.ops.wm.read_factory_settings(use_empty=True)
    mag_objs = [o for o in import_fbx(os.path.join(FBXDIR, AUTHORED[gun][0])) if o.type == "MESH"]
    mo = mag_objs[-1]
    authored = np.array([v.co[:] for v in mo.data.vertices], dtype=float)
    if len(authored) != len(factory):
        raise RuntimeError("%s vertex count %d != factory %d" % (gun, len(authored), len(factory)))
    r, t, fit = fit_ransac(authored, factory)
    new = (r @ authored.T).T + t
    for v, p in zip(mo.data.vertices, new):
        v.co = (float(p[0]), float(p[1]), float(p[2]))
    mo.data.update()
    bpy.ops.object.select_all(action='DESELECT')
    mo.select_set(True); bpy.context.view_layer.objects.active = mo
    out = os.path.join(FBXDIR, AUTHORED[gun][1])
    bpy.ops.export_scene.fbx(filepath=out, use_selection=True, apply_unit_scale=True,
                             object_types={'MESH'}, mesh_smooth_type='FACE',
                             add_leaf_bones=False, path_mode='COPY')
    report[gun] = {"out": os.path.basename(out), "fit": fit,
                   "frame": "own factory magazine (index-wise Kabsch)",
                   "new_bounds_m": [round(float(v), 5) for v in new.min(0)] +
                                   [round(float(v), 5) for v in new.max(0)]}

# --- AKM: shared PMAG, fitted onto the M4 shape then moved to the AKM throat --
bpy.ops.wm.read_factory_settings(use_empty=True)
m4_objs = [o for o in import_fbx(SRC["M4"]) if o.type == "MESH"]
_, m4_factory = factory_magazine("M4", m4_objs)
m4_rot, m4_org = install_frame(m4_factory)
L_m4 = frame_matrix(m4_rot, m4_org)

bpy.ops.wm.read_factory_settings(use_empty=True)
akm_src = [o for o in import_fbx(SRC["AKM"]) if o.type == "MESH"]
_, akm_factory = factory_magazine("AKM", akm_src)

bpy.ops.wm.read_factory_settings(use_empty=True)
mo = [o for o in import_fbx(os.path.join(FBXDIR, AUTHORED["AKM"][0])) if o.type == "MESH"][-1]
authored = np.array([v.co[:] for v in mo.data.vertices], dtype=float)
if len(authored) != len(m4_factory):
    raise RuntimeError("AKM vertex count %d != M4 magazine %d" % (len(authored), len(m4_factory)))
r_m4, t_m4, fit_m4 = fit_ransac(authored, m4_factory)

# AKM throat frame: measured well axis (seat_final.json) + the welded
# magazine's own top slice, so the PMAG's feed lips sit at the same height.
seat = json.load(open(os.path.join(REF, "seat_final.json")))
up = np.array(seat["AKM"]["axis"], dtype=float); up /= np.linalg.norm(up)
t = (akm_factory - akm_factory.mean(0)) @ up
top = akm_factory[t > t.max() - 0.004]
org = top.mean(0)
x = np.array([1.0, 0.0, 0.0]) - up * float(up[0])
x /= np.linalg.norm(x)
y = np.cross(up, x); y /= np.linalg.norm(y)
L_akm = frame_matrix(np.stack([x, y, up], axis=1), org)

M = L_akm @ np.linalg.inv(L_m4) @ np.concatenate(
    [np.concatenate([r_m4, t_m4[:, None]], axis=1), [[0, 0, 0, 1]]], axis=0)
new = (M[:3, :3] @ authored.T).T + M[:3, 3]
for v, p in zip(mo.data.vertices, new):
    v.co = (float(p[0]), float(p[1]), float(p[2]))
mo.data.update()
bpy.ops.object.select_all(action='DESELECT')
mo.select_set(True); bpy.context.view_layer.objects.active = mo
out = os.path.join(FBXDIR, AUTHORED["AKM"][1])
bpy.ops.export_scene.fbx(filepath=out, use_selection=True, apply_unit_scale=True,
                         object_types={'MESH'}, mesh_smooth_type='FACE',
                         add_leaf_bones=False, path_mode='COPY')

err = np.linalg.norm((r_m4 @ authored.T).T + t_m4 - m4_factory, axis=1)
report["AKM"] = {
    "out": os.path.basename(out),
    "frame": "PMAG fitted to M4 magazine, then placed at the AKM magazine throat",
    "pmag_fit": fit_m4,
    "akm_up_axis": [round(float(v), 5) for v in up],
    "akm_throat_top_m": [round(float(v), 5) for v in org],
    "m4_throat_top_m": [round(float(v), 5) for v in m4_org],
    "m4_pmag_length_m": round(float(np.ptp((m4_factory - m4_factory.mean(0)) @ (L_m4[:3, 2]))), 5),
    "akm_factory_length_m": round(float(np.ptp((akm_factory - akm_factory.mean(0)) @ up)), 5),
    "new_bounds_m": [round(float(v), 5) for v in new.min(0)] + [round(float(v), 5) for v in new.max(0)],
}

with open(os.path.join(REF, "weapon_frame_fit.json"), "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=1)
print("WEAPON_FRAME_FIT " + json.dumps(report))
