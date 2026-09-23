"""Template run via capture_slate_stall.ps1 in an existing PIE session."""
import ctypes
from ctypes import wintypes
import datetime
import json
import os
import time
from pathlib import Path
import unreal as u

JOB_ID = '__CAPTURE_ID__'
OUT = Path(u.Paths.project_dir()).resolve() / 'Saved/SlateStall20260923' / JOB_ID
OUT.mkdir(parents=True, exist_ok=True)
TRACE = OUT / 'capture.utrace'
STATUS = OUT / 'capture.json'
user32 = ctypes.windll.user32
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))

def foreground():
    process = wintypes.DWORD()
    user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), ctypes.byref(process))
    return process.value == os.getpid()

def context(world):
    camera = u.GameplayStatics.get_player_camera_manager(world, 0)
    return {'world': world.get_path_name(), 'camera': str(camera.get_camera_location()) if camera else None,
            'rotation': str(camera.get_camera_rotation()) if camera else None,
            'viewport': str(u.WidgetLayoutLibrary.get_viewport_size(world)),
            'paused': u.GameplayStatics.is_game_paused(world), 'foreground': foreground()}

if u.TraceUtilLibrary.is_tracing():
    raise RuntimeError('A trace is already active; existing capture left untouched.')
state = {'status': 'armed', 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'trace': str(TRACE), 'pid': os.getpid(), 'duration_seconds': 15,
         'channels_before': list(u.TraceUtilLibrary.get_enabled_channels()), 'foreground_ticks': 0,
         'background_ticks': 0, 'tick_observations': [], 'errors': []}
armed_at = time.perf_counter()
ready_at = None
started_at = None
handle = None

def save():
    STATUS.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')

def finish(reason):
    global handle
    try:
        if started_at is not None:
            u.TraceUtilLibrary.trace_bookmark('FPS_SlateStall_End_' + JOB_ID)
            state['trace_stop_returned'] = u.TraceUtilLibrary.stop_tracing()
            # Restore only trace-channel state changed by this diagnostic capture.
            before = set(state['channels_before'])
            after = set(u.TraceUtilLibrary.get_enabled_channels())
            for channel in after - before:
                u.TraceUtilLibrary.toggle_channel(channel, False)
            for channel in before - after:
                u.TraceUtilLibrary.toggle_channel(channel, True)
            state['elapsed_seconds'] = time.perf_counter() - started_at
    finally:
        state['status'] = reason
        state['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save()
        if handle is not None:
            u.unregister_slate_post_tick_callback(handle)
            handle = None
        u.log('FPS_SLATE_CAPTURE ' + str(STATUS) + ' ' + reason)

def tick(delta):
    global ready_at, started_at
    try:
        now = time.perf_counter()
        worlds = list(u.EditorLevelLibrary.get_pie_worlds(False))
        if started_at is None:
            if now - armed_at > 90:
                finish('no_foreground_pie'); return
            if not worlds or not foreground() or u.GameplayStatics.is_game_paused(worlds[0]):
                ready_at = None; return
            if ready_at is None:
                ready_at = now; return
            if now - ready_at < 2:
                return
            if u.TraceUtilLibrary.is_tracing():
                finish('another_trace_started'); return
            state['start_context'] = context(worlds[0])
            state['cvars'] = {k: u.SystemLibrary.get_console_variable_float_value(k) for k in ('r.RayTracing','r.Lumen.HardwareRayTracing','r.DynamicGlobalIlluminationMethod','r.ReflectionMethod','r.ScreenPercentage','sg.ShadowQuality','r.Streaming.PoolSize','r.VSync','t.MaxFPS')}
            state['channels_requested'] = ['Cpu','Frame','Gpu','Slate','Bookmark','Region','ThreadIdleScope','LoadTime','AssetLoadTime','Module','ContextSwitch']
            if not u.TraceUtilLibrary.start_trace_to_file(str(TRACE), state['channels_requested']):
                finish('start_failed'); return
            started_at = time.perf_counter()
            state['status'] = 'recording'
            state['started_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            u.TraceUtilLibrary.trace_bookmark('FPS_SlateStall_Start_' + JOB_ID)
            save()
            return
        front = foreground()
        state['foreground_ticks' if front else 'background_ticks'] += 1
        state['tick_observations'].append({'offset_seconds': now-started_at, 'foreground': front})
        if not worlds or worlds[0].get_path_name() != state['start_context']['world']:
            finish('world_changed'); return
        if now - started_at >= state['duration_seconds']:
            state['end_context'] = context(worlds[0])
            finish('complete')
    except Exception as exc:
        state['errors'].append(str(exc))
        finish('error')

save()
handle = u.register_slate_post_tick_callback(tick)
print('Armed existing-session capture: ' + str(STATUS))
