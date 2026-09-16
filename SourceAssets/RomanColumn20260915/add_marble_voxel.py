"""Add the marble voxel (石材类体素) to the active build palette.

User request 2026-09-16: "体素栏新加入一个新的体素，大理石体素，就用罗马柱的材质做一个 20*20cm 的体素块".
The voxel surface generator writes world-projected UVs, so the roman stone material (a plain
UV0 material with StoneNoise / StoneDetail texture parameters) drives the 20 cm blocks directly.

Physics: `UVoxelBuildPalette::Physical()` only special-cases `stone`, so a new id would silently
fall back to the wood defaults. The entry therefore carries an explicit override with the same
stone-class numbers the code uses for 石头.

Runs in the running editor:
    python Tools/AssetPipeline/ue_python_exec.py --script SourceAssets/RomanColumn20260915/add_marble_voxel.py
"""

import unreal

ACTIVE = "/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette"
MARBLE_SURFACE = "/Game/Props/RomanColumn20260915/M_RomanStone_V2"


def log(message):
    print("[marble] " + message)


def make_material(entry_id, caption, surface_path, physics):
    surface = unreal.load_asset(surface_path)
    if not surface:
        raise RuntimeError("surface not loadable: %s" % surface_path)
    entry = unreal.VoxelBuildMaterial()
    entry.set_editor_property("id", entry_id)
    entry.set_editor_property("display_name", unreal.Text(caption))
    entry.set_editor_property("surface", surface)
    entry.set_editor_property("supports_weight", True)
    if physics:
        values = unreal.VoxelPhysicalMaterial()
        values.set_editor_property("density_kg_m3", physics[0])
        values.set_editor_property("compression_pa", physics[1])
        values.set_editor_property("tension_pa", physics[2])
        values.set_editor_property("shear_pa", physics[3])
        values.set_editor_property("durability", physics[4])
        values.set_editor_property("joules_per_damage", physics[5])
        entry.set_editor_property("physics", values)
        entry.set_editor_property("override_physics", True)
    return entry


palette = unreal.load_asset(ACTIVE)
if not palette:
    raise RuntimeError("palette not loadable: %s" % ACTIVE)

old = palette.get_editor_property("materials") or []
log("materials before: %s" % [str(m.get_editor_property("id")) for m in old])

rebuilt = []
for entry in old:
    if str(entry.get_editor_property("id")) == "marble":
        continue
    copy = unreal.VoxelBuildMaterial()
    copy.set_editor_property("id", entry.get_editor_property("id"))
    copy.set_editor_property("display_name", entry.get_editor_property("display_name"))
    copy.set_editor_property("surface", entry.get_editor_property("surface"))
    copy.set_editor_property("example_mesh", entry.get_editor_property("example_mesh"))
    copy.set_editor_property("supports_weight", entry.get_editor_property("supports_weight"))
    copy.set_editor_property("override_physics", entry.get_editor_property("override_physics"))
    copy.set_editor_property("physics", entry.get_editor_property("physics"))
    rebuilt.append(copy)

# Stone-class defaults, same numbers UVoxelBuildPalette::Physical() applies to `stone`.
rebuilt.append(make_material("marble", "大理石", MARBLE_SURFACE, (2600.0, 3000000.0, 12000.0, 40000.0, 500.0, 15.0)))

palette.modify()
palette.set_editor_property("materials", rebuilt)
log("save_packages=%s" % unreal.EditorLoadingAndSavingUtils.save_packages([unreal.load_package(ACTIVE)], False))

back = unreal.load_asset(ACTIVE)
for entry in back.get_editor_property("materials") or []:
    surface = entry.get_editor_property("surface")
    physics = entry.get_editor_property("physics")
    log("  %-8s %-8s override=%s surface=%s density=%.0f compression=%.0f tension=%.0f durability=%.0f" % (
        str(entry.get_editor_property("id")), str(entry.get_editor_property("display_name")),
        entry.get_editor_property("override_physics"),
        surface.get_path_name().split(".")[-1] if surface else "None",
        physics.get_editor_property("density_kg_m3"), physics.get_editor_property("compression_pa"),
        physics.get_editor_property("tension_pa"), physics.get_editor_property("durability")))
