"""Build an entablature and lay out the colonnade in the home scene (DayNight_Lighting).

Reuses the actor placed earlier as column 1 (swapped to the detailed mesh) so no stray
column is left behind, then saves the level.
"""

import unreal

SV = unreal.ModelingService
DIR = "/Game/Props/RomanColumn20260915"
COLUMN = DIR + "/SM_RomanColumn_Detailed"
ENTAB = DIR + "/SM_Colonnade_Entablature"
MAT = DIR + "/M_Plaster_Detailed"

COUNT = 6
SPACING = 300.0
BASE_X = 600.0
BASE_Y = 600.0
COLUMN_TOP = 265.0


def tf(x, y, z):
    t = unreal.Transform()
    t.translation = unreal.Vector(x, y, z)
    t.rotation = unreal.Rotator(0.0, 0.0, 0.0).quaternion()
    t.scale3d = unreal.Vector(1.0, 1.0, 1.0)
    return t


# ------------------------------------------------------------- entablature mesh
span = SPACING * (COUNT - 1) + 120.0
beam = SV.create_mesh().handle
print("[colonnade] entablature span=%.1f" % span)
print("[colonnade] architrave", SV.append_box(beam, tf(0, 0, 0), span, 68.0, 16.0, 0, 0, 0, "Base", 0).success)
print("[colonnade] frieze", SV.append_box(beam, tf(0, 0, 16.0), span - 8.0, 64.0, 14.0, 0, 0, 0, "Base", 0).success)
print("[colonnade] cornice", SV.append_box(beam, tf(0, 0, 30.0), span + 12.0, 76.0, 9.0, 0, 0, 0, "Base", 0).success)
SV.auto_uv(beam, "XAtlas", 0)
unreal.EditorAssetLibrary.make_directory(DIR)
print("[colonnade] save", SV.save_mesh_to_static_mesh(beam, ENTAB, True, True, False, True).success)
print("[colonnade] material", SV.set_asset_materials(ENTAB, MAT, True).success)
SV.release_mesh(beam)

# ---------------------------------------------------------------- place actors
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = sub.get_all_level_actors()

column_asset = unreal.EditorAssetLibrary.load_asset(COLUMN)
material = unreal.EditorAssetLibrary.load_asset(MAT)

first = next((a for a in actors if a.get_actor_label() == "RomanColumn_Home"), None)
placed = []

if first:
    first.set_actor_label("Colonnade_C01")
    first.set_actor_location(unreal.Vector(BASE_X, BASE_Y, 0.0), False, False)
    comp = first.static_mesh_component
    comp.set_editor_property("static_mesh", column_asset)
    comp.set_material(0, material)
    placed.append("Colonnade_C01")

start_index = 2 if first else 1
for index in range(start_index, COUNT + 1):
    x = BASE_X + SPACING * (index - 1)
    result = SV.spawn_static_mesh_actor(COLUMN, tf(x, BASE_Y, 0.0), "Colonnade_C%02d" % index)
    if getattr(result, "success", False):
        placed.append("Colonnade_C%02d" % index)
    else:
        print("[colonnade] spawn C%02d failed: %s" % (index, getattr(result, "message", "")))

center_x = BASE_X + SPACING * (COUNT - 1) / 2.0
top = SV.spawn_static_mesh_actor(ENTAB, tf(center_x, BASE_Y, COLUMN_TOP), "Colonnade_Entablature")
print("[colonnade] entablature spawn=%s" % getattr(top, "success", None))

print("[colonnade] placed: %s" % ", ".join(placed))
print("[colonnade] actor count: %d -> %d" % (len(actors), len(sub.get_all_level_actors())))

try:
    saved = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception:
    saved = unreal.EditorLevelLibrary.save_current_level()
print("[colonnade] level saved: %s" % saved)
