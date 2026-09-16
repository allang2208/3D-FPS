"""Wrap-up: put M_RomanStone_V2 on the roman pieces and in the palette, with read-back proof.

Lesson from the last rounds: an asset created in the same process is not loadable yet, and a
returned bool is not evidence. Every reference waits for loadability; every change is read back.
"""

import time

import unreal

SV = unreal.ModelingService
D = "/Game/Props/RomanColumn20260915"
COLUMN, SEG = D + "/SM_RomanColumn_Detailed", D + "/SM_BalustradeSegment_20"
STONE = D + "/M_RomanStone_V2"
PALETTE = "/Game/Building/Voxels/DA_VoxelBuildPalette"
LOG = []


def log(m):
    print("[wrap] " + m)


def wait(p, t=25.0):
    end = time.time() + t
    while time.time() < end:
        a = unreal.EditorAssetLibrary.load_asset(p)
        if a:
            return a
        time.sleep(0.4)
    return None


def slot_material(path):
    a = unreal.EditorAssetLibrary.load_asset(path)
    if not a:
        return "asset missing"
    slots = a.get_editor_property("static_materials")
    if not slots:
        return "no slots"
    m = slots[0].get_editor_property("material_interface")
    return m.get_path_name() if m else "EMPTY"


stone = wait(STONE)
log("stone material loadable: %s" % (stone is not None))
if stone:
    for path in (COLUMN, SEG):
        if not wait(path):
            log("SKIP %s (not loadable)" % path.split("/")[-1])
            continue
        r = SV.set_asset_materials(path, STONE, True)
        log("assign %-28s call=%s  readback=%s" % (
            path.split("/")[-1], getattr(r, "success", None), slot_material(path).split(".")[-1]))

# Rebuild the palette component array from scratch (writing into copies does not persist).
pal = wait(PALETTE)
old = pal.get_editor_property("components") if pal else []
log("palette entries before: %d" % len(old))
rebuilt = []
if pal:
    for e in old:
        pid = e.get_editor_property("id")
        mesh = e.get_editor_property("mesh")
        surf = e.get_editor_property("surface")
        fp = e.get_editor_property("footprint")
        name = e.get_editor_property("display_name")
        pivot = e.get_editor_property("pivot_offset_cm")
        if pid in ("roman_column", "balustrade_segment") and stone:
            surf = stone
        entry = unreal.VoxelBuildPrefab()
        entry.set_editor_property("id", pid)
        entry.set_editor_property("display_name", name)
        entry.set_editor_property("mesh", mesh)
        entry.set_editor_property("footprint", fp)
        entry.set_editor_property("surface", surf)
        entry.set_editor_property("pivot_offset_cm", pivot)
        rebuilt.append(entry)
    pal.set_editor_property("components", rebuilt)
    log("save_asset=%s" % unreal.EditorAssetLibrary.save_asset(PALETTE, False))

back = wait(PALETTE).get_editor_property("components")
log("palette entries after: %d" % len(back))
for e in back:
    s = e.get_editor_property("surface")
    log("  %-20s surface=%s" % (e.get_editor_property("id"),
                                s.get_path_name().split(".")[-1] if s else "None"))
