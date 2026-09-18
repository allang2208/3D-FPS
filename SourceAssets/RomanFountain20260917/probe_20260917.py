"""Probe before the fountain build: API signatures, level state, water materials, slot semantics.

Dispatch inside the RUNNING editor:
  python Tools/AssetPipeline/ue_python_exec.py --script SourceAssets/RomanFountain20260917/probe_20260917.py
"""

import unreal

SV = unreal.ModelingService

# ---------------------------------------------------------------- 1. service surface
names = [n for n in dir(SV) if not n.startswith("_")]
interesting = [n for n in names if any(k in n for k in
               ("append", "revolve", "cylinder", "sphere", "disc", "boolean", "uv", "save",
                "collision", "material", "polygroup", "bevel", "displace", "mesh"))]
print("[probe] ModelingService methods (%d shown of %d):" % (len(interesting), len(names)))
for n in sorted(interesting):
    print("   ", n)

print("\n[probe] doc snippets:")
for fn in ("append_revolve_polygon", "append_cylinder", "append_box", "save_mesh_to_static_mesh",
           "set_asset_materials", "generate_collision", "boolean", "auto_uv"):
    f = getattr(SV, fn, None)
    if f:
        print("--- %s%s" % (fn, getattr(f, "__doc__", "") or ""))

mel = unreal.MaterialEditingLibrary
for fn in ("create_material", "set_material_property", "set_material_blend_mode",
           "update_material_asset", "set_material_usage"):
    f = getattr(mel, fn, None)
    if f:
        print("--- MEL.%s%s" % (fn, getattr(f, "__doc__", "") or ""))

# ---------------------------------------------------------------- 2. world / level state
try:
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    print("\n[probe] PIE=%s" % les.is_in_play_in_editor())
except Exception as exc:  # noqa: BLE001
    print("[probe] PIE check failed: %s" % exc)
try:
    world = unreal.EditorLevelLibrary.get_editor_world()
    print("[probe] level=%s path=%s" % (world.get_name(), world.get_path_name()))
except Exception as exc:  # noqa: BLE001
    print("[probe] world query failed: %s" % exc)

# ---------------------------------------------------------------- 3. existing water materials
try:
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    opts = unreal.ARFilter(class_names=["Material"], package_names=["/Game"], recursive_paths=True)
    mats = reg.get_assets_by_filter(opts)
    hits = []
    for a in mats:
        nm = str(a.package_name)
        low = nm.lower()
        if "water" in low or "lake" in low or "ocean" in low or "river" in low:
            hits.append(nm)
    print("\n[probe] water-ish materials: %d" % len(hits))
    for h in hits[:20]:
        print("   ", h)
except Exception as exc:  # noqa: BLE001
    print("[probe] registry search failed: %s" % exc)

# ---------------------------------------------------------------- 4. slot semantics of append_*
DIR = "/Game/Props/RomanFountain20260917"
try:
    if not unreal.EditorAssetLibrary.does_directory_exist(DIR):
        unreal.EditorAssetLibrary.make_directory(DIR)
    t = SV.create_mesh().handle
    tr = unreal.Transform()
    tr.translation = unreal.Vector(0, 0, 0)
    tr.scale3d = unreal.Vector(1, 1, 1)
    SV.append_cylinder(t, tr, 40.0, 10.0, 24, 0, True, "Marble", 0)
    SV.append_cylinder(t, tr, 20.0, 10.0, 24, 0, True, "Water", 1)
    SV.auto_uv(t, "XAtlas", 0)
    scratch = DIR + "/SM_ProbeSlots"
    SV.save_mesh_to_static_mesh(t, scratch, True, True, False, True)
    SV.release_mesh(t)
    m = unreal.EditorAssetLibrary.load_asset(scratch)
    if m:
        slots = m.get_editor_property("static_materials")
        print("\n[probe] two-polygroup mesh -> static_materials slots = %d" % len(slots))
        for s in slots:
            print("    slot name=%s" % s.get_editor_property("material_slot_name"))
        unreal.EditorAssetLibrary.delete_asset(scratch)
        print("[probe] scratch deleted")
    else:
        print("[probe] scratch save FAILED (slot test inconclusive)")
except Exception as exc:  # noqa: BLE001
    print("[probe] slot test failed: %s" % exc)

# ---------------------------------------------------------------- 5. candidate spots
try:
    sub = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    w = sub.get_editor_world()
    for (x, y) in ((1350.0, 550.0), (900.0, 500.0), (1800.0, 500.0)):
        hit = unreal.SystemLibrary.line_trace_single(
            w, unreal.Vector(x, y, 500.0), unreal.Vector(x, y, -200.0),
            unreal.TraceTypeQuery.Visibility, False, [], False, 0.0)
        print("[probe] ground trace (%.0f,%.0f) blocking=%s distance=%s" % (
            x, y, hit.to_tuple()[0], hit.to_tuple()[3]))
    # what stands within 7 m of the primary candidate?
    ov = unreal.SystemLibrary.sphere_overlap_actors(
        w, unreal.Vector(1350.0, 550.0, 100.0), 700.0,
        unreal.ObjectQueryParams().to_tuple() if False else None, None, [])
except Exception as exc:  # noqa: BLE001
    print("[probe] spot probe failed: %s" % exc)

# actors near the candidate, via actor subsystem (works when not in PIE)
try:
    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    near = []
    for a in actor_sub.get_all_level_actors():
        loc = a.get_actor_location()
        if 500.0 < loc.x < 2300.0 and -200.0 < loc.y < 1000.0:
            near.append("%s@(%d,%d,%d)" % (a.get_name(), loc.x, loc.y, loc.z))
    print("[probe] actors in x500..2300 y-200..1000: %d" % len(near))
    for n in near[:40]:
        print("   ", n)
except Exception as exc:  # noqa: BLE001
    print("[probe] actor scan failed: %s" % exc)

print("[probe] DONE")
