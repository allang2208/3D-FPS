"""Read only the active weapon/outfit paths for the reported inspect defect."""
import json, unreal as u
from pathlib import Path
O=Path(__file__).parent
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
result={'pie':bool(world),'components':[]}
if world:
    player=u.GameplayStatics.get_player_character(world,0)
    if player:
        for c in player.get_components_by_class(u.SkeletalMeshComponent):
            if not c.is_visible():continue
            mesh=c.get_editor_property('skeletal_mesh_asset')
            if not mesh:continue
            row={'name':c.get_name(),'mesh':mesh.get_path_name()}
            a=c.get_anim_instance()
            if a:
                for key in ('grip_profile','action_clip','action_time','action_alpha'):
                    try:
                        v=a.get_editor_property(key)
                        row[key]=v.get_path_name() if hasattr(v,'get_path_name') else v
                    except Exception:pass
            result['components'].append(row)
(O/'active.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result),flush=True)
