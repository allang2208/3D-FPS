"""Scan the level: what happened to RomanFountain1 / the jet, and where can a 960x960 foot
actually stand? Ground = actors with top z in [-1,5]; a candidate is OK if a 5x5 sample grid
over the span is covered by ground actors AND no other actor's bbox intersects the span."""

import unreal

LEVEL = "/Game/GameMaps/DayNight_Lighting"
FOOT = 960.0
HEIGHT = 720.0

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not les.load_level(LEVEL):
    print("[scan] load FAILED")
    raise SystemExit(0)

actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
all_actors = actor_sub.get_all_level_actors()
fountains = [a for a in all_actors if a.get_actor_label() == "RomanFountain1"]
jets = [a for a in all_actors if a.get_actor_label() == "RomanFountainFX_Jet"]
print("[scan] fountain actors=%d jets=%d" % (len(fountains), len(jets)))
for f in fountains:
    l = f.get_actor_location()
    print("[scan]   fountain at (%.0f,%.0f,%.0f)" % (l.x, l.y, l.z))
for j in jets:
    l = j.get_actor_location()
    pa = j.get_attach_parent_actor()
    print("[scan]   jet at (%.0f,%.0f,%.0f) parent=%s" % (
        l.x, l.y, l.z, pa.get_actor_label() if pa else None))

solids = [a for a in all_actors if a.get_class().get_name() == "StaticMeshActor"]
boxes = {}
for a in solids:
    o, e = a.get_actor_bounds(False)
    boxes[a] = (o.x - e.x, o.x + e.x, o.y - e.y, o.y + e.y, o.z - e.z, o.z + e.z)

ground = [(a, b) for a, b in boxes.items() if b[4] <= -5.0 and -1.0 <= b[5] <= 5.0]
print("[scan] ground actors=%d, largest:" % len(ground))
for a, b in sorted(ground, key=lambda kv: (kv[1][1] - kv[1][0]) * (kv[1][3] - kv[1][2]), reverse=True)[:6]:
    print("[scan]   %s  x %.0f..%.0f  y %.0f..%.0f  top z %.1f" % (
        a.get_actor_label() or a.get_name(), b[0], b[1], b[2], b[3], b[5]))


def covered(x, y):
    for a, b in ground:
        if b[0] <= x <= b[1] and b[2] <= y <= b[3]:
            return True
    return False


def evaluate(cx, cy):
    half = FOOT / 2.0
    samples = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 0), (0, 1), (1, -1), (1, 0), (1, 1)]
    miss = sum(1 for sx, sy in samples if not covered(cx + sx * half * 0.9, cy + sy * half * 0.9))
    span = (cx - half, cx + half, cy - half, cy + half, 0.0, HEIGHT)
    clash = None
    for a, b in boxes.items():
        if (b[4] < span[5] and b[5] > span[4] and b[0] < span[1] and b[1] > span[0] and
                b[2] < span[3] and b[3] > span[2]):
            if b[5] <= 1.0 and b[4] >= -200.0 and (b[1] - b[0]) > 3000:  # the floor itself
                continue
            clash = "%s(x%.0f..%.0f y%.0f..%.0f z%.0f..%.0f)" % (
                a.get_actor_label() or a.get_name(), b[0], b[1], b[2], b[3], b[4], b[5])
            break
    return miss, clash


for (cx, cy) in ((1350, -1500), (1350, -1700), (1350, -1150), (900, -1500), (1800, -1500),
                 (2400, -600), (600, -600), (2400, 600), (300, 0), (1350, 250)):
    miss, clash = evaluate(cx, cy)
    print("[scan] candidate (%d,%d): ground misses %d/9, clash=%s" % (cx, cy, miss, clash))
print("[scan] DONE")
