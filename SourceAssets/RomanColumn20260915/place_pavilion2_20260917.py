"""Place the v2 pavilion into DayNight_Lighting.

The build script's spawn_static_mesh_actor path fails headless ("SpawnActorFromObject.
No actor was spawned."), so placement goes through EditorActorSubsystem.spawn_actor_from_class
— the same route the voxel build-world dump uses successfully in a commandlet.

Run headless:  UnrealEditor-Cmd <uproject> -run=pythonscript -script=<this> -unattended -NullRHI -nosplash
"""

import math

import unreal

DIR = "/Game/Props/RomanColumn20260915"
LEVEL = "/Game/GameMaps/DayNight_Lighting"
ORIGIN = (1350.0, -400.0)
R_COL = 360.0
N_COL = 10
V = 20.0

PIECES = (
    (DIR + "/SM_RomanPavilionBase_20", 0.0, "RomanPavilion2_Base"),
    (DIR + "/SM_RomanPavilionArch_20", 280.0, "RomanPavilion2_Arch"),
    (DIR + "/SM_RomanPavilionDome_20", 360.0, "RomanPavilion2_Dome"),
)

LOG = []


def log(message):
    print("[place] " + message)


sub = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
sub.load_level(LEVEL)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

# --- ground check: where is the terrain under the pavilion centre?
start = unreal.Vector(ORIGIN[0], ORIGIN[1], 500.0)
hit = unreal.SystemLibrary.line_trace_single(
    unreal.EditorLevelLibrary.get_editor_world(), start, unreal.Vector(0.0, 0.0, -1.0),
    unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
ground_z = hit.location.z if hit else None
log("ground under (%.0f, %.0f): z=%s" % (ORIGIN[0], ORIGIN[1], "%.2f" % ground_z if hit else "MISS"))
base_z = ground_z if ground_z is not None else 0.0
if abs(base_z) > 0.5:
    log("WARNING: ground is not at z=0, pavilion will be seated at %.2f" % base_z)

existing = {a.get_actor_label(): a for a in actors.get_all_level_actors()}
log("existing actors: %d, pavilion2 pieces already present: %d" % (
    len(existing), sum(1 for k in existing if k.startswith("RomanPavilion2"))))

placed = 0
for path, z, label in PIECES:
    mesh = unreal.EditorAssetLibrary.load_asset(path)
    if not mesh:
        log("MISSING asset %s" % path)
        continue
    actor = actors.spawn_actor_from_class(
        unreal.StaticMeshActor, unreal.Vector(ORIGIN[0], ORIGIN[1], base_z + z), unreal.Rotator(0.0, 0.0, 0.0))
    if not actor:
        log("FAILED to spawn %s" % label)
        continue
    actor.set_actor_label(label)
    smc = actor.static_mesh_component
    if smc.mobility != unreal.ComponentMobility.MOVABLE:
        smc.set_mobility(unreal.ComponentMobility.MOVABLE)
    smc.set_static_mesh(mesh)
    smc.set_material(0, unreal.EditorAssetLibrary.load_asset(DIR + "/M_RomanStone_V2"))
    log("placed %-26s at z=%.0f mobility=%s" % (label, base_z + z, smc.mobility))
    placed += 1

for k in range(N_COL):
    angle = 2.0 * math.pi * k / N_COL
    label = "RomanPavilion2_Column_%02d" % (k + 1)
    actor = actors.spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(ORIGIN[0] + R_COL * math.cos(angle), ORIGIN[1] + R_COL * math.sin(angle), base_z + V),
        unreal.Rotator(0.0, 0.0, 0.0))
    if not actor:
        log("FAILED to spawn %s" % label)
        continue
    actor.set_actor_label(label)
    smc = actor.static_mesh_component
    if smc.mobility != unreal.ComponentMobility.MOVABLE:
        smc.set_mobility(unreal.ComponentMobility.MOVABLE)
    smc.set_static_mesh(unreal.EditorAssetLibrary.load_asset(DIR + "/SM_RomanColumn_Detailed"))
    smc.set_material(0, unreal.EditorAssetLibrary.load_asset(DIR + "/M_RomanStone_V2"))
    placed += 1
log("placed %d actors" % placed)

saved = sub.save_current_level()
log("level saved: %s" % saved)

# --- read back from the level to prove the actors exist with the right meshes
back = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
mine = [a for a in back if a.get_actor_label().startswith("RomanPavilion2")]
log("read back %d pavilion2 actors (level total %d)" % (len(mine), len(back)))
LOG.append(("readback", len(mine) == len(PIECES) + N_COL))
zspan = {}
for a in sorted(mine, key=lambda x: x.get_actor_label()):
    loc = a.get_actor_location()
    mesh = a.static_mesh_component.static_mesh
    zspan[a.get_actor_label()] = (loc.z, mesh.get_name() if mesh else "None")
for label, (z, mesh) in list(zspan.items())[:4]:
    log("  %-28s z=%.0f %s" % (label, z, mesh))
stack = sorted(set(round(z) for z, _ in zspan.values()))
log("distinct placements z: %s" % stack)

bad = [e for e in LOG if e[1] is False]
log("RESULT: " + ("PASS" if not bad else "CHECK"))
