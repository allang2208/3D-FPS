"""Headless probe: is voxel grounding broken in general, or is there just no floor at the site?"""

import unreal

KEY = "ColdSteelPlayer|DayNight_Lighting"
WORLD_cls = unreal.load_class(None, "/Script/FPSGAME.VoxelBuildWorld")

sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()

for label, x, y in (("build site", 570.0, -670.0), ("column site", 600.0, 600.0), ("floor mid", 0.0, 0.0)):
    hit = unreal.SystemLibrary.line_trace_single(
        world, unreal.Vector(x, y, 200.0), unreal.Vector(x, y, -100.0),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY2, False, [], unreal.DrawDebugTrace.NONE, False)
    if not hit:
        print("[probe] %-11s NO HIT - no ground within z -100..200" % label)
    else:
        print("[probe] %-11s comp=%s point=%s" % (
            label,
            hit.component.get_name() if hit.component else "-",
            (round(hit.location.x, 1), round(hit.location.y, 1), round(hit.location.z, 1))))

bw = sub.spawn_actor_from_class(WORLD_cls, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
print("[probe] init=%s" % bw.call_method("DebugInitialize", args=(KEY,)))
for label, cell in (("floor cell", (30, 30, 0)), ("build cell", (28, -31, 0))):
    r = bw.call_method("EditCells", args=([unreal.IntVector(*cell)], unreal.Name("marble")))
    print("[probe] place %s %s -> %s blocks=%s" % (
        label, cell, r, bw.call_method("BlockCount")))
    if r:
        bw.call_method("EditCells", args=([unreal.IntVector(*cell)], unreal.Name("None")))
bw.destroy_actor()
