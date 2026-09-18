"""Second-process readback: the only accepted evidence that the writes landed on disk.

Loads the fountain asset, the palette and the level fresh from disk in a NEW headless process,
and cross-checks every field the build claimed - plus confirms the pavilion / fence actors are
untouched. Run after build_fountain_20260917.py with the editor closed.
"""

import unreal

DIR = "/Game/Props/RomanFountain20260917"
FULL = DIR + "/SM_RomanFountain_20"
PALETTE = "/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette"
LEVEL = "/Game/GameMaps/DayNight_Lighting"
LOG = []


def log(m):
    print("[vfy] " + m)


def check(label, ok):
    LOG.append((label, bool(ok)))
    log("%-28s %s" % (label, "OK" if ok else "FAIL"))


# ---------------------------------------------------------------- asset
mesh = unreal.load_asset(FULL)
check("asset_loadable", mesh is not None)
if mesh:
    bb = mesh.get_bounds()
    size = (bb.box_extent.x * 2, bb.box_extent.y * 2, bb.box_extent.z * 2)
    check("bbox_960x960x720 (2x)",
          abs(size[0] - 960) < 0.5 and abs(size[1] - 960) < 0.5 and abs(size[2] - 720) < 0.5)
    check("pivot_bottom_center", abs(bb.origin.x) < 0.5 and abs(bb.origin.y) < 0.5
          and abs(bb.origin.z - 360.0) < 0.5)
    tris = mesh.get_num_triangles(0)
    check("tri_count_unchanged_by_scale(~22k)", 19000 <= tris <= 24000)
    log("   tris=%d bbox=%.0fx%.0fx%.0f origin z=%.1f" % (tris, size[0], size[1], size[2], bb.origin.z))
    slots = mesh.get_editor_property("static_materials")
    m0 = str(mesh.get_material(0).get_path_name()) if mesh.get_material(0) else "?"
    m1 = str(mesh.get_material(1).get_path_name()) if len(slots) > 1 and mesh.get_material(1) else "?"
    check("slot0_marble", "RomanStone" in m0)
    check("slot1_water", "Water" in m1)
    log("   water material variant: %s" % ("OPAQUE" if "Opaque" in m1 else m1))
    log("   slot0=%s slot1=%s" % (m0, m1))
    setup = mesh.get_editor_property("body_setup")
    agg = None
    if setup:
        for prop in ("agg_geom", "aggregate_geometry"):
            try:
                agg = setup.get_editor_property(prop)
            except Exception:
                continue
            if agg:
                break
    counts = {}
    if agg:
        for elem in ("box_elems", "convex_elems", "sphere_elems", "sphyl_elems", "taper_elems"):
            try:
                arr = agg.get_editor_property(elem)
                counts[elem.replace("_elems", "")] = len(arr) if arr else 0
            except Exception:
                pass
    flag = setup.get_editor_property("collision_trace_flag") if setup else None
    no_strays = not any(counts.get(k) for k in ("convex", "sphere", "sphyl", "taper"))
    complex_ok = flag == unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE and no_strays
    boxes_ok = bool(counts.get("box")) and no_strays
    check("collision_boxes_or_complex", complex_ok or boxes_ok)
    log("   collision=%s flag=%s" % (counts, flag))
    log("   collision=%s" % counts)

