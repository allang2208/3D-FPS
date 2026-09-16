"""Place SM_RomanColumn into the home scene (GameMaps/DayNight_Lighting) and save the level.

Placement: on top of the level's `Floor` actor, offset from the player start so it does not
overlap the traversal / stair test props.
"""

import unreal

MESH_PATH = "/Game/Props/RomanColumn20260915/SM_RomanColumn"
LABEL = "RomanColumn_Home"
OFFSET_X = 600.0
OFFSET_Y = 600.0


def editor_world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


world = editor_world()
print("[place] level: %s" % world.get_path_name())

subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = subsystem.get_all_level_actors()
before = len(actors)

floor = next((a for a in actors if a.get_actor_label() == "Floor"), None)
start = next((a for a in actors if isinstance(a, unreal.PlayerStart)), None)
print("[place] floor found: %s" % (floor is not None))
print("[place] player start: %s" % (start.get_actor_location() if start else None))

ground_z = 0.0
if floor:
    origin, extent = floor.get_actor_bounds(False)
    print("[place] floor origin=%s extent=%s" % (origin, extent))
    ground_z = origin.z + extent.z
elif start:
    ground_z = start.get_actor_location().z
print("[place] ground z = %.2f" % ground_z)

base = start.get_actor_location() if start else unreal.Vector(0, 0, 0)
target = unreal.Vector(base.x + OFFSET_X, base.y + OFFSET_Y, ground_z)

transform = unreal.Transform()
transform.translation = target
transform.rotation = unreal.Rotator(0.0, 0.0, 0.0).quaternion()
transform.scale3d = unreal.Vector(1.0, 1.0, 1.0)

result = unreal.ModelingService.spawn_static_mesh_actor(MESH_PATH, transform, LABEL)
print("[place] spawn success=%s message=%s" % (getattr(result, "success", None), getattr(result, "message", "")))

after_actors = subsystem.get_all_level_actors()
placed = next((a for a in after_actors if a.get_actor_label() == LABEL), None)
print("[place] actor count %d -> %d" % (before, len(after_actors)))
if placed:
    origin, extent = placed.get_actor_bounds(False)
    print("[place] %s location=%s bounds origin=%s extent=%s" % (
        LABEL, placed.get_actor_location(), origin, extent))

try:
    saved = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception:
    saved = unreal.EditorLevelLibrary.save_current_level()
print("[place] level saved: %s" % saved)
