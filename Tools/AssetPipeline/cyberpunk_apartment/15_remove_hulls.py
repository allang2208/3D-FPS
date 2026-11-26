"""Delete the degenerate convex hulls from every architectural mesh.

All eight meshes still carry exactly one convex element - the hull the glTF
importer generated. For S_floors that hull is built from a zero-thickness
plane and collapses to nothing; for walls it is a solid slab across the
doorways. Removing it leaves complex (triangle) collision as the only simple
representation, which is what these meshes need.
"""
import json

import unreal

BASE = "/Game/Props/CyberpunkApartment20261020/CyberpunkApartment"
REPORT = r"D:\FPS3D\FPSGAME\Saved\_hull_removed.json"

NAMES = ["S_floors", "S_plate", "S_walls", "S_ceiling", "S_joinery", "S_doors",
         "S_finish", "S_balcony", "S_balcony_glass", "S_glazing", "S_trim",
         "S_facade"]

out = {"cleared": [], "failed": [], "readback": []}
eal = unreal.EditorAssetLibrary

for name in NAMES:
    path = "%s/StaticMeshes/%s" % (BASE, name)
    try:
        mesh = eal.load_asset(path + "." + name)
        body = mesh.get_editor_property("body_setup")
        agg = body.get_editor_property("agg_geom")

        for kind in ("convex_elems", "box_elems", "sphere_elems", "sphyl_elems"):
            arr = agg.get_editor_property(kind)
            if len(arr):
                arr.clear()
                agg.set_editor_property(kind, arr)

        body.set_editor_property("agg_geom", agg)
        body.set_editor_property("collision_trace_flag",
                                 unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)

        if unreal.EditorLoadingAndSavingUtils.save_packages(
                [unreal.load_package(path)], True):
            out["cleared"].append(name)
        else:
            out["failed"].append(name + " (save)")
    except Exception as exc:  # noqa: BLE001
        out["failed"].append("%s: %s: %s" % (name, type(exc).__name__, exc))

for name in NAMES:
    try:
        m = eal.load_asset("%s/StaticMeshes/%s.%s" % (BASE, name, name))
        b = m.get_editor_property("body_setup")
        agg = b.get_editor_property("agg_geom")
        out["readback"].append({
            "name": name,
            "convex": len(agg.get_editor_property("convex_elems")),
            "box": len(agg.get_editor_property("box_elems")),
            "flag": str(b.get_editor_property("collision_trace_flag")),
        })
    except Exception as exc:  # noqa: BLE001
        out["readback"].append({"name": name, "error": str(exc)})

with open(REPORT, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)
unreal.log("HULL_REMOVED_WRITTEN")