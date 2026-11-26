"""Start the native streaming check after separately timing resource preparation.

Used only by an explicitly requested isolated -game check. Leaves the native
180-second grass/rotation/rainforest limits intact and preserves first-run failures.
"""
import time
import traceback
import unreal as u

started = time.monotonic()
next_log = 0.0
handle = None


def tick(dt):
    global next_log
    try:
        # The subsystem implementation returns GWorld in standalone -game.
        world = u.get_default_object(u.UnrealEditorSubsystem).get_game_world()
        if not world:
            return
        elapsed = time.monotonic() - started
        hills = u.GameplayStatics.get_all_actors_of_class(world, u.TemperateHillsWorld)
        pc = u.GameplayStatics.get_player_controller(world, 0)
        ready = bool(hills and hills[0].get_editor_property('ready'))
        if elapsed >= next_log:
            next_log = elapsed + 10
            u.log('HILLS_ENTRY_OBSERVER elapsed_s=%.3f world=%s ready=%s' %
                  (elapsed, world.get_name(), ready))
        if ready and pc and not pc.is_move_input_ignored():
            u.log('HILLS_ENTRY_OBSERVER passed elapsed_s=%.3f' % elapsed)
            u.unregister_slate_post_tick_callback(handle)
            u.SystemLibrary.execute_console_command(world, 'fps.Test.HillsVegetationStreaming')
        elif elapsed > 600:
            u.log_error('HILLS_ENTRY_OBSERVER failed: entry exceeded 600 seconds')
            u.unregister_slate_post_tick_callback(handle)
            u.SystemLibrary.execute_console_command(world, 'quit')
    except Exception:
        u.log_error('HILLS_ENTRY_OBSERVER exception: ' + traceback.format_exc())
        u.unregister_slate_post_tick_callback(handle)
        u.SystemLibrary.execute_console_command(world, 'quit')


if '-HillsVegetationCheck' not in u.SystemLibrary.get_command_line():
    raise RuntimeError('Isolated diagnostic flag required')
handle = u.register_slate_post_tick_callback(tick)
u.log('HILLS_ENTRY_OBSERVER registered')
