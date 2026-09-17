"""Which actors' collision actually occupies the pavilion's interior? sphere_overlap_actors
names them directly — no hit-result fields needed.

Read-only.
"""

import unreal

ORIGIN = (1350.0, -400.0)


def log(m):
    print("[ovl] " + m)


world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def overlaps(x, y, z, radius):
    # signature: (WorldContext, SpherePos, Radius, ObjectTypes, ActorClassFilter, ActorsToIgnore)
    object_types = [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1,
                    unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY2]
    hits = unreal.SystemLibrary.sphere_overlap_actors(
        world, unreal.Vector(x, y, z), radius, object_types, unreal.Actor, [])
    out = []
    for a in hits or []:
        if a is None:
            continue
        try:
            label = a.get_actor_label()
        except Exception:
            label = "?"
        out.append(label)
    return out


log("=== sphere overlap (r=42), point by point ===")
points = [
    ("pavilion centre z=96", (ORIGIN[0], ORIGIN[1], 96.0)),
    ("pavilion centre z=20", (ORIGIN[0], ORIGIN[1], 20.0)),
    ("pavilion centre z=200", (ORIGIN[0], ORIGIN[1], 200.0)),
    ("pavilion centre z=300", (ORIGIN[0], ORIGIN[1], 300.0)),
    ("pavilion centre z=500", (ORIGIN[0], ORIGIN[1], 500.0)),
    ("bay1 mouth r=360 z=96", (ORIGIN[0] + 360.0, ORIGIN[1], 96.0)),
    ("outside r=600 z=96", (ORIGIN[0] + 600.0, ORIGIN[1], 96.0)),
    ("open ground (3000,3000,96)", (3000.0, 3000.0, 96.0)),
]
for name, (x, y, z) in points:
    log("%-28s -> %s" % (name, overlaps(x, y, z, 42.0) or "nothing"))

log("=== same, larger radius 100 ===")
for name, (x, y, z) in points[:6]:
    log("%-28s -> %s" % (name, overlaps(x, y, z, 100.0) or "nothing"))

log("=== all pavilion actors with collision enabled? ===")
for a in sub.get_all_level_actors():
    label = a.get_actor_label()
    if not label.startswith("RomanPavilion2"):
        continue
    try:
        comp = a.static_mesh_component
        enabled = comp.get_collision_enabled()
        profile = comp.get_collision_profile_name()
        log("%-28s collision=%-14s profile=%s" % (label, enabled, profile))
    except Exception as exc:
        log("%-28s collision read failed: %s" % (label, type(exc).__name__))
log("RESULT: DONE")
