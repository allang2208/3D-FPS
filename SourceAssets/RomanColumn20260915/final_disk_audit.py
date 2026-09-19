import os, time
import unreal

D = "/Game/Props/RomanColumn20260915"
ASSETS = ["SM_RomanBaluster_Small", "SM_RomanRail_100", "SM_RomanRail_200", "SM_RomanRail_300",
          "SM_BalustradeSegment_20", "SM_RomanPavilionBase_20", "SM_RomanPavilionArch_20",
          "SM_RomanPavilionDome_20", "SM_RomanPavilionColonnade_20", "SM_RomanPavilionFull_20",
          "SM_RomanColumn_Round_20", "SM_RomanColumn_Detailed"]

def log(m):
    print("[final] " + m)

def stamp(rel):
    full = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()) + rel
    if not os.path.exists(full):
        return "MISSING"
    st = os.stat(full)
    return "%d B @ %s" % (st.st_size, time.strftime("%H:%M:%S", time.localtime(st.st_mtime)))

log("=== asset slot0 (fresh load from disk) ===")
for name in ASSETS:
    a = unreal.EditorAssetLibrary.load_asset(D + "/" + name)
    s = a.get_editor_property("static_materials")[0].get_editor_property("material_interface") if a else None
    mat = s.get_path_name().split(".")[-1] if s else "EMPTY/missing"
    log("  %-28s %-20s %s" % (name, mat, stamp("Props/RomanColumn20260915/" + name + ".uasset")))

log("=== palette ===")
pal = unreal.load_asset("/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette")
for e in (pal.get_editor_property("components") or []):
    s = e.get_editor_property("surface")
    log("  %-22s %-8s %s" % (str(e.get_editor_property("id")), str(e.get_editor_property("material")),
                             s.get_path_name().split(".")[-1] if s else "None"))
for m in (pal.get_editor_property("materials") or []):
    s = m.get_editor_property("surface")
    log("  [row] %-10s %s" % (str(m.get_editor_property("id")),
                              s.get_path_name().split(".")[-1] if s else "None"))
log("  palette file: %s" % stamp("Building/Voxels/Rounded/DA_VoxelBuildPalette.uasset"))
log("  umap file:    %s" % stamp("GameMaps/DayNight_Lighting.umap"))

log("=== voxel save (ColdSteelPlayer|DayNight) ===")
sg = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "SaveGames")
f = os.path.join(sg, "Voxel20_EA319301D380398C3E2B85F8D5D81163.sav")
if os.path.exists(f):
    data = open(f, "rb").read()
    log("  %d B @ %s | baluster=%d rail=%d marble=%d" % (
        os.path.getsize(f), time.strftime("%H:%M:%S", time.localtime(os.path.getmtime(f))),
        data.count(b"baluster_small"), data.count(b"balustrade_rail"), data.count(b"marble")))
else:
    log("  save missing!")
