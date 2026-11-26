"""Make the wall shells collide on their triangles, not a solid hull.

Evidence: S_joinery / S_doors / S_glazing already read back as
CTF_USE_COMPLEX_AS_SIMPLE (3) and are walkable, while S_walls / S_floors /
S_plate still read CTF_USE_SIMPLE_AND_COMPLEX (1) with one convex hull.
That hull is a solid slab across the whole mesh, so the door openings are
filled in and the player cannot enter the rooms.

Setting COMPLEX_AS_SIMPLE everywhere makes the engine trace the actual
triangles, which preserves the openings.
"""
import json

import unreal

BASE = "/Game/Props/CyberpunkApartment20261020/CyberpunkApartment"
REPORT = r"D:\FPS3D\FPSGAME\Saved\_complex_walls.json"

NAMES = ["S_walls", "S_floors", "S_plate", "S_ceiling", "S_finish",
         "S_trim", "S_facade", "S_balcony", "S_balcony_glass"]

out = {"ok": [], "failed": [], "readback": []}

for name in NAMES:
    path = "%s/StaticMeshes/%s" % (BASE, name)
    try:
        mesh = unreal.EditorAssetLibrary.load_asset(path + "." + name)
        body = mesh.get_editor_property("body_setup")
        body.set_editor_property(
            "collision_trace_flag",
            unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)

        ok = unreal.EditorLoadingAndSavingUtils.save_packages(
            [unreal.load_package(path)], True)
        (out["ok"] if ok else out["failed"]).append(name)
    except Exception as exc:  # noqa: BLE001
        out["failed"].append("%s: %s: %s" % (name, type(exc).__name__, exc))

# read back from a fresh load of the saved packages
for name in NAMES:
    path = "%s/StaticMeshes/%s.%s" % (BASE, name, name)
    try:
        m = unreal.EditorAssetLibrary.load_asset(path)
        b = m.get_editor_property("body_setup")
        out["readback"].append({"name": name,
                                "flag": str(b.get_editor_property("collision_trace_flag"))})
    except Exception as exc:  # noqa: BLE001
        out["readback"].append({"name": name, "error": str(exc)})

with open(REPORT, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)
unreal.log("COMPLEX_WALLS_WRITTEN")