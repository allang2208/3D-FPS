"""Final read-back in a fresh process: what is actually on disk for the v2 pavilion."""

import os
import time

import unreal

DIR = "/Game/Props/RomanColumn20260915"
LEVEL = "/Game/GameMaps/DayNight_Lighting"
CONTENT = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())

PIECES = ("SM_RomanPavilionBase_20", "SM_RomanPavilionColonnade_20",
          "SM_RomanPavilionArch_20", "SM_RomanPavilionDome_20")


def log(m):
    print("[v2] " + m)


for name in PIECES:
    full = CONTENT + "Props/RomanColumn20260915/" + name + ".uasset"
    st = os.stat(full) if os.path.exists(full) else None
    asset = unreal.EditorAssetLibrary.load_asset(DIR + "/" + name)
    bb = asset.get_bounds() if asset else None
    log("%-30s %s  %s tris=%s  bbox %.0fx%.0fx%.0f" % (
        name,
        "%8d B / %s" % (st.st_size, time.strftime("%H:%M:%S", time.localtime(st.st_mtime))) if st else "MISSING",
        "loaded" if asset else "LOAD FAILED",
        asset.get_num_triangles(0) if asset else "-",
        bb.box_extent.x * 2, bb.box_extent.y * 2, bb.box_extent.z * 2) if bb else "")

pal = CONTENT + "Building/Voxels/Rounded/DA_VoxelBuildPalette.uasset"
st = os.stat(pal)
log("palette %d B / %s" % (st.st_size, time.strftime("%H:%M:%S", time.localtime(st.st_mtime))))

sub = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
sub.load_level(LEVEL)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
mine = sorted([a for a in actors if a.get_actor_label().startswith("RomanPavilion2")],
              key=lambda a: a.get_actor_label())
old = [a.get_actor_label() for a in actors if a.get_actor_label().startswith("Pavilion_")]
log("level: %d actors total, %d new pavilion, %d legacy pavilion (want 0)" % (
    len(actors), len(mine), len(old)))
zs = {}
for a in mine:
    loc = a.get_actor_location()
    mesh = a.static_mesh_component.static_mesh
    zs.setdefault(round(loc.z), []).append(mesh.get_name() if mesh else "None")
for z in sorted(zs):
    log("  z=%4d  %d actor(s): %s" % (z, len(zs[z]), sorted(set(zs[z]))))
lvl = CONTENT + "GameMaps/DayNight_Lighting.umap"
st = os.stat(lvl)
log("level file %d B / %s" % (st.st_size, time.strftime("%H:%M:%S", time.localtime(st.st_mtime))))
log("RESULT: " + ("PASS" if len(mine) == 13 and not old else "CHECK"))
