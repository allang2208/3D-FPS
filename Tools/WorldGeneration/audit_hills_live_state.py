"""Read-only snapshots of an existing hills game; never moves or edits the world."""
import json
import time
from pathlib import Path
import unreal as u

root = Path('D:/FPS3D/FPSGAME/Saved/HillsDisappearanceAudit20261114')
root.mkdir(parents=True, exist_ok=True)
run = root / time.strftime('live-%H%M%S')
run.mkdir()
started = time.monotonic()
next_sample = 0.0
callback = None
previous = {}
samples = 0
first_hills_sample = None
last_world = None

def prop(obj, key):
    try:
        value = obj.get_editor_property(key)
        if isinstance(value, (str, bool, int, float)) or value is None:
            return value
        if isinstance(value, u.Object):
            return value.get_path_name()
        return str(value)
    except Exception:
        return 'unavailable'

def sample(_dt=0):
    global next_sample, samples, previous, first_hills_sample, last_world
    now = time.monotonic()
    if now < next_sample:
        return
    next_sample = now + 2.0
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    hills = u.GameplayStatics.get_all_actors_of_class(world, u.TemperateHillsWorld) if world else []
    if not hills:
        if now-started >= 600:
            u.unregister_slate_post_tick_callback(callback)
            u.log('HILLS_LIVE_AUDIT not captured: no hills game within 600 seconds')
        return
    if world.get_path_name() != last_world:
        previous = {}
        first_hills_sample = now
        last_world = world.get_path_name()
    pc = u.GameplayStatics.get_player_controller(world, 0)
    pawn = u.GameplayStatics.get_player_pawn(world, 0)
    rows = {}
    layers = []
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.Actor):
        for c in actor.get_components_by_class(u.PrimitiveComponent):
            static = isinstance(c, u.InstancedStaticMeshComponent)
            skinned = isinstance(c, u.InstancedSkinnedMeshComponent)
            if not static and not skinned:
                continue
            mesh = c.get_editor_property('static_mesh') if static else c.get_skinned_asset()
            if not mesh or '/WorldGeneration/TemperateHills/' not in mesh.get_path_name():
                continue
            rows[c.get_path_name()] = dict(mesh=mesh.get_path_name(), count=c.get_instance_count(),
                visible=prop(c, 'visible'), hidden=prop(c, 'hidden_in_game'),
                location=str(c.get_world_location()), owner=actor.get_path_name())
        if isinstance(actor, u.TemperateHillsWorld):
            for c in actor.get_components_by_class(u.PCGComponent):
                layers.append(dict(path=c.get_path_name(), active=prop(c, 'activated'),
                    radii=prop(c, 'generation_radii'), override=prop(c, 'override_generation_radii'),
                    partitioned=prop(c, 'is_component_partitioned')))
    removed = {key: row for key, row in previous.items() if key not in rows}
    changed = {key: {'before': previous[key], 'after': row} for key, row in rows.items()
               if key in previous and row != previous[key]}
    event = dict(elapsed=now-started, world=world.get_path_name(),
        pawn=str(pawn.get_actor_location()) if pawn else None,
        camera=str(pc.player_camera_manager.get_camera_location()) if pc else None,
        totals={'components':len(rows), 'instances':sum(row['count'] for row in rows.values())},
        removed=removed, changed=changed, added={key:row for key,row in rows.items() if key not in previous}, layers=layers)
    with (run / 'samples.jsonl').open('a', encoding='utf8') as f:
        f.write(json.dumps(event, ensure_ascii=False) + '\n')
    previous = rows
    samples += 1
    if samples == 1:
        u.log('HILLS_LIVE_AUDIT started %s components=%d' % (run, len(rows)))
    if now-first_hills_sample >= 120:
        u.unregister_slate_post_tick_callback(callback)
        u.log('HILLS_LIVE_AUDIT finished samples=%d output=%s' % (samples, run))

def tick(dt):
    try:
        sample(dt)
    except Exception:
        import traceback
        u.unregister_slate_post_tick_callback(callback)
        (run / 'error.txt').write_text(traceback.format_exc(), encoding='utf8')
        u.log_error('HILLS_LIVE_AUDIT failed: ' + traceback.format_exc())

callback = u.register_slate_post_tick_callback(tick)
u.log('HILLS_LIVE_AUDIT observer registered; no world changes')
