"""Diagnose why new_level fails: what state is the editor in?"""
import unreal

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

try:
    world = ues.get_editor_world()
    unreal.log('DIAG world=' + (world.get_name() if world else 'None'))
except Exception as e:
    unreal.log('DIAG world_err ' + str(e))

try:
    unreal.log('DIAG all_worlds=' + str([w.get_name() for w in unreal.EditorLevelLibrary.get_all_level_actors()][:1]))
except Exception as e:
    pass

try:
    actors = eas.get_all_level_actors()
    unreal.log(f'DIAG actors={len(actors)}')
except Exception as e:
    unreal.log('DIAG actors_err ' + str(e))

# Does the target package exist already?
try:
    exists = unreal.EditorAssetLibrary.does_asset_exist('/Game/GameMaps/L_Dungeon_Prototype')
    unreal.log('DIAG target_exists=' + str(exists))
except Exception as e:
    unreal.log('DIAG exists_err ' + str(e))

# Try loading an existing map to give the editor a world.
try:
    loaded = les.load_level('/Game/GameMaps/DayNight_Lighting')
    unreal.log('DIAG load_daynight=' + str(loaded))
    world = ues.get_editor_world()
    unreal.log('DIAG world_after=' + (world.get_name() if world else 'None'))
except Exception as e:
    unreal.log('DIAG load_err ' + str(e))

unreal.log('DIAG_DONE')