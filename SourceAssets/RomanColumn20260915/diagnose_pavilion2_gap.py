"""Diagnose the two reported defects: an extra ring on the dome crown, and a gap between
the dome and the columns. Prints每个构件的本地包围盒（看 pivot 在不在底面）、关卡里每个
actor 的世界 z，以及拼装后相邻构件之间的 z 关系。"""

import unreal

D = "/Game/Props/RomanColumn20260915"
LEVEL = "/Game/GameMaps/DayNight_Lighting"
PIECES = {
    "SM_RomanPavilionBase_20": D + "/SM_RomanPavilionBase_20",
    "SM_RomanPavilionColonnade_20": D + "/SM_RomanPavilionColonnade_20",
    "SM_RomanPavilionArch_20": D + "/SM_RomanPavilionArch_20",
    "SM_RomanPavilionDome_20": D + "/SM_RomanPavilionDome_20",
    "SM_RomanColumn_Detailed": D + "/SM_RomanColumn_Detailed",
}


def log(m):
    print("[gap] " + m)


log("=== local bounds (pivot check) ===")
for name, path in PIECES.items():
    mesh = unreal.EditorAssetLibrary.load_asset(path)
    if not mesh:
        log("%s LOAD FAILED" % name)
        continue
    bb = mesh.get_bounds()
    o, e = bb.origin, bb.box_extent
    log("%-30s local origin z=%8.2f extent z=%7.2f  -> z %.1f .. %.1f   r %.1f" % (
        name, o.z, e.z, o.z - e.z, o.z + e.z, e.x))

log("=== level actors ===")
sub = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
sub.load_level(LEVEL)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
rows = []
for a in actors:
    label = a.get_actor_label()
    if not label.startswith("RomanPavilion2"):
        continue
    loc = a.get_actor_location()
    scale = a.get_actor_scale3d()
    mesh = a.static_mesh_component.static_mesh
    bb = mesh.get_bounds() if mesh else None
    zmin = loc.z + (bb.origin.z - bb.box_extent.z) * scale.z if bb else 0.0
    zmax = loc.z + (bb.origin.z + bb.box_extent.z) * scale.z if bb else 0.0
    rows.append((label, loc, scale, mesh.get_name() if mesh else "None", zmin, zmax))

for label, loc, scale, mesh_name, zmin, zmax in sorted(rows, key=lambda r: r[4]):
    log("%-26s loc=(%.0f,%.0f,%.0f) scale=(%.2f,%.2f,%.2f) %-28s spans z %.1f .. %.1f" % (
        label, loc.x, loc.y, loc.z, scale.x, scale.y, scale.z, mesh_name, zmin, zmax))

log("=== assembled stack ===")
stack = sorted(set((round(r[4], 1), round(r[5], 1), r[3]) for r in rows))
for zmin, zmax, mesh_name in stack:
    log("  %8.1f .. %8.1f   %s" % (zmin, zmax, mesh_name))
top_of_columns = max([r[5] for r in rows if r[3] == "SM_RomanColumn_Detailed"], default=None)
bottom_of_dome = min([r[4] for r in rows if r[3] == "SM_RomanPavilionDome_20"], default=None)
bottom_of_arch = min([r[4] for r in rows if r[3] == "SM_RomanPavilionArch_20"], default=None)
log("column tops z=%s, arch bottom z=%s, dome bottom z=%s" % (top_of_columns, bottom_of_arch, bottom_of_dome))
if top_of_columns is not None and bottom_of_dome is not None:
    log("column-top -> dome gap: %.1f cm (entablature is %.1f cm tall)" % (
        bottom_of_dome - top_of_columns, (bottom_of_arch and 0) or 80.0))
log("RESULT: DONE")
