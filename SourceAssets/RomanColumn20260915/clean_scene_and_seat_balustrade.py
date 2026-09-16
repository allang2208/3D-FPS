"""Two fixes requested by the user.

1. Remove the traversal test obstacles (the coloured blocks and their signs).
2. Seat the balustrade on the marble floor: add a continuous plinth strip, put the balusters on
   top of it and drop the floating bottom rail.
"""

import time

import unreal

SV = unreal.ModelingService
DIR = "/Game/Props/RomanColumn20260915"
PLINTH = DIR + "/SM_Balustrade_Plinth"
PLASTER = DIR + "/M_Plaster_Detailed"
FLOOR_ACTOR = "MarbleFloor_Colonnade"
REMOVE_PREFIXES = ("TraversalTest",)

LOG = []


def log(message):
    print("[scene] " + message)


def tf(x=0.0, y=0.0, z=0.0):
    t = unreal.Transform()
    t.translation = unreal.Vector(x, y, z)
    t.rotation = unreal.Rotator(0.0, 0.0, 0.0).quaternion()
    t.scale3d = unreal.Vector(1.0, 1.0, 1.0)
    return t


def do(label, result):
    ok = getattr(result, "success", None)
    msg = getattr(result, "message", "")
    LOG.append((label, ok, msg))
    log("%-22s %s %s" % (label, ok, msg))
    return result


def wait_for_asset(path, timeout=20.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        asset = unreal.EditorAssetLibrary.load_asset(path)
        if asset:
            return asset
        time.sleep(0.3)
    return None


sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = sub.get_all_level_actors()

# ------------------------------------------------- 1. remove test obstacles
victims = []
for actor in actors:
    label = actor.get_actor_label()
    if any(label.startswith(prefix) for prefix in REMOVE_PREFIXES):
        origin, extent = actor.get_actor_bounds(False)
        victims.append((label, actor.get_class().get_name(), extent.x * 2, extent.y * 2, extent.z * 2, actor))

for label, klass, sx, sy, sz, actor in victims:
    log("remove %-26s %-28s size=(%.0f, %.0f, %.0f)" % (label, klass, sx, sy, sz))
for _, _, _, _, _, actor in victims:
    sub.destroy_actor(actor)
log("removed %d test actors" % len(victims))

remaining = [a.get_actor_label() for a in sub.get_all_level_actors()]
log("stair/test actors still present: %s" % ", ".join(sorted(
    n for n in remaining if n.startswith("StairWalk"))))

# --------------------------------------------- 2. seat the balustrade
actors = sub.get_all_level_actors()
floor_actor = next((a for a in actors if a.get_actor_label() == FLOOR_ACTOR), None)
if floor_actor:
    origin, extent = floor_actor.get_actor_bounds(False)
    floor_top = origin.z + extent.z
else:
    floor_top = 0.0
log("marble floor top z = %.2f" % floor_top)

# Continuous plinth strip: 1620 x 30 x 12, sitting directly on the marble.
plinth = SV.create_mesh().handle
SV.append_box(plinth, tf(0, 0, 0), 1620.0, 30.0, 12.0, 0, 0, 0, "Base", 0)
do("plinth_uv", SV.auto_uv(plinth, "XAtlas", 0))
do("plinth_save", SV.save_mesh_to_static_mesh(plinth, PLINTH, True, True, False, True))
SV.release_mesh(plinth)
if wait_for_asset(PLINTH):
    do("plinth_collision", SV.generate_collision(PLINTH, "AlignedBoxes", 1, 25, True))
    do("plinth_material", SV.set_asset_materials(PLINTH, PLASTER, True))

# Drop the floating bottom rail, replace it with the plinth.
for actor in sub.get_all_level_actors():
    if actor.get_actor_label() == "BalustradeRail_Bottom":
        sub.destroy_actor(actor)
        log("removed floating bottom rail")

plinth_z = floor_top
baluster_z = floor_top + 12.0
top_rail_z = baluster_z + 86.0

spawn = SV.spawn_static_mesh_actor(PLINTH, tf(1350.0, 930.0, plinth_z), "Balustrade_Plinth")
log("plinth spawn=%s at z=%.1f" % (getattr(spawn, "success", None), plinth_z))

moved = 0
for actor in sub.get_all_level_actors():
    label = actor.get_actor_label()
    if label.startswith("Baluster_"):
        loc = actor.get_actor_location()
        actor.set_actor_location(unreal.Vector(loc.x, loc.y, baluster_z), False, False)
        moved += 1
    elif label == "BalustradeRail_Top":
        loc = actor.get_actor_location()
        actor.set_actor_location(unreal.Vector(loc.x, loc.y, top_rail_z), False, False)
        log("top rail moved to z=%.1f" % top_rail_z)
log("balusters seated at z=%.1f (%d moved)" % (baluster_z, moved))

try:
    saved = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception:
    saved = unreal.EditorLevelLibrary.save_current_level()
log("level saved: %s" % saved)

bad = [entry for entry in LOG if entry[1] is False]
log("steps=%d failed=%d" % (len(LOG), len(bad)))
log("RESULT: " + ("PASS" if not bad else "CHECK"))
