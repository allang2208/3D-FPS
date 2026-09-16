"""Retune the marble voxel entry so its explicit physics match the new joint balance.

The balance lives in `UVoxelBuildPalette::Physical()` (stone/marble 500 kPa tension, wood 120 kPa).
The marble entry keeps an explicit override so the palette inspector shows the numbers the game
actually uses; keep both in sync when tuning.

Runs in the running editor:
    python Tools/AssetPipeline/ue_python_exec.py --script SourceAssets/RomanColumn20260915/retune_voxel_joints.py
"""

import unreal

ACTIVE = "/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette"
OVERRIDES = {
    # 2026-09-16: doubled per user request (see Docs/Building/voxel-build-workflow.md).
    # 2026-09-16 (second pass): shear 80 -> 300 kPa for the "cannot build past 1 m" report; the
    # diagnosis is in Docs/Building/voxel-vertical-build-diagnosis-20260916.md.
    # 2026-09-16 (third pass): every voxel weighs a quarter of what it did (2600 -> 650 kg/m3).
    "marble": (650.0, 6000000.0, 900.0 * 1000.0, 300.0 * 1000.0, 500.0, 15.0),
}


def log(message):
    print("[retune] " + message)


palette = unreal.load_asset(ACTIVE)
if not palette:
    raise RuntimeError("palette not loadable: %s" % ACTIVE)

rebuilt = []
for entry in palette.get_editor_property("materials") or []:
    entry_id = str(entry.get_editor_property("id"))
    copy = unreal.VoxelBuildMaterial()
    copy.set_editor_property("id", entry.get_editor_property("id"))
    copy.set_editor_property("display_name", entry.get_editor_property("display_name"))
    copy.set_editor_property("surface", entry.get_editor_property("surface"))
    copy.set_editor_property("example_mesh", entry.get_editor_property("example_mesh"))
    copy.set_editor_property("supports_weight", entry.get_editor_property("supports_weight"))
    copy.set_editor_property("override_physics", entry.get_editor_property("override_physics"))
    copy.set_editor_property("physics", entry.get_editor_property("physics"))
    if entry_id in OVERRIDES:
        density, compression, tension, shear, durability, joules = OVERRIDES[entry_id]
        values = unreal.VoxelPhysicalMaterial()
        values.set_editor_property("density_kg_m3", density)
        values.set_editor_property("compression_pa", compression)
        values.set_editor_property("tension_pa", tension)
        values.set_editor_property("shear_pa", shear)
        values.set_editor_property("durability", durability)
        values.set_editor_property("joules_per_damage", joules)
        copy.set_editor_property("physics", values)
        copy.set_editor_property("override_physics", True)
        log("override %s tension=%.0f compression=%.0f" % (entry_id, tension, compression))
    rebuilt.append(copy)

palette.modify()
palette.set_editor_property("materials", rebuilt)
log("save_packages=%s" % unreal.EditorLoadingAndSavingUtils.save_packages([unreal.load_package(ACTIVE)], False))

back = unreal.load_asset(ACTIVE)
for entry in back.get_editor_property("materials") or []:
    physics = entry.get_editor_property("physics")
    log("  %-8s override=%s density=%.0f tension=%.0f compression=%.0f shear=%.0f" % (
        str(entry.get_editor_property("id")), entry.get_editor_property("override_physics"),
        physics.get_editor_property("density_kg_m3"), physics.get_editor_property("tension_pa"),
        physics.get_editor_property("compression_pa"), physics.get_editor_property("shear_pa")))
