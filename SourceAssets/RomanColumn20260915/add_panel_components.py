"""Put the roman prefab pieces into the palette the build component actually loads.

2026-09-16 finding: `UVoxelBuildComponent` loads
`/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette`, while the earlier registration wrote the
initial palette in the parent folder. The active palette had `components == []`, so the drawer
listed nothing. This adds the two requested pieces there.

Save path: the running editor already holds the asset, so an external process would fail
silently (see the case README). `EditorAssetLibrary.save_*` returns False from the remote
execution context, while `EditorLoadingAndSavingUtils.save_packages` works.

Runs in the running editor:
    python Tools/AssetPipeline/ue_python_exec.py --script SourceAssets/RomanColumn20260915/add_panel_components.py
"""

import unreal

ACTIVE = "/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette"
D = "/Game/Props/RomanColumn20260915"
# id, display name, mesh, footprint in 20 cm cells, surface
ENTRIES = [
    ("roman_column", "罗马柱", D + "/SM_RomanColumn_Detailed", (4, 4, 13), D + "/M_RomanStone_V2"),
    ("baluster_small", "矮栏杆罗马柱", D + "/SM_RomanBaluster_Small", (2, 2, 5), D + "/M_Plaster_Detailed"),
]


def log(message):
    print("[components] " + message)


def size_of(asset):
    extent = asset.get_bounds().box_extent
    return (round(extent.x * 2, 1), round(extent.y * 2, 1), round(extent.z * 2, 1))


palette = unreal.load_asset(ACTIVE)
if not palette:
    raise RuntimeError("palette not loadable: %s" % ACTIVE)

old = palette.get_editor_property("components") or []
log("active palette %s" % ACTIVE)
log("components before: %d -> %s" % (len(old), [str(e.get_editor_property("id")) for e in old]))

rebuilt = []
for entry in old:
    # Keep whatever else lives there; only the two requested ids are replaced.
    copy = unreal.VoxelBuildPrefab()
    copy.set_editor_property("id", entry.get_editor_property("id"))
    copy.set_editor_property("display_name", entry.get_editor_property("display_name"))
    copy.set_editor_property("mesh", entry.get_editor_property("mesh"))
    copy.set_editor_property("footprint", entry.get_editor_property("footprint"))
    copy.set_editor_property("surface", entry.get_editor_property("surface"))
    copy.set_editor_property("pivot_offset_cm", entry.get_editor_property("pivot_offset_cm"))
    rebuilt.append(copy)

for pid, name, mesh_path, cells, surface_path in ENTRIES:
    mesh = unreal.load_asset(mesh_path)
    surface = unreal.load_asset(surface_path)
    if not mesh or not surface:
        log("SKIP %s: mesh=%s surface=%s" % (pid, mesh is not None, surface is not None))
        continue
    actual = size_of(mesh)
    wanted = (cells[0] * 20, cells[1] * 20, cells[2] * 20)
    entry = unreal.VoxelBuildPrefab()
    entry.set_editor_property("id", pid)
    entry.set_editor_property("display_name", unreal.Text(name))
    entry.set_editor_property("mesh", mesh)
    entry.set_editor_property("footprint", unreal.IntVector(cells[0], cells[1], cells[2]))
    entry.set_editor_property("surface", surface)
    entry.set_editor_property("pivot_offset_cm", unreal.Vector(0.0, 0.0, 0.0))
    rebuilt = [e for e in rebuilt if str(e.get_editor_property("id")) != pid]
    rebuilt.append(entry)
    log("entry %-16s %-8s cells=%s mesh_size=%s expected=%s %s" % (
        pid, name, "x".join(str(v) for v in cells), actual, wanted,
        "OK" if actual == wanted else "MISMATCH"))

palette.modify()
palette.set_editor_property("components", rebuilt)
package = unreal.load_package(ACTIVE)
log("save_packages=%s" % unreal.EditorLoadingAndSavingUtils.save_packages([package], False))
log("saved package: %s" % package.get_name())

back = unreal.load_asset(ACTIVE)
entries = back.get_editor_property("components") or []
log("components after: %d" % len(entries))
for entry in entries:
    mesh = entry.get_editor_property("mesh")
    surface = entry.get_editor_property("surface")
    log("  %-16s %-8s %-16s %s mesh=%s surface=%s" % (
        str(entry.get_editor_property("id")),
        str(entry.get_editor_property("display_name")),
        str(entry.get_editor_property("footprint")),
        size_of(mesh) if mesh else "no mesh",
        mesh.get_path_name().split(".")[-1] if mesh else "None",
        surface.get_path_name().split(".")[-1] if surface else "None"))
