"""Group each placed prefab under the material row whose 其他构造 submenu lists it.

2026-09-16: the drawer lists voxel shapes plus same-material constructions under every material
row. Which material owns a construction is palette data (`FVoxelBuildPrefab::Material`, a stable
material ID such as `marble`), not a code branch, so adding pieces later needs no C++ change.

Run against the editor that owns the asset (the load/save path below is the one that works from a
remote-execution context):
    python Tools/AssetPipeline/ue_python_exec.py --script SourceAssets/RomanColumn20260915/set_prefab_panel_material.py
Headless equivalent:
    UnrealEditor-Cmd.exe D:/FPS3D/FPSGAME/FPSGAME.uproject -run=pythonscript
        -script=<abs path> -unattended -nop4 -nosplash -NullRHI
"""

import unreal

ACTIVE = "/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette"
# component id -> material id it is listed under. Ids not listed here keep whatever the asset has.
GROUPS = {
    "roman_column": "marble",
    "baluster_small": "stone",
}
# Fields carried over unchanged when an entry is rewritten.
COPY_FIELDS = ("id", "display_name", "mesh", "footprint", "surface", "pivot_offset_cm")


def log(message):
    print("[panel-group] " + message)


palette = unreal.load_asset(ACTIVE)
if not palette:
    raise RuntimeError("palette not loadable: %s" % ACTIVE)

material_ids = [str(entry.get_editor_property("id")) for entry in (palette.get_editor_property("materials") or [])]
log("palette %s" % ACTIVE)
log("materials: %s" % material_ids)
for component_id, material_id in GROUPS.items():
    if material_id not in material_ids:
        log("WARNING %s -> %s: material id missing from the palette" % (component_id, material_id))

entries = palette.get_editor_property("components") or []
log("components before: %d" % len(entries))
rebuilt = []
for entry in entries:
    component_id = str(entry.get_editor_property("id"))
    copy = unreal.VoxelBuildPrefab()
    for field in COPY_FIELDS:
        copy.set_editor_property(field, entry.get_editor_property(field))
    if component_id in GROUPS:
        copy.set_editor_property("material", unreal.Name(GROUPS[component_id]))
    rebuilt.append(copy)
    log("  %-16s -> %s" % (component_id, GROUPS.get(component_id, "(unchanged)")))

palette.modify()
palette.set_editor_property("components", rebuilt)
package = unreal.load_package(ACTIVE)
log("save_packages=%s" % unreal.EditorLoadingAndSavingUtils.save_packages([package], False))
log("saved package: %s" % package.get_name())

back = unreal.load_asset(ACTIVE)
for entry in (back.get_editor_property("components") or []):
    log("  %-16s %-8s material=%s mesh=%s" % (
        str(entry.get_editor_property("id")),
        str(entry.get_editor_property("footprint")),
        str(entry.get_editor_property("material")),
        entry.get_editor_property("mesh").get_path_name().split(".")[-1]
        if entry.get_editor_property("mesh") else "no mesh"))
