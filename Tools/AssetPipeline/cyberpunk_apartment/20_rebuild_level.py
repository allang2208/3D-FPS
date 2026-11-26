"""Rebuild L_CyberpunkApartment from the measured geometry.

Eleven additive patch rounds produced four stacked collision slabs, an
invisible landing ledge 152 m in the air, and collision switched off on the
glazing. This script replaces all of that with one consistent structure
built from facts measured out of the source glTF
(`00_gltf_geometry.py` -> `Saved/_gltf_geometry.json`).

Measured facts, UE centimetres
-----------------------------
  S_floors  11 room quads at z=+0.2, balcony deck at z=-3.0, 24 one-sided tris
  S_plate   structural slab, top face z=0.0, bottom z=-34
  S_glazing fixed panes stop at x=690/705, slider starts at 805 -> a 100 cm
            opening at x 705..805
  S_facade  one mullion, 8.5 cm wide, at x 757.8..766.2 -> splits that opening in two
  S_balcony glass railing, 2 tris at y=279, z 4..106; handrail top z=112.5
  S_doors   five baked leaves swung to 58/22/-34/12/-46 deg, physically
            across every doorway (measured: 104/105 cm of the entry opening)

What this script does
---------------------
  1. deletes every historical patch actor
  2. one collision slab per room at the real floor height, balcony deck included
  3. a real 3.2 cm threshold step so the deck drop is walkable
  4. railing tagged Traversal.GuardrailDrop with real collision, so the
     traversal rules can see it (falls stay allowed -- no fake ledge)
  5. baked door leaves lose collision; the project's AColdSteelSlidingDoor
     takes over on corrected UE coordinates
  6. PlayerStart on the living-room floor; lights moved indoors;
     CITY_* backdrop loses collision

Commandlet:
  UnrealEditor-Cmd.exe FPSGAME.uproject -run=pythonscript \
    -script=Tools/AssetPipeline/cyberpunk_apartment/20_rebuild_level.py \
    -unattended -nop4 -nosplash -NullRHI
"""
import json

import unreal

BASE = "/Game/Props/CyberpunkApartment20261020/CyberpunkApartment"
MESH_DIR = BASE + "/StaticMeshes"
MAP = "/Game/GameMaps/L_CyberpunkApartment"
CUBE = "/Engine/BasicShapes/Cube.Cube"
DOOR_CLASS = "/Script/FPSGAME.ColdSteelSlidingDoor"
REPORT = r"D:\FPS3D\FPSGAME\Saved\_rebuild_20261020.json"

FLOOR_TOP = 0.2      # S_floors room quads
DECK_TOP = -3.0      # S_floors balcony deck
SLAB = 40.0          # collision slab thickness (cm)

log = {"removed": [], "floors": [], "tags": [], "collision": {},
       "doors": [], "lights": [], "spawn": None, "errors": [], "notes": []}


def note(msg):
    log["notes"].append(msg)


def spawn_cube(eas, mesh, label, centre, size, *, block=True, visible=False,
               tag=None):
    """An engine cube used as an exact collision block.

    /Engine/BasicShapes/Cube has engine-native box collision, which stays
    exact under non-uniform scale -- unlike collision generated from imported
    triangle data, which is what kept failing here.
    """
    a = eas.spawn_actor_from_class(unreal.StaticMeshActor,
                                   unreal.Vector(*centre),
                                   unreal.Rotator(0, 0, 0))
    a.set_actor_label(label)
    smc = a.static_mesh_component
    smc.set_editor_property("static_mesh", mesh)
    smc.set_mobility(unreal.ComponentMobility.STATIC)
    a.set_actor_scale3d(unreal.Vector(size[0] / 100.0, size[1] / 100.0,
                                      size[2] / 100.0))
    if block:
        smc.set_collision_profile_name(unreal.Name("BlockAll"))
        smc.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    else:
        smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    smc.set_editor_property("cast_shadow", False)
    smc.set_visibility(visible, True)
    if tag:
        tags = [str(t) for t in smc.get_editor_property("component_tags")]
        if tag not in tags:
            comp_tags = list(smc.get_editor_property("component_tags"))
            comp_tags.append(unreal.Name(tag))
            smc.set_editor_property("component_tags", comp_tags)
        if tag not in [str(t) for t in a.tags]:
            a.tags.append(unreal.Name(tag))
        log["tags"].append({"actor": label, "tag": tag})
    return a


def component_tags(comp):
    return [str(t) for t in comp.get_editor_property("component_tags")]


