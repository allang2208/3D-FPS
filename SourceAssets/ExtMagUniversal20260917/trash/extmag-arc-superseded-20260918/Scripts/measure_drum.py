"""Measure the three accepted drum assets: tower axis/section, drum disc."""
import bpy, math, os, json
from mathutils import Matrix, Vector
import numpy as np
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SA = r"D:\FPS3D\FPSGAME\SourceAssets"
DRUMS = {
    "M4": os.path.join(SA, r"WeaponAttachmentFinish20260913\FBX\M4\drum.fbx"),
    "AKM": os.path.join(SA, r"WeaponAttachmentFinish20260913\FBX\AKM\drum.fbx"),
    "QBZ": os.path.join(SA, r"QBZ191Attachments20260913\SM_QBZ191_drum.fbx"),
}
report = {}
for gun, path in DRUMS.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
    mo = [o for o in bpy.context.scene.objects if o.type == "MESH"][-1]
    mw = mo.matrix_world
    arr = np.array([[ (mw @ v.co).x, (mw @ v.co).y, (mw @ v.co).z ] for v in mo.data.vertices])
    mn, mx = arr.min(axis=0), arr.max(axis=0)
    # slice along the longest axis (the tower axis is roughly the asset's longest)
    extents = mx - mn
    long_ax = int(np.argmax(extents))
    u_ax = sorted(set(range(3)) - {long_ax})
    # profile: per 1cm bin along long axis, extents on the other two axes
    prof = []
    a0, a1 = mn[long_ax], mx[long_ax]
    nb = int((a1 - a0) / 0.01) + 1
    for i in range(nb):
        t0 = a0 + i * 0.01; t1 = t0 + 0.01
        sel = arr[(arr[:, long_ax] >= t0) & (arr[:, long_ax] < t1)]
        if len(sel) < 5:
            prof.append({"t": round(float(t0), 3), "w": 0.0, "d": 0.0, "n": 0,
                         "cu": 0.0, "cv": 0.0})
            continue
        u = sel[:, u_ax[0]]; v = sel[:, u_ax[1]]
        prof.append({"t": round(float(t0), 3),
                     "w": round(float(u.max() - u.min()), 4),
                     "d": round(float(v.max() - v.min()), 4),
                     "cu": round(float((u.max() + u.min()) / 2), 4),
                     "cv": round(float((v.max() + v.min()) / 2), 4),
                     "n": len(sel)})
    report[gun] = {
        "asset_min": [round(float(v), 4) for v in mn],
        "asset_max": [round(float(v), 4) for v in mx],
        "long_axis": long_ax, "profile": prof,
        "n_verts": len(arr),
    }
with open(os.path.join(ROOT, "Reference", "drum_measure.json"), "w") as f:
    json.dump(report, f, indent=1)
print("DRUM_MEASURE_DONE")
