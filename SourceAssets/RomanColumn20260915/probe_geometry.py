"""Headless: what geometry exists under/around the build site, and where is the Floor?"""

import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.EditorLoadingAndSavingUtils.load_map("/Game/GameMaps/DayNight_Lighting")
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
print("[geo] world=%s actors=%d" % (world.get_name(),
      len(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor))))

for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
    label = a.get_actor_label()
    o, e = a.get_actor_bounds(False)
    # anything near the build site OR the big ground pieces
    near_site = (o.x - e.x < 800 and o.x + e.x > 400 and o.y - e.y < -300 and o.y + e.y > -900)
    interesting = label in ("Floor",) or near_site
    if interesting:
        print("[geo] %-28s origin=(%.0f,%.0f,%.0f) extent=(%.0f,%.0f,%.0f)" % (
            label, o.x, o.y, o.z, e.x, e.y, e.z))
