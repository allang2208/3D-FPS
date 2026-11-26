"""Record an existing hills PIE session without moving the player or editing it."""
import json
import time
import traceback
from pathlib import Path
import unreal as u

root = Path('D:/FPS3D/FPSGAME/Saved/HillsDisappearanceAudit20261114')
run = root/time.strftime('live-frames-%H%M%S')
run.mkdir(parents=True)
registered = time.monotonic()
started = None
world_path = None
last_frame = -1
shots = 0
next_state = 0
previous = {}
callback = None

def finish(reason):
    u.unregister_slate_post_tick_callback(callback)
    (run/'complete.json').write_text(json.dumps({'reason':reason,'requests':shots,
        'seconds':time.monotonic()-started if started else 0},indent=2),encoding='utf8')
    u.log('HILLS_LIVE_FRAMES finished '+str(run)+' '+reason)

def tick(_dt):
    global started,world_path,last_frame,shots,next_state,previous
    try:
        now = time.monotonic()
        if started is None and now-registered>=600:
            finish('hills was not ready within 600 seconds');return
        world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
        hills = u.GameplayStatics.get_all_actors_of_class(world,u.TemperateHillsWorld) if world else []
        if not hills:
            if started:finish('hills session ended')
            elif now-registered>600:finish('no hills session')
            return
        if not hills[0].get_editor_property('ready'):
            return
        if started is None:
            started = now
            world_path = world.get_path_name()
            u.log('HILLS_LIVE_FRAMES started '+str(run))
        if world.get_path_name()!=world_path:
            finish('world changed');return
        if now-started>=90:
            finish('90 seconds recorded');return
        frame = u.SystemLibrary.get_frame_count()
        if frame==last_frame:return
        last_frame = frame
        pc = u.GameplayStatics.get_player_controller(world,0)
        if not pc:return
        camera = pc.player_camera_manager
        event = {'image':shots,'frame':frame,'seconds':now-started,
            'eye':str(camera.get_camera_location()),'rotation':str(camera.get_camera_rotation())}
        # Do not retain UObject wrappers between callbacks; a recorder must not
        # keep generated components or meshes alive and conceal a lifetime fault.
        if now>=next_state:
            next_state = now+.2
            current = {}
            for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
                for component in actor.get_components_by_class(u.PrimitiveComponent):
                    static = isinstance(component,u.InstancedStaticMeshComponent)
                    if not static and not isinstance(component,u.InstancedSkinnedMeshComponent):continue
                    mesh = component.get_editor_property('static_mesh') if static else component.get_skinned_asset()
                    if not mesh or not mesh.get_path_name().startswith('/Game/WorldGeneration/TemperateHills/'):continue
                    current[component.get_path_name()] = {
                        'mesh':mesh.get_path_name(),'count':component.get_instance_count(),
                        'visible':component.get_editor_property('visible'),
                        'hidden':component.get_editor_property('hidden_in_game')}
            event['state'] = {'components':len(current),'instances':sum(x['count'] for x in current.values()),
                'removed':{k:v for k,v in previous.items() if k not in current},
                'changed':{k:{'before':previous[k],'after':v} for k,v in current.items() if k in previous and v!=previous[k]},
                'added':{k:v for k,v in current.items() if k not in previous}}
            previous = current
        file = (run/('frame-%06d.png'%shots)).as_posix()
        u.SystemLibrary.execute_console_command(world,'Shot filename='+file+' nosuffix',pc)
        with (run/'frames.jsonl').open('a',encoding='utf8') as stream:
            stream.write(json.dumps(event)+'\n')
        shots += 1
    except Exception:
        (run/'error.txt').write_text(traceback.format_exc(),encoding='utf8')
        finish('recorder error')

callback = u.register_slate_post_tick_callback(tick)
u.log('HILLS_LIVE_FRAMES armed '+str(run))
