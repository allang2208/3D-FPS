"""Read-only recon: where the roman pavilion lives, what it measures, how the dome profile looks.

Headless:  UnrealEditor-Cmd <uproject> -run=pythonscript -script=<this> -unattended -NullRHI -nosplash
"""

import unreal

SV = unreal.ModelingService
LEVEL = "/Game/GameMaps/DayNight_Lighting"
D = "/Game/Props/RomanColumn20260915"


def log(m):
    print("[recon] " + m)


# ---------------------------------------------------------------- level actors
sub = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
try:
    sub.load_level(LEVEL)
    log("level loaded: %s" % LEVEL)
except Exception as exc:
    log("level load failed: %s" % exc)

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
log("level actor count: %d" % len(actors))
KEYS = ("pavilion", "roman", "balust", "colonnade", "marble", "floor", "column")
hits = 0
for a in actors:
    label = a.get_actor_label()
    low = label.lower()
    if any(k in low for k in KEYS):
        hits += 1
        loc = a.get_actor_location()
        rot = a.get_actor_rotation()
        extra = ""
        try:
            smc = a.static_mesh_component
            mesh = smc.static_mesh
            extra = " mesh=%s" % (mesh.get_path_name() if mesh else "None")
            origin, extent = mesh.get_bounds().origin, mesh.get_bounds().box_extent
            extra += " bbox[%s x %s x %s]" % (round(extent.x * 2), round(extent.y * 2), round(extent.z * 2))
        except Exception:
            pass
        log("  %-28s loc=(%.1f,%.1f,%.1f) yaw=%.1f%s" % (label, loc.x, loc.y, loc.z, rot.yaw, extra))
log("keyed actors: %d" % hits)

# ------------------------------------------------------------- dome silhouette
for name in ("SM_PavilionDome_20", "SM_PavilionRing_20", "SM_PavilionStylobate_20"):
    path = D + "/" + name
    mesh = unreal.EditorAssetLibrary.load_asset(path)
    if not mesh:
        log("%s: MISSING" % name)
        continue
    bb = mesh.get_bounds()
    tri = mesh.get_num_triangles(0) if hasattr(mesh, "get_num_triangles") else -1
    log("%s: bbox origin=(%.1f,%.1f,%.1f) extent=(%.1f,%.1f,%.1f) tris=%s" % (
        name, bb.origin.x, bb.origin.y, bb.origin.z, bb.box_extent.x, bb.box_extent.y, bb.box_extent.z, tri))
    mats = []
    try:
        for i in range(len(mesh.get_editor_property("static_materials"))):
            m = mesh.get_editor_property("static_materials")[i]
            mats.append(m.material_interface.get_path_name() if m.material_interface else "None")
    except Exception as exc:
        mats.append("err %s" % exc)
    log("   materials: %s" % mats)

# ------------------------------------------------------------------- palette
for pal in ("/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette", "/Game/Building/Voxels/DA_VoxelBuildPalette"):
    p = unreal.EditorAssetLibrary.load_asset(pal)
    if not p:
        log("palette MISSING: %s" % pal)
        continue
    comps = p.get_editor_property("components")
    mats = p.get_editor_property("materials")
    log("palette %s: %d prefabs, %d materials" % (pal, len(comps), len(mats)))
    for c in comps:
        fp = c.get_editor_property("footprint")
        log("   %-22s %-16s cells %sx%sx%s" % (c.get_editor_property("id"),
                                               str(c.get_editor_property("display_name")),
                                               fp.x, fp.y, fp.z))
    for m in mats:
        log("   mat %-14s %-12s %s" % (m.get_editor_property("id"),
                                       str(m.get_editor_property("display_name")),
                                       m.get_editor_property("surface").get_path_name()
                                       if m.get_editor_property("surface") else "None"))

log("RESULT: DONE")
