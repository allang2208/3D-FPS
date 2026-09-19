"""Next-process readback: load the upgraded baluster + palette fresh from disk.

Second process after upgrade_baluster_20260917.py; the numbers below are the evidence that
the rebuild and the material/palette sync actually landed on disk.
"""

import unreal

D = "/Game/Props/RomanColumn20260915"
BALUSTER = D + "/SM_RomanBaluster_Small"
STONE = D + "/M_RomanStone_V2"
PALETTE = "/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette"


def log(m):
    print("[verify] " + m)


asset = unreal.EditorAssetLibrary.load_asset(BALUSTER)
if not asset:
    log("FAIL: baluster not loadable from disk")
else:
    slots = asset.get_editor_property("static_materials")
    slot0 = slots[0].get_editor_property("material_interface") if slots else None
    extent = asset.get_bounds().box_extent
    log("slot0=%s dims=(%.1f, %.1f, %.1f)" % (
        slot0.get_path_name().split(".")[-1] if slot0 else "EMPTY",
        extent.x * 2, extent.y * 2, extent.z * 2))
    lod_count = asset.get_editor_property("static_materials") and len(slots)
    log("lods=%s material_slots=%s" % (asset.get_num_lods(), lod_count))

pal = unreal.load_asset(PALETTE)
for entry in (pal.get_editor_property("components") or []):
    if str(entry.get_editor_property("id")) == "baluster_small":
        surface = entry.get_editor_property("surface")
        log("palette baluster_small surface=%s footprint=%s" % (
            surface.get_path_name().split(".")[-1] if surface else "None",
            entry.get_editor_property("footprint")))

log("stone_matches=%s" % (slot0 is not None and slot0.get_path_name() == STONE + "." + "M_RomanStone_V2"))
