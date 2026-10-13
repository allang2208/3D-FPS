"""Arm in an existing editor, before PIE. Record dungeon entry and first staff wave.

Run through Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript <this file>.
Does not launch/stop PIE, change quality, or require a manually timed trigger.
"""

def arm_dungeon_entry_capture():
    import ctypes
    from ctypes import wintypes
    import datetime
    import json
    import os
    import time
    from pathlib import Path
    import unreal as u

    active = getattr(u, '_fps_dungeon_entry_capture', None)
    if active and active.get('status') in ('armed', 'recording', 'exporting'):
        print(json.dumps({'already_armed': active['report'], 'status': active['status']}))
        return
    if u.TraceUtilLibrary.is_tracing():
        raise RuntimeError('Another trace is active; left untouched.')

    job = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    capture_rdg = bool(globals().get('DUNGEON_CAPTURE_RDG', False))
    capture_monsters = bool(globals().get('DUNGEON_CAPTURE_MONSTERS', False))
    if capture_monsters and u.SystemLibrary.get_console_variable_int_value('fps.Perf.MonsterCaptureVersion') != 1:
        raise RuntimeError('The AI/render capture build is not loaded; do not start PIE yet.')
    out = Path(u.Paths.project_saved_dir()).resolve() / 'DungeonEntryCaptures' / job
    out.mkdir(parents=True, exist_ok=False)
    report = out / 'capture.json'
    trace = out / 'capture.utrace'
    state = {
        'status': 'armed', 'report': str(report), 'trace': str(trace), 'pid': os.getpid(),
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'arm_timeout_seconds': 1200, 'recording_limit_seconds': 300 if capture_monsters else 180,
        'post_first_spawn_seconds': 40 if capture_monsters else (10 if capture_rdg else 30),
        'monster_attribution': capture_monsters,
        'collector_version': 2,
        'engine_version': u.SystemLibrary.get_engine_version(),
        'spawn_observation_contract': '0.5 s observation of staff with a controller; '
            'deferred bodies without AI are excluded. Use FPS.Hall.SpawnActivated '
            'trace bookmarks for exact native activation times.',
        'rdg_resource_capture': capture_rdg, 'observations': [], 'slow_callback_gaps': [],
        'gap_contract': 'Slate post-tick callback wall gaps, not engine-frame timings; '
                        'use trace Frame scopes for FPS and CPU/GPU attribution.',
        'foreground_callbacks': 0, 'background_callbacks': 0, 'errors': [],
    }
    u._fps_dungeon_entry_capture = state
    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
    armed_at = time.perf_counter()
    started_at = first_spawn_at = previous_tick_at = None
    next_poll = next_save = 0.0
    handle = None
    added_channels, removed_channels = set(), set()
    previous_names = set()
    resources_started = False
    capture_world = None
    export_deadline = None
    receipt = out / 'performance-report-receipt.json'
    initial_world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world() if capture_monsters else None
    initial_world_path = initial_world.get_path_name() if initial_world else None
    initial_world = None
    wait_for_new_world = bool(initial_world_path and 'L_Dungeon_Randomized' in initial_world_path)
    state['waiting_for_new_dungeon_world'] = wait_for_new_world

    def foreground():
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), ctypes.byref(pid))
        return pid.value == os.getpid()

    def save():
        report.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')

    def observe_ai(world, row):
        row['ai'] = []
        if state.get('ai_observation_error'):
            return
        try:
            for ai in u.GameplayStatics.get_all_actors_of_class(world, u.MonsterAIController):
                # Controller.GetPawn is native-only. K2_GetPawn is exposed to
                # Python as get_controlled_pawn in this engine version.
                pawn = ai.get_controlled_pawn()
                if pawn is None:
                    continue
                row['ai'].append({
                    'controller': ai.get_name(), 'pawn': pawn.get_name(),
                    'class': pawn.get_class().get_name(),
                    'action': str(ai.get_editor_property('active_action')),
                    'navigation_requests': ai.get_editor_property('navigation_requests'),
                    'last_navigation_failed': ai.get_editor_property('navigation_failed'),
                    'decision_enabled': ai.get_editor_property('decision_enabled'),
                })
        except Exception as exc:
            # Optional Python context must not discard the native CPU/GPU
            # trace. Report the missing context once and keep recording.
            state['ai_observation_error'] = repr(exc)
            u.log_warning('DUNGEON_CAPTURE_AI_CONTEXT ' + repr(exc))

    def observe(world, now):
        nonlocal first_spawn_at, previous_names
        # Poll twice a second; never scan the world on each render frame.
        actors = u.GameplayStatics.get_all_actors_of_class(world, u.NurseZombie)
        staff = [a for a in actors if a.get_class().get_name().startswith('BP_Faceless')
                 and a.get_controller() is not None]
        names = {a.get_name() for a in staff}
        new_names = sorted(names - previous_names)
        if new_names:
            if first_spawn_at is None:
                first_spawn_at = now
                state['first_staff_observed_seconds'] = now - started_at
                state['first_staff_observed_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            u.TraceUtilLibrary.trace_bookmark('DungeonCapture_StaffAdded_' + ','.join(new_names))
        previous_names = names
        camera = u.GameplayStatics.get_player_camera_manager(world, 0)
        row = {
            'seconds': now - started_at, 'foreground': foreground(),
            'paused': u.GameplayStatics.is_game_paused(world), 'staff_count': len(staff),
            'staff_alive': sum(a.get_editor_property('health') > 0 for a in staff),
            'new_staff': new_names,
            'camera': str(camera.get_camera_location()) if camera else None,
            'rotation': str(camera.get_camera_rotation()) if camera else None,
        }
        state['observations'].append(row)
        if capture_monsters:
            # State/call counters only. Python polling is not a CPU timer, and
            # NavigationRequests includes admitted goals that failed projection.
            observe_ai(world, row)

    def detach():
        nonlocal handle
        if handle is not None:
            u.unregister_slate_post_tick_callback(handle)
            handle = None

    def restore_resources():
        nonlocal resources_started
        if resources_started:
            world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
            world = world or u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            u.SystemLibrary.execute_console_command(world, 'fps.Perf.MonsterCapture end')
            resources_started = False

    def finish(reason):
        nonlocal export_deadline
        try:
            if started_at is not None:
                u.TraceUtilLibrary.trace_bookmark('DungeonCapture_End_' + reason)
                state['trace_stop_returned'] = u.TraceUtilLibrary.stop_tracing()
                for channel in added_channels:
                    u.TraceUtilLibrary.toggle_channel(channel, False)
                for channel in removed_channels:
                    u.TraceUtilLibrary.toggle_channel(channel, True)
                state['elapsed_seconds'] = time.perf_counter() - started_at
                if capture_monsters and reason in ('complete', 'recording_limit') and capture_world:
                    state['performance_report_receipt'] = str(receipt)
                    # Export after Trace.Stop, so the diagnostic scan does not
                    # inflate the combat CPU/GPU timeline being investigated.
                    u.SystemLibrary.execute_console_command(capture_world,
                        'fps.Perf.MonsterCapture export "' + str(receipt) + '"')
                    export_deadline = time.perf_counter() + 30.
        finally:
            restore_resources()
            state['status'] = reason
            state['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            if export_deadline is not None:
                state['capture_result'] = reason
                state['status'] = 'exporting'
            else:
                detach()
            save()
            u.log('DUNGEON_ENTRY_CAPTURE ' + reason + ' ' + str(report))

    def tick(_delta):
        nonlocal started_at, previous_tick_at, next_poll, next_save
        nonlocal added_channels, removed_channels
        nonlocal resources_started, capture_world
        nonlocal wait_for_new_world
        try:
            now = time.perf_counter()
            if state['status'] == 'exporting':
                if now < next_poll:
                    return
                next_poll = now + .5
                if receipt.exists():
                    state['performance_report'] = json.loads(receipt.read_text(encoding='utf-8-sig'))
                    state['status'] = state['capture_result']
                    if not state['performance_report'].get('saved'):
                        state['errors'].append('Performance JSON export failed; trace is retained.')
                elif now >= export_deadline:
                    state['status'] = state['capture_result']
                    state['errors'].append('Performance JSON receipt timed out; trace is retained.')
                else:
                    return
                detach()
                save()
                u.log('DUNGEON_ENTRY_CAPTURE reports_ready ' + str(report))
                return
            if started_at is None:
                if now < next_poll:
                    return
                next_poll = now + .25
                if now - armed_at >= state['arm_timeout_seconds']:
                    finish('no_dungeon_world'); return
                world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
                if wait_for_new_world:
                    if world and world.get_path_name() == initial_world_path:
                        return
                    wait_for_new_world = False
                    state['waiting_for_new_dungeon_world'] = False
                if not world or 'L_Dungeon_Randomized' not in world.get_path_name():
                    return
                if u.TraceUtilLibrary.is_tracing():
                    finish('another_trace_started'); return
                state['world'] = world.get_path_name()
                capture_world = world
                state['viewport'] = str(u.WidgetLayoutLibrary.get_viewport_size(world))
                state['cvars'] = {k: u.SystemLibrary.get_console_variable_float_value(k) for k in (
                    'r.RayTracing', 'r.Lumen.HardwareRayTracing', 'r.DynamicGlobalIlluminationMethod',
                    'r.ReflectionMethod', 'r.Shadow.Virtual.Enable', 'sg.ShadowQuality',
                    'r.ScreenPercentage', 'r.Streaming.PoolSize', 'r.VSync', 't.MaxFPS')}
                if capture_monsters:
                    state['diagnostic_cvars_before'] = {k: u.SystemLibrary.get_console_variable_int_value(k)
                        for k in ('fps.Perf.RenderResourceSampling', 'fps.Perf.GpuResourceInventory')}
                    u.SystemLibrary.execute_console_command(world, 'fps.Perf.MonsterCapture begin')
                    resources_started = True
                before = set(u.TraceUtilLibrary.get_enabled_channels())
                state['channels_before'] = sorted(before)
                state['channels_requested'] = ['Cpu', 'Frame', 'Gpu', 'Bookmark', 'Region',
                                               'ThreadIdleScope', 'LoadTime', 'AssetLoadTime', 'Log', 'Counters']
                if capture_monsters:
                    state['channels_requested'].append('Task')
                if capture_rdg:
                    # RDG includes resource names, dimensions, byte sizes and
                    # transient cache hits; CPU scopes alone cannot identify the
                    # texture behind AllocatePlacedTexture. Opt in for 10 s only.
                    state['channels_requested'].append('RDG')
                if not u.TraceUtilLibrary.start_trace_to_file(str(trace), state['channels_requested']):
                    finish('start_failed'); return
                started_at = previous_tick_at = time.perf_counter()
                state['started_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                state['status'] = 'recording'
                after = set(u.TraceUtilLibrary.get_enabled_channels())
                state['channels_enabled'] = sorted(after)
                added_channels, removed_channels = after - before, before - after
                u.TraceUtilLibrary.trace_bookmark('DungeonCapture_WorldDetected')
                observe(world, started_at)
                next_poll = started_at + .5
                next_save = started_at + 5.
                save()
                return

            front = foreground()
            state['foreground_callbacks' if front else 'background_callbacks'] += 1
            gap = now - previous_tick_at
            previous_tick_at = now
            if gap >= .05 and len(state['slow_callback_gaps']) < 512:
                state['slow_callback_gaps'].append({'seconds': now - started_at,
                    'gap_ms': gap * 1000., 'foreground': front})
                u.TraceUtilLibrary.trace_bookmark('DungeonCapture_CallbackGap_%.1fms' % (gap * 1000.))
            if now < next_poll:
                return
            next_poll = now + .5
            world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
            if not world or world.get_path_name() != state['world']:
                finish('world_ended'); return
            observe(world, now)
            if first_spawn_at is not None and now - first_spawn_at >= state['post_first_spawn_seconds']:
                finish('complete'); return
            if now - started_at >= state['recording_limit_seconds']:
                finish('recording_limit'); return
            if now >= next_save:
                next_save = now + 5.
                save()
        except Exception as exc:
            state['errors'].append(repr(exc))
            if state['status'] == 'exporting':
                state['status'] = 'export_error'
                detach()
                save()
            else:
                finish('error')

    save()
    handle = u.register_slate_post_tick_callback(tick)
    print(json.dumps({'armed': str(report), 'trigger': 'random dungeon World detected',
                      'stop': str(state['post_first_spawn_seconds']) +
                              ' seconds after first staff appears; at most ' +
                              str(state['recording_limit_seconds']) + ' seconds of recording'}))


arm_dungeon_entry_capture()
