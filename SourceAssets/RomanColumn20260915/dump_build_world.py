"""Headless: scan the user's voxel build world occupancy in a fixed window around spawn."""

import unreal

KEY = "ColdSteelPlayer|DayNight_Lighting"
WORLD_cls = unreal.load_class(None, "/Script/FPSGAME.VoxelBuildWorld")


def log(m):
    print("[dump] " + m)


sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
bw = sub.spawn_actor_from_class(WORLD_cls, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
if not bw:
    raise SystemExit("cannot spawn VoxelBuildWorld")

log("initialize=%s" % bw.call_method("DebugInitialize", args=(KEY,)))
log("blocks=%s prefabs=%s" % (bw.call_method("BlockCount"), bw.call_method("PrefabCount")))

hist = {}
top = {}
layers = {}
R = 40
for cz in range(0, 21):
    for cy in range(-R, R + 1):
        for cx in range(-R, R + 1):
            mat = str(bw.call_method("MaterialAt", args=(unreal.IntVector(cx, cy, cz),)))
            if mat != "None":
                hist[mat] = hist.get(mat, 0) + 1
                key = (cx, cy)
                if key not in top or cz > top[key][0]:
                    top[key] = (cz, mat)
                layers.setdefault(cz, set()).add((cx, cy))
log("voxel histogram: %s" % hist)

xs = sorted(set(k[0] for k in top)) or [0]
ys = sorted(set(k[1] for k in top)) or [0]
log("occupied x range %d..%d, y range %d..%d" % (xs[0], xs[-1], ys[0], ys[-1]))
log("per-z block counts: %s" % {z: len(v) for z, v in sorted(layers.items())})

log("top view (rows=y %d..%d, cols=x %d..%d):" % (ys[0], ys[-1], xs[0], xs[-1]))
for cy in range(ys[0], ys[-1] + 1):
    row = ""
    for cx in range(xs[0], xs[-1] + 1):
        t = top.get((cx, cy))
        row += (t[1][0].upper() if t else ".")
    log("  y=%4d |%s|" % (cy, row))

log("top-z view (same window, %% = z>=10):")
for cy in range(ys[0], ys[-1] + 1):
    row = ""
    for cx in range(xs[0], xs[-1] + 1):
        t = top.get((cx, cy))
        row += ("%" if t and t[0] >= 10 else (str(t[0]) if t else "."))
    log("  y=%4d |%s|" % (cy, row))

bw.destroy_actor()
