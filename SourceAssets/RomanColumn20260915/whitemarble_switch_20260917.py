"""Run INSIDE the live editor: switch the roman railing kit + pavilion + marble voxel row
from M_RomanStone_V2 (grey matte) to M_WhiteMarble_V2 (polished white, matches the floor).

Scope:
  assets (slot0):  SM_RomanBaluster_Small, SM_RomanRail_100/200/300, SM_BalustradeSegment_20,
                   SM_RomanPavilionBase/Arch/Dome/Colonnade/Full_20, SM_RomanColumn_Round_20
  map overrides:   RomanFence_* (railing), RomanPavilion2_* (pavilion) actors
  palette:         surface of baluster_small, rails, segment, pavilion_full, roman_column_round
                   + marble material row + door_marble  (9-field copy rebuild)
  NOT touched:     roman_column (square colonnade column), door_wood/stone/physics
"""

import os
import time

import unreal

D = "/Game/Props/RomanColumn20260915"
PALETTE = "/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette"
WHITE = D + "/M_WhiteMarble_V2"
FIELDS = ("id", "display_name", "mesh", "footprint", "surface", "pivot_offset_cm",
          "actor_class", "actor_offset_cm", "material")
ASSETS = [D + "/SM_RomanBaluster_Small", D + "/SM_RomanRail_100", D + "/SM_RomanRail_200",
          D + "/SM_RomanRail_300", D + "/SM_BalustradeSegment_20",
          D + "/SM_RomanPavilionBase_20", D + "/SM_RomanPavilionArch_20",
          D + "/SM_RomanPavilionDome_20", D + "/SM_RomanPavilionColonnade_20",
          D + "/SM_RomanPavilionFull_20", D + "/SM_RomanColumn_Round_20"]
PREFAB_IDS = ("baluster_small", "balustrade_rail_100", "balustrade_rail_200",
              "balustrade_rail_300", "balustrade_segment", "pavilion_full",
              "roman_column_round")
STARTED = time.time()


def log(m):
    print("[white] " + m)


def project_disk(rel):
    full = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()) + \
        rel.split("/Game/", 1)[1] + ".uasset"
    return full


def disk_stamp(rel):
    full = project_disk(rel)
    if not os.path.exists(full):
        return None
    st = os.stat(full)
    return st.st_size, time.strftime("%H:%M:%S", time.localtime(st.st_mtime)), st.st_mtime


white = unreal.EditorAssetLibrary.load_asset(WHITE)
log("white loadable: %s" % (white is not None))

# ------------------------------------------------- 1. asset slot0 -> white marble
for path in ASSETS:
    a = unreal.EditorAssetLibrary.load_asset(path)
    if not a:
        log("SKIP missing asset %s" % path.split("/")[-1])
        continue
    ok = unreal.ModelingService.set_asset_materials(path, WHITE, True)
    log("asset %-30s set=%s" % (path.split("/")[-1], getattr(ok, "success", None)))
packages = [unreal.load_package(p) for p in ASSETS if unreal.load_package(p)]
log("asset save_packages=%s" % unreal.EditorLoadingAndSavingUtils.save_packages(packages, False))

# ----------------------------------------------------- 2. map actor overrides
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
n_fence = n_pav = 0
for a in sub.get_all_level_actors():
    label = a.get_actor_label()
    if label.startswith("RomanFence_") or label.startswith("RomanPavilion2_"):
        for comp in a.get_components_by_class(unreal.StaticMeshComponent):
            comp.set_material(0, white)
        if label.startswith("RomanFence_"):
            n_fence += 1
        else:
            n_pav += 1
log("map overrides: fence=%d pavilion=%d" % (n_fence, n_pav))

# ------------------------------------------------------------- 3. palette swap
pal = unreal.load_asset(PALETTE)
rebuilt, changed = [], []
for e in pal.get_editor_property("components") or []:
    copy = unreal.VoxelBuildPrefab()
    for f in FIELDS:
        copy.set_editor_property(f, e.get_editor_property(f))
    pid = str(copy.get_editor_property("id"))
    if pid in PREFAB_IDS:
        copy.set_editor_property("surface", white)
        changed.append("component:" + pid)
    rebuilt.append(copy)
mats = []
for m in pal.get_editor_property("materials") or []:
    mid = str(m.get_editor_property("id"))
    if mid in ("marble",):
        m.set_editor_property("surface", white)
        changed.append("material:" + mid)
    mats.append(m)
# door_marble follows the marble row
for e in rebuilt:
    if str(e.get_editor_property("id")) == "door_marble":
        e.set_editor_property("surface", white)
        changed.append("component:door_marble")
pal.modify()
pal.set_editor_property("materials", mats)
pal.set_editor_property("components", rebuilt)
log("palette changes: %s" % changed)
log("palette save_packages=%s" % unreal.EditorLoadingAndSavingUtils.save_packages(
    [unreal.load_package(PALETTE)], False))

# --------------------------------------------------------------- 4. save map
saved = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
log("map save=%s" % saved)

# --------------------------------------------------------------- 5. evidence
log("=== disk stamps (expect all FRESH) ===")
for rel in ASSETS + [PALETTE.split("/Game/", 1)[1].replace("/", "/")]:
    stamp = disk_stamp("/Game/" + rel.strip("/")) if not rel.startswith("/") else disk_stamp(rel)
for path in ASSETS:
    s = disk_stamp(path)
    fresh = bool(s and s[2] >= STARTED - 15)
    log("  %-30s %s %s" % (path.split("/")[-1], "%d B / %s" % (s[0], s[1]) if s else "missing",
                           "FRESH" if fresh else "stale"))
ps = disk_stamp(PALETTE)
log("  %-30s %s %s" % ("DA_VoxelBuildPalette", "%d B / %s" % (ps[0], ps[1]) if ps else "missing",
                       "FRESH" if ps and ps[2] >= STARTED - 15 else "stale"))
ms = disk_stamp("/Game/GameMaps/DayNight_Lighting")
full = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()) + "GameMaps/DayNight_Lighting.umap"
st = os.stat(full)
log("  %-30s %d B / %s" % ("DayNight_Lighting.umap", st.st_size,
                           time.strftime("%H:%M:%S", time.localtime(st.st_mtime))))

# readback
back = unreal.load_asset(PALETTE)
for e in back.get_editor_property("components") or []:
    surf = e.get_editor_property("surface")
    log("  pal %-22s surf=%s" % (str(e.get_editor_property("id")),
                                 surf.get_path_name().split(".")[-1] if surf else "None"))
log("RESULT: %s" % ("PASS" if saved else "CHECK"))
