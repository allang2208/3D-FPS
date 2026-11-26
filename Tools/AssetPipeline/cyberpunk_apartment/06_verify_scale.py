"""Verify imported scale and report bounds in UE units (cm)."""
import json

import unreal

BASE = "/Game/Props/CyberpunkApartment20261020/CyberpunkApartment/StaticMeshes"
REPORT = r"D:\FPS3D\FPSGAME\Saved\_scale_report.json"

out = {"samples": [], "union": None, "errors": []}
try:
    us = unreal.EditorAssetLibrary
    paths = us.list_assets(BASE, recursive=False, include_folder=False)
    lo = [1e12, 1e12, 1e12]
    hi = [-1e12, -1e12, -1e12]
    for p in sorted(paths):
        m = us.load_asset(p)
        if not isinstance(m, unreal.StaticMesh):
            continue
        b = m.get_bounding_box()
        bmin, bmax = b.min, b.max
        origin = unreal.Vector((bmin.x + bmax.x) * 0.5,
                               (bmin.y + bmax.y) * 0.5,
                               (bmin.z + bmax.z) * 0.5)
        ext = unreal.Vector((bmax.x - bmin.x) * 0.5,
                            (bmax.y - bmin.y) * 0.5,
                            (bmax.z - bmin.z) * 0.5)
        short = p.split("/")[-1].split(".")[0]
        out["samples"].append({
            "name": short,
            "center": [round(origin.x, 1), round(origin.y, 1), round(origin.z, 1)],
            "extent": [round(ext.x, 1), round(ext.y, 1), round(ext.z, 1)],
        })
        for i, v in enumerate((origin.x - ext.x, origin.y - ext.y, origin.z - ext.z)):
            lo[i] = min(lo[i], v)
        for i, v in enumerate((origin.x + ext.x, origin.y + ext.y, origin.z + ext.z)):
            hi[i] = max(hi[i], v)
    out["union"] = {"min": [round(v, 1) for v in lo], "max": [round(v, 1) for v in hi],
                    "size": [round(hi[i] - lo[i], 1) for i in range(3)]}
except Exception as exc:  # noqa: BLE001
    out["errors"].append("%s: %s" % (type(exc).__name__, exc))

with open(REPORT, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)
unreal.log("SCALE_REPORT_WRITTEN")