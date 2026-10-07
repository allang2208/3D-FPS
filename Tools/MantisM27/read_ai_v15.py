"""Read-only evidence for the requested M27 approach/attack investigation."""
import json
from pathlib import Path
import unreal as u

out = Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27/CombatV15')
out.mkdir(parents=True, exist_ok=True)
result = {'pie': u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor(), 'actors': []}
bp = u.load_asset('/Game/Monsters/MantisM27/BP_MantisM27')
props = ['health', 'max_health', 'attack_range', 'contact_time', 'contact_end',
         'recovery_time', 'pounce_min_range', 'pounce_max_range', 'walk_speed', 'cloak_move_speed']
def fields(obj):
    row = {}
    for key in props:
        try: row[key] = obj.get_editor_property(key)
        except Exception: pass
    return row
defaults = u.get_default_object(bp.generated_class())
result['defaults'] = fields(defaults)
for key in ['left_slash_clip', 'right_slash_clip', 'pounce_windup_clip']:
    clip = defaults.get_editor_property(key)
    result['defaults'][key] = clip.get_path_name() if clip else None
if result['pie']:
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    for a in u.GameplayStatics.get_all_actors_of_class(world, u.MantisM27Monster):
        move = a.get_character_movement()
        row = dict(name=a.get_name(), state=str(a.get_editor_property('state')), **fields(a),
                   cloaked=a.get_editor_property('b_cloaked'), position=str(a.get_actor_location()),
                   velocity=str(a.get_velocity()), movement_mode=str(move.movement_mode), max_speed=move.max_walk_speed)
        ai = a.get_controller()
        if ai:
            row.update(active_action=ai.get_editor_property('active_action'),
                       navigation_failed=ai.get_editor_property('b_navigation_failed'))
            bb = u.AIBlueprintHelperLibrary.get_blackboard(ai)
            if bb:
                row['blackboard'] = {key: bb.get_value_as_bool(key) for key in ['Hold','Returning','CanAttack','HasTarget','Visible']}
                row['last_known'] = str(bb.get_value_as_vector('LastKnown'))
                row['home'] = str(bb.get_value_as_vector('Home'))
                target = bb.get_value_as_object('Target')
                row['target'] = target.get_name() if target else None
                if target:
                    row.update(distance=a.get_horizontal_distance_to(target), target_position=str(target.get_actor_location()), target_velocity=str(target.get_velocity()))
        result['actors'].append(row)
(out / 'live_ai_before.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False), flush=True)
