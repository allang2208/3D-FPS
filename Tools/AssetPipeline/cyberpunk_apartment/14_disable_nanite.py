"""Disable Nanite on the architectural meshes.

Root cause of the falling: the glTF importer enabled Nanite on every mesh.
Nanite renders virtualised geometry and its render data is not a reliable
source for complex collision, so CTF_USE_COMPLEX_AS_SIMPLE produces no
walkable surface and the pawn falls through.

Turning Nanite off restores the classic triangle data that both rendering and
complex collision read, which is what these low-poly architectural meshes
want anyway (S_floors is 24 triangles - Nanite adds nothing).
"""
import json

import unreal

BASE = "/Game/Props/CyberpunkApartment20261020/CyberpunkApartment"
REPORT = r"D:\FPS3D\FPSGAME\Saved\_nanite_off.json"

NAMES = ["S_plate", "S_floors", "S_walls", "S_ceiling", "S_trim", "S_joinery",
         "S_finish", "S_doors", "S_facade", "S_balcony", "S_balcony_glass",
         "S_glazing", "FOY_room", "COR_room", "KIT_run", "KIT_dining",
         "B2_room", "B3_room", "MST_room", "BA1_room", "BA2_room", "UTL_room",
         "LIV_furniture", "LIV_rug", "DET_practicals"]

out = {"disabled": [], "failed": [], "readback": []}

for name in NAMES:
    path = "%s/StaticMeshes/%s" % (BASE, name)
    try:
        mesh = unreal.EditorAssetLibrary.load_asset(path + "." + name)
        if mesh is None:
            out["failed"].append(name + " (load)")
            continue
        ns = mesh.get_editor_property("nanite_settings")
        ns.set_editor_property("enabled", False)
        mesh.set_editor_property("nanite_settings", ns)

        ok = unreal.EditorLoadingAndSavingUtils.save_packages(
            [unreal.load_package(path)], True)
        if ok:
            out["disabled"].append(name)
        else:
            out["failed"].append(name + " (save)")
    except Exception as exc:  # noqa: BLE001
        out["failed"].append("%s: %s: %s" % (name, type(exc).__name__, exc))

for name in NAMES:
    try:
        m = unreal.EditorAssetLibrary.load_asset(
            "%s/StaticMeshes/%s.%s" % (BASE, name, name))
        ns = m.get_editor_property("nanite_settings")
        out["readback"].append({
            "name": name,
            "nanite": str(ns.get_editor_property("enabled")),
            "flag": str(m.get_editor_property("body_setup")
                        .get_editor_property("collision_trace_flag")),
        })
    except Exception as exc:  # noqa: BLE001
        out["readback"].append({"name": name, "error": str(exc)})

with open(REPORT, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)
unreal.log("NANITE_OFF_WRITTEN")