# ---------------------------------------------------------------- palette
pal = unreal.load_asset(PALETTE)
check("palette_loadable", pal is not None)
if pal:
    entries = {str(e.get_editor_property("id")): e for e in (pal.get_editor_property("components") or [])}
    check("palette_count_at_least_13", len(entries) >= 13)  # 2026-09-18: 16 with parallel window entries
    e = entries.get("roman_fountain")
    check("fountain_entry_present", e is not None)
    if e:
        fp = e.get_editor_property("footprint")
        check("fountain_footprint_48_48_36", (fp.x, fp.y, fp.z) == (48, 48, 36))
        check("fountain_group_marble", str(e.get_editor_property("material")) == "marble")
        check("fountain_plain_prefab", not e.get_editor_property("actor_class"))
        surf = e.get_editor_property("surface")
        check("fountain_surface_marble", surf and "RomanStone" in str(surf.get_path_name()))
        em = e.get_editor_property("mesh")
        check("fountain_mesh_linked", em and str(em.get_path_name()).startswith(FULL))
        dn = str(e.get_editor_property("display_name"))
        log("   display_name=%s" % dn)
    # door fields survived the 9-field rewrite
    for did in ("door_wood", "door_stone", "door_marble"):
        d = entries.get(did)
        check("door_intact_" + did, d is not None and bool(d.get_editor_property("actor_class")))

# ---------------------------------------------------------------- level
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
check("level_loadable", les.load_level(LEVEL))
actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
fountain = []
pavilion = 0
fence = 0
doors = 0
for a in actor_sub.get_all_level_actors():
    name = a.get_name()
    label = a.get_actor_label()
    if label == "RomanFountain1" or name.startswith("RomanFountain1"):
        fountain.append(a)
    # prior sessions tagged these via set_actor_label; the internal name stays StaticMeshActor_N
    if label.startswith("RomanPavilion2_") or name.startswith("RomanPavilion2_"):
        pavilion += 1
    if label.startswith("RomanFence_") or name.startswith("RomanFence_"):
        fence += 1
    if "Door" in a.get_class().get_name():
        doors += 1
check("fountain_actor_x1", len(fountain) == 1)
if fountain:
    a = fountain[0]
    loc = a.get_actor_location()
    smc = a.get_component_by_class(unreal.StaticMeshComponent)
    sm = smc.static_mesh if smc else None
    check("fountain_mesh_assigned", sm and str(sm.get_path_name()).startswith(FULL))
    check("fountain_at_1350_-1550", abs(loc.x - 1350.0) < 1.0 and abs(loc.y + 1550.0) < 1.0)
    check("fountain_grounding_z0", abs(loc.z + 360.0) < 1.0)
    m0 = smc.get_material(0)
    m1 = smc.get_material(1)
    check("fountain_actor_materials", m0 and "RomanStone" in str(m0.get_path_name())
          and m1 and "Water" in str(m1.get_path_name()))
    log("   actor=%s loc=(%.0f,%.0f,%.0f)" % (a.get_name(), loc.x, loc.y, loc.z))

# FX jet (2026-09-18): engine FountainLightweight template at the pigna tip
jets = [x for x in actor_sub.get_all_level_actors()
        if x.get_actor_label() == "RomanFountainFX_Jet"]
check("fx_jet_x1", len(jets) == 1)
if jets:
    j = jets[0]
    nc = j.get_component_by_class(unreal.NiagaraComponent)
    check("fx_jet_asset", nc is not None and nc.get_asset() is not None and
          "FountainLightweight" in str(nc.get_asset().get_path_name()))
    pa = j.get_attach_parent_actor()
    check("fx_jet_attached", pa is not None and pa.get_actor_label() == "RomanFountain1")
    jloc = j.get_actor_location()
    check("fx_jet_at_tip", abs(jloc.x - 1350.0) < 1.0 and abs(jloc.y + 1550.0) < 1.0 and
          abs(jloc.z - 720.0) < 1.0)
    log("   jet loc=(%.0f,%.0f,%.0f) scale=%.1f" % (
        jloc.x, jloc.y, jloc.z, j.get_actor_scale3d().x))
check("pavilion_actors_13", pavilion == 13)
check("fence_actors_144", fence == 144)
log("   pavilion=%d fence=%d door-actors=%d" % (pavilion, fence, doors))

bad = [x for x in LOG if x[1] is False]
log("checks=%d failed=%d %s" % (len(LOG), len(bad), [b[0] for b in bad]))
log("RESULT: " + ("PASS" if not bad else "CHECK"))
