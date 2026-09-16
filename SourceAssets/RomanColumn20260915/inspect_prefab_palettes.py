"""Read-only: dump the build palettes and the roman prefab candidates.

Runs in the running editor over Python remote execution (or headless):
    python Tools/AssetPipeline/ue_python_exec.py --script SourceAssets/RomanColumn20260915/inspect_prefab_palettes.py

Uses unreal.load_asset rather than unreal.EditorAssetLibrary: the editor-scripting-utilities
layer returns empty defaults while the editor is in PIE, the plain loader keeps working.
"""

import unreal

PALETTES = [
    "/Game/Building/Voxels/DA_VoxelBuildPalette",
    "/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette",
]
MESHES = [
    "/Game/Props/RomanColumn20260915/SM_RomanColumn",
    "/Game/Props/RomanColumn20260915/SM_RomanColumn_Detailed",
    "/Game/Props/RomanColumn20260915/SM_RomanBaluster_Small",
    "/Game/Props/RomanColumn20260915/SM_BalustradeSegment_20",
    "/Game/Props/RomanColumn20260915/SM_Balustrade_Rail",
    "/Game/Props/RomanColumn20260915/SM_Balustrade_Plinth",
    "/Game/Props/RomanColumn20260915/SM_PavilionStylobate_20",
    "/Game/Props/RomanColumn20260915/SM_PavilionRing_20",
    "/Game/Props/RomanColumn20260915/SM_PavilionDome_20",
]


def dump_palette(path):
    palette = unreal.load_asset(path)
    print("=== PALETTE %s loaded=%s" % (path, palette is not None))
    if not palette:
        return
    materials = palette.get_editor_property("materials") or []
    components = palette.get_editor_property("components") or []
    print("    materials=%d components=%d edge=%.2f cantilever=%.1f" % (
        len(materials), len(components),
        palette.get_editor_property("edge_radius_cm") or 0.0,
        palette.get_editor_property("max_cantilever_cm") or 0.0))
    for entry in materials:
        print("    M id=%-12s name=%-12s surface=%s mesh=%s" % (
            entry.get_editor_property("id"),
            str(entry.get_editor_property("display_name")),
            entry.get_editor_property("surface"),
            entry.get_editor_property("example_mesh")))
    for entry in components:
        print("    C id=%-22s name=%-14s footprint=%s mesh=%s surface=%s" % (
            entry.get_editor_property("id"),
            str(entry.get_editor_property("display_name")),
            entry.get_editor_property("footprint"),
            entry.get_editor_property("mesh"),
            entry.get_editor_property("surface")))


def dump_mesh(path):
    mesh = unreal.load_asset(path)
    if not mesh:
        print("=== MESH %s MISSING" % path)
        return
    bounds = mesh.get_bounds()
    extent = bounds.box_extent
    origin = bounds.origin
    slots = mesh.get_editor_property("static_materials") or []
    print("=== MESH %-52s origin=(%.1f,%.1f,%.1f) extent=(%.1f,%.1f,%.1f) size=(%.1f,%.1f,%.1f) z=%.1f..%.1f mats=%s" % (
        path.rsplit("/", 1)[-1], origin.x, origin.y, origin.z, extent.x, extent.y, extent.z,
        extent.x * 2, extent.y * 2, extent.z * 2, origin.z - extent.z, origin.z + extent.z,
        [str(slot.get_editor_property("material_interface")) for slot in slots]))


for palette_path in PALETTES:
    dump_palette(palette_path)
for mesh_path in MESHES:
    dump_mesh(mesh_path)
