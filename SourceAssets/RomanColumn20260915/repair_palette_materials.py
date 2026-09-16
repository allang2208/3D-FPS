"""Rebuild the active palette's material entries from the workflow's reference list.

Needed because the 2026-09-16 live-coding experiment with a USTRUCT default value made
FVoxelBuildMaterial unreadable in that editor session, and the retune script then wrote the
empty result into /Game/Building/Voxels/Rounded/DA_VoxelBuildPalette.

Run from a fresh process (editor closed is safest, headless is fine):
    python Tools/AssetPipeline/ue_python_exec.py --script SourceAssets/RomanColumn20260915/repair_palette_materials.py
    UnrealEditor-Cmd <uproject> -run=pythonscript -script=<this> -nullrhi -unattended

Reference list: Docs/Building/voxel-build-workflow.md section 6.
"""

import unreal

ACTIVE = "/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette"
MATERIALS = [
    # id, caption, surface, example mesh, physics override (None = use UVoxelBuildPalette::Physical())
    ("wood", "木材", "/Game/Building/Voxels/Rounded/M_Voxel_Wood", "/Game/Building/Voxels/Rounded/SM_Voxel20_Wood", None),
    ("stone", "石头", "/Game/Building/Voxels/Rounded/M_Voxel_Stone", "/Game/Building/Voxels/Rounded/SM_Voxel20_Stone", None),
    ("marble", "大理石", "/Game/Props/RomanColumn20260915/M_RomanStone_V2", "/Game/Building/Voxels/Rounded/SM_Voxel20_Stone",
     (2600.0, 3000000.0, 450000.0, 40000.0, 500.0, 15.0)),
]


def log(message):
    print("[repair] " + message)


def load(path):
    asset = unreal.EditorAssetLibrary.load_asset(path) or unreal.load_asset(path)
    if not asset:
        raise RuntimeError("not loadable: %s" % path)
    return asset


palette = load(ACTIVE)
kept_components = list(palette.get_editor_property("components") or [])
log("components kept: %s" % [str(c.get_editor_property("id")) for c in kept_components])

entries = []
for entry_id, caption, surface_path, mesh_path, physics in MATERIALS:
    entry = unreal.VoxelBuildMaterial()
    entry.set_editor_property("id", entry_id)
    entry.set_editor_property("display_name", unreal.Text(caption))
    entry.set_editor_property("surface", load(surface_path))
    entry.set_editor_property("example_mesh", load(mesh_path))
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
    entries.append(entry)

palette.modify()
palette.set_editor_property("materials", entries)
palette.set_editor_property("components", kept_components)
saved = unreal.EditorAssetLibrary.save_asset(ACTIVE, False)
if not saved:
    saved = unreal.EditorLoadingAndSavingUtils.save_packages([unreal.load_package(ACTIVE)], False)
log("save=%s" % saved)

back = load(ACTIVE)
for entry in back.get_editor_property("materials") or []:
    surface = entry.get_editor_property("surface")
    physics = entry.get_editor_property("physics")
    log("  %-8s %-8s override=%s surface=%s density=%.0f tension=%.0f" % (
        str(entry.get_editor_property("id")), str(entry.get_editor_property("display_name")),
        entry.get_editor_property("override_physics"),
        surface.get_name() if surface else "None",
        physics.get_editor_property("density_kg_m3"), physics.get_editor_property("tension_pa")))
for entry in back.get_editor_property("components") or []:
    mesh = entry.get_editor_property("mesh")
    log("  component %-16s mesh=%s footprint=%s" % (
        str(entry.get_editor_property("id")), mesh.get_name() if mesh else "None",
        str(entry.get_editor_property("footprint"))))