def set_tags(actor, tag):
    for comp in actor.get_components_by_class(unreal.PrimitiveComponent):
        if tag not in component_tags(comp):
            tags = list(comp.get_editor_property("component_tags"))
            tags.append(unreal.Name(tag))
            comp.set_editor_property("component_tags", tags)
    if tag not in [str(t) for t in actor.tags]:
        actor.tags.append(unreal.Name(tag))


def main():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    les.load_level(MAP)

    mesh = unreal.EditorAssetLibrary.load_asset(CUBE)
    if mesh is None:
        raise RuntimeError("engine cube missing")

    # ---- 1. remove every patch from the previous rounds -------------------
    for a in list(eas.get_all_level_actors()):
        lbl = str(a.get_actor_label())
        if (lbl in ("CollisionFloor", "SlabFloor", "BlockFloor_Apartment",
                    "BalconyLedge")
                or lbl.startswith("FloorTile_")
                or lbl.startswith("Floor_")
                or lbl.startswith("Threshold_")
                or lbl.startswith("Rail_")):
            log["removed"].append(lbl)
            eas.destroy_actor(a)
    note("removed %d patch actors" % len(log["removed"]))

    # ---- 2. floor slabs, top face at the real walkable height ------------
    rooms = [
        ("living",   396.0, 1128.0,  -540.0,   -12.0),
        ("master",    12.0,  384.0,  -540.0,   -12.0),
        ("bed2",    1140.0, 1588.0,  -540.0,   -12.0),
        ("bed3",    1140.0, 1588.0, -1088.0,  -552.0),
        ("corridor",  12.0, 1128.0,  -672.0,  -552.0),
        ("utility",   12.0,  272.0,  -808.0,  -672.0),
        ("bath2",     12.0,  272.0, -1088.0,  -820.0),
        ("bath1",    284.0,  468.0, -1088.0,  -820.0),
        ("utility2", 284.0,  468.0,  -808.0,  -684.0),
        ("kitchen",  480.0,  864.0, -1088.0,  -684.0),
        ("foyer",    876.0, 1128.0, -1088.0,  -684.0),
    ]
    for (name, x0, x1, y0, y1) in rooms:
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        w, d = (x1 - x0) + 8.0, (y1 - y0) + 8.0     # lap 4 cm under the walls
        spawn_cube(eas, mesh, "Floor_%s" % name,
                   (cx, cy, FLOOR_TOP - SLAB / 2.0), (w, d, SLAB))
        log["floors"].append({"room": name, "top": FLOOR_TOP,
                              "x": [x0, x1], "y": [y0, y1]})

    # balcony deck: S_balcony slab spans x 398..1130, y 2..280 at z -7..-3,
    # so the deck surface is real geometry; give it a matching block.
    spawn_cube(eas, mesh, "Floor_balcony",
               (764.0, 141.0, DECK_TOP - SLAB / 2.0), (740.0, 282.0, SLAB))
    log["floors"].append({"room": "balcony", "top": DECK_TOP})

    # ---- 3. threshold: the 3.2 cm deck drop becomes a real step ----------
    spawn_cube(eas, mesh, "Threshold_Balcony",
               (757.0, 6.0, DECK_TOP + (FLOOR_TOP - DECK_TOP) / 2.0),
               (440.0, 30.0, FLOOR_TOP - DECK_TOP))
    note("balcony threshold: flat 3.2 cm sill at the sliding door, no lip")

    # ---- 4. railing: real collision + the traversal tag ------------------
    # S_balcony_glass is 2 triangles at y=279, z 4..106. A two-triangle sheet
    # is far too thin for the traversal's nine-point landing support test, so
    # it gets a solid 8 cm block along the same line, tagged as a guardrail.
    # The tag is what makes FindTarget accept the obstacle at all
    # (FPSTraversalComponent.cpp: IsAuthoredGuardrail).
    spawn_cube(eas, mesh, "Rail_BalconyCollision",
               (764.0, 277.5, (4.0 + 112.5) / 2.0),
               (716.0, 8.0, 112.5 - 4.0), tag="Traversal.GuardrailDrop")

    # the visible railing meshes keep collision too, so the handrail top is
    # grabbable; both carry the tag.
    for a in eas.get_all_level_actors():
        lbl = str(a.get_actor_label())
        if lbl in ("S_balcony", "S_balcony_glass"):
            smc = a.static_mesh_component
            smc.set_collision_profile_name(unreal.Name("BlockAll"))
            smc.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
            set_tags(a, "Traversal.GuardrailDrop")
            log["tags"].append({"actor": lbl, "tag": "Traversal.GuardrailDrop"})

    # ---- 5. mesh collision policy ----------------------------------------
    # Architecture traces its triangles. Decoration that used to wall the
    # player in (signs, cables, curtains, graffiti, wires, the baked door
    # leaves) stops colliding.
    COMPLEX = ["S_plate", "S_walls", "S_floors", "S_ceiling", "S_facade",
               "S_balcony", "S_balcony_glass", "S_glazing", "S_trim",
               "S_joinery", "S_finish", "LIV_furniture", "KIT_run",
               "KIT_dining", "B2_room", "B3_room", "MST_room", "BA1_room",
               "BA2_room", "UTL_room", "FOY_room", "COR_room"]
    NOCOLLIDE = ["S_doors", "LIV_sign_01", "LIV_sign_24H",
                 "LIV_sign_NOODLE__", "MST_sign", "B2_sign", "B3_sign",
                 "FOY_sign", "BAL_sign", "BAL_holo", "DET_graffiti",
                 "DET_wires", "LIV_cables", "LIV_curtains", "LIV_micro",
                 "LIV_micro_clutter", "LIV_clutter", "LIV_plants",
                 "LIV_art", "LIV_ceiling", "KIT_pendants", "KIT_micro",
                 "KIT_micro_table", "KIT_clutter", "KIT_light",
                 "DET_ceiling_services", "DET_practicals", "DET_wall_greeble",
                 "DET_facade_out", "DET_floor", "COR_micro", "COR_clutter",
                 "B2_micro", "B2_clutter", "B3_micro", "B3_clutter",
                 "MST_micro", "MST_clutter", "MST_art", "BA1_micro",
                 "BA1_clutter", "BA2_micro", "BA2_clutter", "UTL_clutter",
                 "FOY_micro", "FOY_clutter", "BAL_detail", "BAL_furniture",
                 "BAL_micro",
                 "CITY_blocks", "CITY_bridges", "CITY_fog", "CITY_ground",
                 "CITY_horizon", "CITY_our_tower", "CITY_signs",
                 "CITY_traffic"]

    archive_of = {}
    for a in eas.get_all_level_actors():
        if isinstance(a, unreal.StaticMeshActor):
            m = a.static_mesh_component.get_editor_property("static_mesh")
            if m:
                archive_of[str(a.get_actor_label())] = m

    for name in COMPLEX + NOCOLLIDE:
        path = "%s/%s.%s" % (MESH_DIR, name, name)
        if not unreal.EditorAssetLibrary.does_asset_exist(path):
            log["errors"].append("missing mesh asset: " + name)
            continue
        try:
            m = unreal.EditorAssetLibrary.load_asset(path)
            body = m.get_editor_property("body_setup")
            if body is None:
                log["errors"].append("no body setup: " + name)
                continue
            body.set_editor_property(
                "collision_trace_flag",
                unreal.CollisionTraceFlag.CTF_USE_DEFAULT if name in NOCOLLIDE
                else unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
            if name in NOCOLLIDE:
                # Clear the importer's single convex hull as well: with the
                # hull left in place an actor-level BlockAll still blocks on
                # that solid, which is exactly the wall players hit.
                try:
                    body.set_editor_property("agg_geom",
                                             unreal.KAggregateGeom())
                except Exception:           # noqa: BLE001
                    note("could not clear hull on " + name)
            unreal.EditorAssetLibrary.save_loaded_asset(m)
            log["collision"][name] = ("no-collision" if name in NOCOLLIDE
                                      else "complex-as-simple")
        except Exception as exc:            # noqa: BLE001
            log["errors"].append("mesh %s: %s" % (name, exc))

    # ---- 6. actor-level collision ----------------------------------------
    for a in eas.get_all_level_actors():
        if not isinstance(a, unreal.StaticMeshActor):
            continue
        lbl = str(a.get_actor_label())
        smc = a.static_mesh_component
        if lbl.startswith("CITY_") or lbl in NOCOLLIDE:
            smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        elif lbl in COMPLEX:
            smc.set_collision_profile_name(unreal.Name("BlockAll"))
            smc.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)

    # ---- 7. interactive doors on the corrected UE coordinates ------------
    # Wall planes and opening spans measured from S_walls:
    #   entry   y=-1100, x 941..1043        living  y=-546, x 661..959
    #   master  y=-546,  x 153..241         kitchen y=-678, x 531..789
    #   bath2   y=-814,  x 123..201         bath1   y=-814, x 331..409
    #   bed2    x=1134,  y -499..-411       bed3    x=1134, y -847..-759
    #   balcony y=0,     x 705..805
    doors = [
        ("Door_Entry",   992.0, -1100.0,   0.0),
        ("Door_Living",  810.0,  -546.0,   0.0),
        ("Door_Master",  197.0,  -546.0,   0.0),
        ("Door_Kitchen", 660.0,  -678.0,   0.0),
        ("Door_Bath1",   370.0,  -814.0,   0.0),
        ("Door_Bath2",   162.0,  -814.0,   0.0),
        ("Door_Bed2",   1134.0,  -455.0,  90.0),
        ("Door_Bed3",   1134.0,  -803.0,  90.0),
        ("Door_Balcony", 755.0,     0.0,   0.0),
    ]
    for a in list(eas.get_all_level_actors()):
        if str(a.get_actor_label()).startswith("Door_"):
            eas.destroy_actor(a)
    door_cls = unreal.load_class(None, DOOR_CLASS)
    if door_cls is None:
        log["errors"].append("ColdSteelSlidingDoor class not found")
    else:
        for (label, x, y, yaw) in doors:
            a = eas.spawn_actor_from_class(door_cls, unreal.Vector(x, y, 0.0),
                                           unreal.Rotator(0.0, 0.0, yaw))
            if a is None:
                log["errors"].append("%s: spawn returned None" % label)
                continue
            a.set_actor_label(label)
            log["doors"].append({"label": label, "loc": [x, y, 0.0], "yaw": yaw})

    # ---- 8. spawn on the living-room floor, facing the sofa --------------
    for a in eas.get_all_level_actors():
        if isinstance(a, unreal.PlayerStart):
            eas.destroy_actor(a)
    ps = eas.spawn_actor_from_class(unreal.PlayerStart,
                                    unreal.Vector(790.0, -180.0, FLOOR_TOP),
                                    unreal.Rotator(0.0, 0.0, 90.0))
    ps.set_actor_label("PlayerStart_Apartment")
    log["spawn"] = {"loc": [790.0, -180.0, FLOOR_TOP], "yaw": 90.0}

    # ---- 9. lights inside the rooms --------------------------------------
    # The old rig sat at y +110..+950, i.e. beyond the facade, so the room
    # had no light of its own.
    lights = [
        ("L_living_key",  (760.0, -300.0, 280.0), 6000.0, (1.0, 0.886, 0.745)),
        ("L_living_fill", (1040.0, -430.0, 262.0), 2600.0, (0.745, 0.824, 1.0)),
        ("L_corr",        (560.0, -612.0, 285.0), 3200.0, (0.784, 0.902, 1.0)),
        ("L_kitchen",     (672.0, -886.0, 230.0), 3400.0, (1.0, 0.878, 0.729)),
        ("L_master",      (200.0, -276.0, 286.0), 3000.0, (1.0, 0.886, 0.769)),
        ("L_bath",        (376.0, -954.0, 280.0), 2200.0, (0.922, 0.949, 1.0)),
        ("L_foyer",      (1000.0, -886.0, 284.0), 2400.0, (1.0, 0.910, 0.784)),
    ]
    existing = {str(a.get_actor_label()): a
                for a in eas.get_all_level_actors()
                if isinstance(a, unreal.RectLight)}
    for (label, loc, intensity, colour) in lights:
        a = existing.get(label)
        if a is None:
            a = eas.spawn_actor_from_class(unreal.RectLight,
                                           unreal.Vector(*loc),
                                           unreal.Rotator(0.0, -90.0, 0.0))
            a.set_actor_label(label)
        a.set_actor_location(unreal.Vector(*loc), False, False)
        comp = a.get_component_by_class(unreal.LightComponent)
        if comp:
            comp.set_mobility(unreal.ComponentMobility.MOVABLE)
            comp.set_intensity(intensity)
            comp.set_light_color(unreal.LinearColor(colour[0], colour[1],
                                                    colour[2], 1.0))
        log["lights"].append({"label": label, "loc": list(loc)})

    # ---- save ------------------------------------------------------------
    les.save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_packages(
        [unreal.load_package(MAP)], True)
    note("level saved")


try:
    main()
except Exception as exc:                   # noqa: BLE001
    log["errors"].append("%s: %s" % (type(exc).__name__, exc))

with open(REPORT, "w", encoding="utf-8") as fh:
    json.dump(log, fh, indent=1)
unreal.log("REBUILD_20261020_WRITTEN")
