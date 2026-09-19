"""Headless (editor closed): switch the square-base Roman column to white marble too.

- SM_RomanColumn_Detailed slot0 -> M_WhiteMarble_V2
- palette roman_column surface -> M_WhiteMarble_V2 (9-field copy)
- map: Colonnade_C*/RomanColumn_Home actors get their override set (or refreshed) to white
- save all + disk stamps
"""

import os
import time

import unreal

D = "/Game/Props/RomanColumn20260915"
WHITE = D + "/M_WhiteMarble_V2"
PALETTE = "/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette"
FIELDS = ("id", "display_name", "mesh", "footprint", "surface", "pivot_offset_cm",
          "actor_class", "actor_offset_cm", "material")
STARTED = time.time()


def log(m):
    print("[sq] " + m)


def stamp(rel):
    full = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()) + rel
    if not os.path.exists(full):
        return "MISSING"
    st = os.stat(full)
    fresh = st.st_mtime >= STARTED - 15
    return "%d B @ %s %s" % (st.st_size, time.strftime("%H:%M:%S", time.localtime(st.st_mtime)),
                             "FRESH" if fresh else "stale")


white = unreal.EditorAssetLibrary.load_asset(WHITE)
log("white=%s" % (white is not None))

# 1. asset slot
r = unreal.ModelingService.set_asset_materials(D + "/SM_RomanColumn_Detailed", WHITE, True)
log("asset set=%s" % getattr(r, "success", None))
log("asset save=%s" % unreal.EditorLoadingAndSavingUtils.save_packages(
    [unreal.load_package(D + "/SM_RomanColumn_Detailed")], False))

# 2. palette entry
pal = unreal.load_asset(PALETTE)
rebuilt = []
for e in pal.get_editor_property("components") or []:
    copy = unreal.VoxelBuildPrefab()
    for f in FIELDS:
        copy.set_editor_property(f, e.get_editor_property(f))
    if str(copy.get_editor_property("id")) == "roman_column":
        copy.set_editor_property("surface", white)
        log("palette roman_column surface -> white")
    rebuilt.append(copy)
pal.modify()
pal.set_editor_property("components", rebuilt)
log("palette save=%s" % unreal.EditorLoadingAndSavingUtils.save_packages(
    [unreal.load_package(PALETTE)], False))

# 3. map actors (colonnade + any leftover single column)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
n = 0
for a in sub.get_all_level_actors():
    label = a.get_actor_label()
    if label.startswith("Colonnade_C") or label == "RomanColumn_Home":
        mesh = None
        for comp in a.get_components_by_class(unreal.StaticMeshComponent):
            mesh = comp.get_editor_property("static_mesh")
            if mesh and "RomanColumn_Detailed" in mesh.get_name():
                comp.set_material(0, white)
                n += 1
        log("  %-22s mesh=%s -> white" % (label, mesh.get_name() if mesh else "-"))
log("map column actors updated: %d" % n)
saved = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
log("map save=%s" % saved)

# 4. disk evidence
log("column asset: %s" % stamp("Props/RomanColumn20260915/SM_RomanColumn_Detailed.uasset"))
log("palette:      %s" % stamp("Building/Voxels/Rounded/DA_VoxelBuildPalette.uasset"))
log("umap:         %s" % stamp("GameMaps/DayNight_Lighting.umap"))
log("RESULT: %s" % ("PASS" if saved else "CHECK"))
