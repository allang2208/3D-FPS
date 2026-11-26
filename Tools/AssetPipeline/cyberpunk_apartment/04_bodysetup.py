"""Set complex-as-simple on the BodySetup so traces hit the render mesh.

`collision_trace_flag` lives on UBodySetup (accessible via the mesh body
setup), not on UStaticMesh. Actor-level BlockAll is already applied; this
finishes the trace behaviour so the camera and player capsule collide with
the actual geometry rather than an empty hull.
"""
import json

import unreal

BASE = "/Game/Props/CyberpunkApartment20261020/CyberpunkApartment"
REPORT = r"D:\FPS3D\FPSGAME\Saved\_bodysetup_report.json"

NAMES = ["S_plate", "S_walls", "S_floors", "S_ceiling", "S_joinery", "S_finish",
         "S_doors", "S_facade", "S_balcony", "S_glazing", "S_balcony_glass",
         "S_trim", "FOY_room", "COR_room", "KIT_run", "KIT_dining", "B2_room",
         "B3_room", "MST_room", "BA1_room", "BA2_room", "UTL_room",
         "LIV_furniture", "LIV_rug", "DET_practicals"]

out = {"ok": [], "failed": [], "errors": []}
eal = unreal.EditorAssetLibrary

for name in NAMES:
    path = "%s/StaticMeshes/%s.%s" % (BASE, name, name)
    try:
        mesh = eal.load_asset(path)
        if mesh is None:
            out["failed"].append(name + " (load)")
            continue
        body = mesh.get_editor_property("body_setup")
        if body is None:
            out["failed"].append(name + " (no body setup)")
            continue
        body.set_editor_property("collision_trace_flag",
                                 unreal.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
        eal.save_loaded_asset(mesh)
        out["ok"].append(name)
    except Exception as exc:  # noqa: BLE001
        out["failed"].append("%s: %s: %s" % (name, type(exc).__name__, exc))

with open(REPORT, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)
unreal.log("BODYSETUP_REPORT_WRITTEN")