"""Correct daylight in an already-built, isolated screenshot host only."""
import time
import traceback
import unreal as u

if '-HillsLandscapeCapture' not in u.SystemLibrary.get_command_line():
    raise RuntimeError('Isolated landscape capture flag required')

next_poll = 0.0
handle = None


def tick(dt):
    global next_poll
    now = time.monotonic()
    if now < next_poll:
        return
    next_poll = now + 1.0
    try:
        world = u.get_default_object(u.UnrealEditorSubsystem).get_game_world()
        if not world:
            return
        for weather in u.GameplayStatics.get_all_actors_of_class(world, u.FPSWeatherManager):
            hour = weather.get_editor_property('normalized_day_time') * 24.0
            if hour < 10.4 or hour > 10.7:
                weather.set_editor_property('real_seconds_per_game_day', 864000.0)
                weather.advance_game_time((10.5 - hour) % 24.0 + 0.0001)
                u.log('HILLS_CAPTURE_DAYLIGHT corrected_from_hour=%.3f' % hour)
    except Exception:
        u.log_error('HILLS_CAPTURE_DAYLIGHT: ' + traceback.format_exc())
        u.unregister_slate_post_tick_callback(handle)


handle = u.register_slate_post_tick_callback(tick)
u.log('HILLS_CAPTURE_DAYLIGHT registered')
