"""Headless: test voxel anchoring at (0,0,0) vs the build site; inspect Brush1 collision."""

import unreal

KEY = "ColdSteelPlayer|DayNight_Lighting"
WORLD_cls = unreal.load_class(None, "/Script/FPSGAME.VoxelBuildWorld")

sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.EditorLoadingAndSavingUtils.load_map("/Game/GameMaps/DayNight_Lighting")
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()

for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
    if a.get_actor_label() == "Brush1":
        for comp in a.get_components_by_class(unreal.PrimitiveComponent):
            bi = comp.get_editor_property("body_instance")
            print("[t] Brush1 comp=%s collision=%s" % (
                comp.get_name(), bi.get_editor_property("collision_enabled")))

bw = sub.spawn_actor_from_class(WORLD_cls, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
print("[t] init=%s" % bw.call_method("DebugInitialize", args=(KEY,)))
for label, cell in (("origin (0,0,0)", (0, 0, 0)),
                    ("near origin (2,2,0)", (2, 2, 0)),
                    ("build site", (28, -31, 0))):
    r = bw.call_method("EditCells", args=([unreal.IntVector(*cell)], unreal.Name("marble")))
    print("[t] place %s -> %s blocks=%s" % (label, r, bw.call_method("BlockCount")))
    if r:
        bw.call_method("EditCells", args=([unreal.IntVector(*cell)], unreal.Name("None")))
bw.destroy_actor()
