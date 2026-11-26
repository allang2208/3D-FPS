"""Read back what L_CyberpunkApartment actually contains after the rebuild.

Reports actor inventory, per-actor collision, traversal tags, floor heights and
the mesh-level trace flags, straight out of the saved packages. It does not
run physics -- UnrealEditor-Cmd has no physics scene, so collision behaviour
still has to be confirmed in PIE. This only proves the data is what we meant.

Writes Saved/_rebuild_verify.json.
"""
import json

import unreal

MAP = "/Game/GameMaps/L_CyberpunkApartment"
BASE = "/Game/Props/CyberpunkApartment20261020/CyberpunkApartment/StaticMeshes"
REPORT = r"D:\FPS3D\FPSGAME\Saved\_rebuild_verify.json"

out = {"actors": [], "playerstart": None, "mesh_flags": {}, "errors": [],
       "counts": {}}


def bbox_world(actor):
    try:
        b = actor.static_mesh_component.get_editor_property("static_mesh").get_bounding_box()
    except Exception:                    # noqa: BLE001
        return None
    loc = actor.get_actor_location()
    sc = actor.get_actor_scale3d()
    return [round(b.min.x * sc.x + loc.x, 1), round(b.min.y * sc.y + loc.y, 1),
            round(b.min.z * sc.z + loc.z, 1), round(b.max.x * sc.x + loc.x, 1),
            round(b.max.y * sc.y + loc.y, 1), round(b.max.z * sc.z + loc.z, 1)]


try:
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    les.load_level(MAP)

    counts = {}
    for a in eas.get_all_level_actors():
        cls = a.get_class().get_name()
        counts[cls] = counts.get(cls, 0) + 1
        lbl = str(a.get_actor_label())
        loc = a.get_actor_location()
        entry = {"label": lbl, "class": cls,
                 "loc": [round(loc.x, 1), round(loc.y, 1), round(loc.z, 1)]}
        if isinstance(a, unreal.StaticMeshActor):
            smc = a.static_mesh_component
            m = smc.get_editor_property("static_mesh")
            entry["mesh"] = m.get_name() if m else None
            entry["collision"] = str(smc.get_collision_enabled()).split(".")[-1].split(":")[0]
            entry["profile"] = str(smc.get_collision_profile_name())
            entry["visible"] = bool(smc.is_visible())
            entry["tags"] = [str(t) for t in smc.get_editor_property("component_tags")]
            entry["actor_tags"] = [str(t) for t in a.tags]
            sc = a.get_actor_scale3d()
            entry["scale"] = [round(sc.x, 2), round(sc.y, 2), round(sc.z, 2)]
            bb = bbox_world(a)
            if bb:
                entry["world_bbox"] = bb
        if isinstance(a, unreal.PlayerStart):
            r = a.get_actor_rotation()
            out["playerstart"] = {"loc": entry["loc"], "yaw": round(r.yaw, 1)}
        out["actors"].append(entry)
    out["counts"] = counts

    # mesh-level trace flags for the architecture set
    for name in ("S_walls", "S_floors", "S_plate", "S_balcony",
                 "S_balcony_glass", "S_glazing", "S_doors", "S_facade",
                 "S_joinery", "CITY_blocks", "LIV_furniture"):
        try:
            m = unreal.EditorAssetLibrary.load_asset("%s/%s.%s" % (BASE, name, name))
            if m is None:
                out["mesh_flags"][name] = "MISSING"
                continue
            body = m.get_editor_property("body_setup")
            flag = str(body.get_editor_property("collision_trace_flag"))
            # KAggregateGeom exposes the primitive arrays through
            # get_editor_property, not as direct attributes.
            agg = body.get_editor_property("agg_geom")
            convex = agg.get_editor_property("convex_elems") if agg else None
            boxes = agg.get_editor_property("box_elems") if agg else None
            out["mesh_flags"][name] = {
                "flag": flag.split(".")[-1].split(":")[0],
                "convex": len(convex) if convex is not None else "n/a",
                "box": len(boxes) if boxes is not None else "n/a",
            }
        except Exception as exc:          # noqa: BLE001
            out["mesh_flags"][name] = "ERR " + str(exc)

except Exception as exc:                  # noqa: BLE001
    out["errors"].append("%s: %s" % (type(exc).__name__, exc))

with open(REPORT, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=1)
unreal.log("REBUILD_VERIFY_WRITTEN")
