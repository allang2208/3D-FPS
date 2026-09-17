"""Map what blocks walking out of the player's build-world pavilion.

Enumerates the prefab actors in the level (the build system spawns AVoxelBuildPrefabActor for
each placed piece), then fans sphere sweeps (player capsule radius 42, at the three heights the
capsule occupies) from the pavilion centre outwards and names the first blocker per direction.
"""

import math

import unreal

KEY = "ColdSteelPlayer|DayNight_Lighting"
R_CAP = 42.0
SWEEP_Z = (42.0, 96.0, 150.0)
N_DIR = 36

sub = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
sub.load_level("/Game/GameMaps/DayNight_Lighting")
world = unreal.EditorLevelLibrary.get_editor_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def log(m):
    print("[map] " + m)


cls = unreal.load_class(None, "/Script/FPSGAME.VoxelBuildWorld")
bw = actors.spawn_actor_from_class(cls, unreal.Vector(0.0, 0.0, 0.0), unreal.Rotator(0.0, 0.0, 0.0))
log("init=%s blocks=%s prefabs=%s" % (bw.call_method("DebugInitialize", args=(KEY,)),
                                      bw.call_method("BlockCount"), bw.call_method("PrefabCount")))

pieces = []
for a in actors.get_all_level_actors():
    if not a.actor_has_tag("VoxelBuildPrefab"):
        continue
    mesh = "?"
    try:
        m = a.mesh_component.static_mesh
        mesh = m.get_name() if m else "(no mesh)"
    except Exception:
        pass
    loc = a.get_actor_location()
    pieces.append((mesh, loc))
    log("PREFAB tag mesh=%-34s loc=(%.0f, %.0f, %.0f) label=%s" % (
        mesh, loc.x, loc.y, loc.z, a.get_actor_label()))

log("=== block footprint (top view, 20 cm cells) ===")
hist = {}
top = {}
R = 60
for cz in range(0, 25):
    for cy in range(-R, R + 1):
        for cx in range(-R, R + 1):
            mat = str(bw.call_method("MaterialAt", args=(unreal.IntVector(cx, cy, cz),)))
            if mat != "None":
                hist[mat] = hist.get(mat, 0) + 1
                k = (cx, cy)
                if k not in top or cz > top[k][0]:
                    top[k] = (cz, mat)
log("voxel histogram: %s" % hist)
xs = sorted(k[0] for k in top) or [0]
ys = sorted(k[1] for k in top) or [0]
log("occupied x %d..%d  y %d..%d" % (xs[0], xs[-1], ys[0], ys[-1]))
for cy in range(ys[0], ys[-1] + 1, 1):
    row = ""
    for cx in range(xs[0], xs[-1] + 1):
        t = top.get((cx, cy))
        row += (t[1][0].upper() if t else ".")
    log("  y=%4d |%s|" % (cy, row))

pav = [(m, l) for m, l in pieces if "RomanPavilion" in m]
if not pav:
    log("no pavilion prefabs in the build world")
else:
    cx = sum(l.x for _, l in pav) / len(pav)
    cy = sum(l.y for _, l in pav) / len(pav)
    log("pavilion pieces=%d centre=(%.0f, %.0f)" % (len(pav), cx, cy))

    def trace(start, end):
        return unreal.SystemLibrary.sphere_trace_single(
            world, unreal.Vector(*start), unreal.Vector(*end), R_CAP,
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY2, False, [], unreal.DrawDebugTrace.NONE, False)

    def label(hit):
        if not hit:
            return "clear to 900"
        try:
            name = hit.hit_actor.get_actor_label() if hit.hit_actor else "?"
        except AttributeError:
            name = "?"
        z = None
        for attr in ("location", "impact_point"):
            try:
                z = getattr(hit, attr).z
                break
            except AttributeError:
                continue
        return "%s @ r=%s z=%s" % (name, "?", "%.0f" % z if z is not None else "?")
        return name

    log("=== sweep from centre outward, per direction (radius of first blocker) ===")
    blocked_dirs = 0
    for i in range(N_DIR):
        ang = 2.0 * math.pi * i / N_DIR
        worst = None
        for z in SWEEP_Z:
            start = (cx, cy, z)
            end = (cx + 900.0 * math.cos(ang), cy + 900.0 * math.sin(ang), z)
            hit = trace(start, end)
            if hit:
                # distance from the centre to the blocking point
                d = None
                for attr in ("location", "impact_point"):
                    try:
                        v = getattr(hit, attr)
                        d = math.hypot(v.x - cx, v.y - cy)
                        break
                    except AttributeError:
                        continue
                try:
                    name = hit.hit_actor.get_actor_label() if hit.hit_actor else "?"
                except AttributeError:
                    name = "?"
                worst = (d, name, z)
                break
        if worst:
            blocked_dirs += 1
            log("dir %3.0f deg: blocked at r=%s by %s (z=%.0f)" % (
                math.degrees(ang), "%.0f" % worst[0] if worst[0] is not None else "?", worst[1], worst[2]))
        else:
            log("dir %3.0f deg: open (no hit to 900)" % math.degrees(ang))
    log("directions blocked: %d/%d" % (blocked_dirs, N_DIR))

    log("=== straight down the axis ===")
    for z in (900.0, 760.0, 500.0, 360.0, 280.0, 200.0, 100.0, 5.0):
        hit = unreal.SystemLibrary.line_trace_single(
            world, unreal.Vector(cx, cy, 900.0), unreal.Vector(cx, cy, z),
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY2, False, [], unreal.DrawDebugTrace.NONE, False)
        try:
            name = hit.hit_actor.get_actor_label() if hit and hit.hit_actor else "clear"
        except AttributeError:
            name = "?"
        zz = "?"
        if hit:
            try:
                zz = "%.1f" % getattr(hit, "location").z
            except AttributeError:
                pass
        log("down to z=%6.0f: %s (hit at z=%s)" % (z, name, zz))
bw.destroy_actor()
log("RESULT: DONE")
