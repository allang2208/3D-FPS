"""Look at the player's build world as it stands now, then test entry at whatever pavilion is
there. Prefab actors spawned by the build system ARE queryable in this process, so a positive
control (a down-trace onto a placed piece) tells us whether the sweeps can be trusted.
"""

import math

import unreal

KEY = "ColdSteelPlayer|DayNight_Lighting"
LEVEL = "/Game/GameMaps/DayNight_Lighting"
R_CAP = 42.0

sub = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
sub.load_level(LEVEL)
world = unreal.EditorLevelLibrary.get_editor_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def log(m):
    print("[bw] " + m)


cls = unreal.load_class(None, "/Script/FPSGAME.VoxelBuildWorld")
bw = actors.spawn_actor_from_class(cls, unreal.Vector(0.0, 0.0, 0.0), unreal.Rotator(0.0, 0.0, 0.0))
log("init=%s blocks=%s prefabs=%s" % (bw.call_method("DebugInitialize", args=(KEY,)),
                                      bw.call_method("BlockCount"), bw.call_method("PrefabCount")))

prefabs = []
for a in actors.get_all_level_actors():
    if a.actor_has_tag("VoxelBuildPrefab"):
        loc = a.get_actor_location()
        prefabs.append((loc.x, loc.y, loc.z, a.get_actor_label()))
prefabs.sort(key=lambda p: (round(p[0]), round(p[1]), p[2]))
log("=== %d prefab actors ===" % len(prefabs))
for x, y, z, label in prefabs:
    log("  (%8.1f, %8.1f, %7.1f)  %s" % (x, y, z, label))


def down(x, y, z0=1500.0, z1=-200.0):
    return unreal.SystemLibrary.line_trace_single(
        world, unreal.Vector(x, y, z0), unreal.Vector(x, y, z1),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY2, False, [], unreal.DrawDebugTrace.NONE, False)


def hit_label(h):
    if not h:
        return "NO HIT"
    try:
        name = h.hit_actor.get_actor_label() if h.hit_actor else "?"
    except AttributeError:
        name = "?"
    try:
        return "%s @ z=%.1f" % (name, h.location.z)
    except AttributeError:
        return name


# positive control on the first prefab we can see, to prove queries answer in this process
control = None
for x, y, z, label in prefabs:
    h = down(x, y)
    if h:
        control = (x, y, label, h)
        break
log("positive control: %s" % ("YES - down-trace onto %s -> %s" % (control[2], hit_label(control[3]))
                              if control else "NO - nothing answers, results unusable"))
if not control:
    bw.destroy_actor()
    log("RESULT: ABORT - build-world pieces do not answer either")
    raise SystemExit(0)

# a pavilion stack shows up as pieces sharing one XY at z = 0 / 20 / 360
stacks = {}
for x, y, z, label in prefabs:
    key = (round(x, 1), round(y, 1))
    stacks.setdefault(key, []).append((z, label))
candidates = [(k, v) for k, v in stacks.items() if len(v) >= 2]
log("=== XY positions with more than one piece (possible pavilion stack) ===")
for (x, y), items in candidates:
    log("  centre (%.0f, %.0f): %s" % (x, y, sorted(round(z) for z, _ in items)))

if not candidates:
    log("no stacked pieces: the pavilion was not built here (or only one piece is placed)")
else:
    gap = 360.0 / 10
    for (cx, cy), items in candidates:
        log("=== bays around (%.0f, %.0f), capsule radius 42 ===" % (cx, cy))
        ok = 0
        for k in range(10):
            ang = math.radians(gap * (k + 0.5))
            blocked = None
            for z in (30.0, 60.0, 96.0, 130.0, 170.0):
                h = unreal.SystemLibrary.sphere_trace_single(
                    world,
                    unreal.Vector(cx + 700.0 * math.cos(ang), cy + 700.0 * math.sin(ang), z),
                    unreal.Vector(cx - 100.0 * math.cos(ang), cy - 100.0 * math.sin(ang), z), R_CAP,
                    unreal.TraceTypeQuery.TRACE_TYPE_QUERY2, False, [], unreal.DrawDebugTrace.NONE, False)
                if h:
                    blocked = "z=%.0f -> %s" % (z, hit_label(h))
                    break
            log("  bay %2d: %s" % (k + 1, blocked or "passable"))
            ok += 1 if not blocked else 0
        log("  passable: %d/10" % ok)
bw.destroy_actor()
log("RESULT: DONE")
