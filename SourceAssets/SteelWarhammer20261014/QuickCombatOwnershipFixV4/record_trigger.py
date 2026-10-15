"""Read-only, bounded capture of the user's F input and animation clock."""
import unreal as u,json,time,ctypes,traceback
from pathlib import Path
from collections import deque
P=Path(__file__).resolve().parent
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if not world:raise RuntimeError('No current PIE world')
pawn=u.GameplayStatics.get_player_character(world,0);pc=u.GameplayStatics.get_player_controller(world,0)
quick=pawn.get_editor_property('QuickCombatPistol')
mesh=next(c for c in pawn.get_components_by_class(u.SkeletalMeshComponent) if c.get_name()=='ProductionToolHands')
started=time.monotonic();rows=deque(maxlen=1200);event=None;handle=None
def capture(delta):
    global event,handle
    now=time.monotonic()-started
    try:
        active=quick.is_occupying_left_hand();down=bool(ctypes.windll.user32.GetAsyncKeyState(0x46)&0x8000)
        v=mesh.get_socket_transform('WPN_root',u.RelativeTransformSpace.RTS_COMPONENT)
        p=v.translation
        rows.append({'wall':now,'F':down,'phase':str(quick.get_phase()),'age':quick.get_action_age(),
                     'position':mesh.get_position(),'weapon_state':str(pawn.get_weapon_state()),'wpn':[p.x,p.y,p.z]})
        if event is None and (down or active):event=now
        done=now>180 or (event is not None and now>event+1.5)
    except Exception as ex:
        rows.append({'error':traceback.format_exc()});done=True
    if done:
        u.unregister_slate_post_tick_callback(handle)
        out={'event':event,'rows':list(rows)}
        (P/'trigger_before.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
        print('WARHAMMER_TRIGGER_CAPTURE '+json.dumps({'event':event,'rows':len(rows)}))
handle=u.register_slate_post_tick_callback(capture)
print('WARHAMMER_TRIGGER_CAPTURE_ARMED')
