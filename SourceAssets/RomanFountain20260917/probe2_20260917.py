"""Probe round 2: fix the round-1 mistakes (world handle, registry API, MEL surface, slot test with polling)."""

import time

import unreal

SV = unreal.ModelingService

print("[p2] MaterialEditingLibrary surface:")
mel = unreal.MaterialEditingLibrary
print("   ", sorted([n for n in dir(mel) if not n.startswith("_")]))

# ---------------------------------------------------------------- world
try:
    sub = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    w = sub.get_editor_world()
    print("[p2] world name=%s path=%s" % (w.get_name(), w.get_path_name()))
except Exception as exc:  # noqa: BLE001
    w = None
    print("[p2] world failed: %s" % exc)

# ---------------------------------------------------------------- water materials via registry
try:
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    mats = reg.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "Material"), True)
    hits = []
    total = 0
    for a in mats:
        total += 1
        nm = str(a.package_name).lower()
        if any(k in nm for k in ("water", "lake", "ocean", "river", "puddle")):
            hits.append(str(a.package_name))
    print("[p2] materials=%d water-ish=%d" % (total, len(hits)))
    for h in hits[:25]:
        print("   ", h)
except Exception as exc:  # noqa: BLE001
    print("[p2] registry failed: %s" % exc)

# ---------------------------------------------------------------- ground traces
if w is not None:
    for (x, y) in ((1350.0, 550.0), (900.0, 500.0), (1800.0, 500.0), (1350.0, -400.0)):
        try:
            hit = unreal.SystemLibrary.line_trace_single(
                w, unreal.Vector(x, y, 500.0), unreal.Vector(x, y, -300.0),
                unreal.TraceTypeQuery.TraceTypeQuery_Visibility, False, [], False, 0.0)
            t = hit.to_tuple()
            # (blocking, initial_overlap, time, distance, ...) -> ground z = 500 - distance
            print("[p2] trace (%.0f,%.0f) blocking=%s dist=%s z_ground=%.1f" % (
                x, y, t[0], t[3], 500.0 - t[3] if t[0] else float("nan")))
        except Exception as exc:  # noqa: BLE001
            print("[p2] trace failed: %s" % exc)
            break

# ---------------------------------------------------------------- actors near site
try:
    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = actor_sub.get_all_level_actors()
    print("[p2] total level actors=%d" % len(actors))
    near = []
    for a in actors:
        loc = a.get_actor_location()
        if -1000.0 < loc.x < 2400.0 and -1100.0 < loc.y < 1100.0:
            near.append("%s @(%d,%d,%d)" % (a.get_class().get_name(), loc.x, loc.y, loc.z))
    print("[p2] actors near pavilion site: %d" % len(near))
    for n in near[:50]:
        print("   ", n)
except Exception as exc:  # noqa: BLE001
    print("[p2] actor scan failed: %s" % exc)

# ---------------------------------------------------------------- slot test with polling
DIR = "/Game/Props/RomanFountain20260917"
try:
    if not unreal.EditorAssetLibrary.does_directory_exist(DIR):
        unreal.EditorAssetLibrary.make_directory(DIR)
    t = SV.create_mesh().handle
    tr = unreal.Transform()
    tr.translation = unreal.Vector(0, 0, 0)
    tr.scale3d = unreal.Vector(1, 1, 1)
    SV.append_cylinder(t, tr, 40.0, 10.0, 24, 0, True, "Base", 0)
    SV.append_cylinder(t, tr, 20.0, 10.0, 24, 0, True, "Base", 1)
    SV.auto_uv(t, "XAtlas", 0)
    r = SV.save_mesh_to_static_mesh(t, DIR + "/SM_ProbeSlots", True, True, False, True)
    print("[p2] scratch save success=%s msg=%s" % (r.success, r.message))
    SV.release_mesh(t)
    m = None
    for _ in range(40):
        m = unreal.EditorAssetLibrary.load_asset(DIR + "/SM_ProbeSlots")
        if m:
            break
        time.sleep(0.25)
    if m:
        slots = m.get_editor_property("static_materials")
        print("[p2] slots=%d names=%s" % (len(slots), [s.get_editor_property("material_slot_name") for s in slots]))
        unreal.EditorAssetLibrary.delete_asset(DIR + "/SM_ProbeSlots")
        print("[p2] scratch deleted")
    else:
        print("[p2] scratch never loadable")
except Exception as exc:  # noqa: BLE001
    print("[p2] slot test failed: %s" % exc)

print("[p2] DONE")
