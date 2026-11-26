"""Start the native diagnostic in a copied, offscreen PIE host. No asset saves."""
import time
import unreal as u

args = u.SystemLibrary.get_command_line()
if '-HillsPIEAudit' not in args or 'VegetationStreamingCheck' not in args:
    raise RuntimeError('This script requires the isolated hills PIE audit launcher')
# Autosave is disabled in the isolated launcher's config override. This editor
# settings class is not exposed by the UE 5.8 Python module.
editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
started = time.monotonic()
requested = False
callback = None

def tick(_dt):
    global requested
    elapsed = time.monotonic()-started
    if elapsed < 3:
        return
    if not requested:
        requested = True
        editor.editor_request_begin_play()
        u.log('HILLS_PIE_AUDIT requested PlayInEditor')
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    pc = u.GameplayStatics.get_player_controller(world, 0) if world else None
    if world and pc and u.GameplayStatics.get_all_actors_of_class(world, u.TemperateHillsWorld):
        u.unregister_slate_post_tick_callback(callback)
        u.SystemLibrary.execute_console_command(world, 'fps.Test.HillsVegetationStreaming', pc)
        u.log('HILLS_PIE_AUDIT native diagnostic started in ' + world.get_path_name())
    elif elapsed > 600:
        u.unregister_slate_post_tick_callback(callback)
        u.log_error('HILLS_PIE_AUDIT failed to create a hills player within 600 seconds')
        u.SystemLibrary.execute_console_command(None, 'QUIT_EDITOR')

callback = u.register_slate_post_tick_callback(tick)
