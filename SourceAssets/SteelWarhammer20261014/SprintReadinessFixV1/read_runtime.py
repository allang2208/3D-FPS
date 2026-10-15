"""Read the existing session only; do not start PIE or change player inputs."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
sub=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=sub.get_game_world() if sub else None
data={'game_running':bool(world),'pawns':[],
      'dirty_content':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
      'dirty_maps':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]}
def read(obj,field):
    try:return str(obj.get_editor_property(field))
    except Exception:return 'not_reflected'
if world:
    data['world']=world.get_path_name()
    for pawn in u.GameplayStatics.get_all_actors_of_class(world,u.FPSGAMECharacter):
        move=pawn.get_component_by_class(u.CharacterMovementComponent)
        row={'name':pawn.get_path_name(),'velocity':str(pawn.get_velocity()),'sprinting':pawn.is_sprinting(),
             'local':pawn.is_locally_controlled(),'movement_mode':read(move,'movement_mode'),
             'state':{n:read(pawn,n) for n in ['sprint_held','is_sprinting','is_sliding','weapon_jump_airborne','aim_held','fire_held','is_aiming','move_input']},
             'movement':{n:read(move,n) for n in ['max_walk_speed','wants_to_sprint','movement_mode']}}
        tool=pawn.get_component_by_class(u.ProductionToolComponent)
        if tool:
            row['tool']={n:read(tool,n) for n in ['equipped_id','kind','elapsed','equip_elapsed','blunt_sprint_seconds','blunt_sprint_instance','blunt_whirlwind','blunt_uppercut','current_motion']}
        row['sprint_related_attributes']=[n for n in dir(pawn) if any(k in n for k in ['sprint','sliding','fire_held','aim_held','move_input'])]
        data['pawns'].append(row)
(P/'runtime_snapshot.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
print(json.dumps(data))
