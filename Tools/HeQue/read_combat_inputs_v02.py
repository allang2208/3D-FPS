"""Read current HeQue asset/runtime inputs without spawning or changing play state."""
import json
from pathlib import Path
import unreal as u
root=Path('D:/FPS3D/FPSGAME/SourceAssets/HeQueBoss20261014/WeightyMoveV02/Records');root.mkdir(parents=True,exist_ok=True)
def prop(obj,name):
    try:
        v=obj.get_editor_property(name)
        if isinstance(v,(int,float,bool,str)) or v is None:return v
        if isinstance(v,u.Object):return v.get_path_name()
        return str(v)
    except Exception as e:return str(e)
def describe(a):
    mesh=a.get_editor_property('mesh');move=a.get_editor_property('character_movement')
    result=dict(name=a.get_path_name(),location=str(a.get_actor_location()),rotation=str(a.get_actor_rotation()),
        fields={n:prop(a,n) for n in ('sweep_clip','sweep_frames','sweep','reaction','stopping_distance','sweep_trigger_range','stride_distance','walk_speed','turn_speed')},
        mesh_transform={n:prop(mesh,n) for n in ('relative_location','relative_rotation','relative_scale3d')},mesh=prop(mesh,'skeletal_mesh_asset'),
        movement={n:prop(move,n) for n in ('movement_mode','max_walk_speed','max_acceleration','braking_deceleration_walking','velocity')})
    # Avoid dumping the large baked contact arrays.
    result['fields']['sweep_frames']=len(a.get_editor_property('sweep_frames'))
    c=a.get_controller()
    if c:
        result['controller']={n:prop(c,n) for n in ('b_decision_enabled','active_action')}
        bb=c.get_editor_property('blackboard')
        if bb:
            result['blackboard']={n:bb.get_value_as_bool(n) for n in ('Hold','CanAttack','HasTarget','Visible','Returning')}
            target=bb.get_value_as_object('Target')
            if target:result['target']=dict(name=target.get_path_name(),location=str(target.get_actor_location()))
    return result
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem);world=editor.get_game_world()
bp=u.load_asset('/Game/Monsters/HeQue/BP_HeQue');cdo=u.get_default_object(bp.generated_class())
report=dict(pie=bool(world),defaults={n:prop(cdo,n) for n in ('sweep_clip','stopping_distance','stride_distance','walk_speed','turn_speed')},
    default_contact_frames=len(cdo.get_editor_property('sweep_frames')),actors=[])
if world:
    report['actors']=[describe(a) for a in u.GameplayStatics.get_all_actors_of_class(world,u.HeQueMonster)]
(root/'combat-inputs.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('HEQUE_COMBAT_INPUTS '+json.dumps(report,ensure_ascii=False),flush=True)
