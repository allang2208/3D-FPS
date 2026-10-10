"""Read the exact editable baseline before applying the user's multipliers."""
from pathlib import Path
import json
import unreal as u

project=Path('D:/FPS3D/FPSGAME')
out=project/'SourceAssets/BoundCongregateMeshy20261006/CaptureV30';out.mkdir(exist_ok=True)
bp=u.load_asset('/Game/Monsters/BoundCongregate/BP_BoundCongregate')
cdo=u.get_default_object(bp.generated_class());move=cdo.get_editor_property('character_movement')
values={key:float(cdo.get_editor_property(key)) for key in
        ('walk_speed','animation_walk_speed','tentacle_pull_speed','tentacle_range','tentacle_cooldown','tentacle_hold_seconds','bite_trigger_range')}
values.update(rotation_yaw=move.get_editor_property('rotation_rate').yaw,
    max_acceleration=move.get_editor_property('max_acceleration'),
    braking_deceleration_walking=move.get_editor_property('braking_deceleration_walking'),
    visual_mesh=cdo.get_editor_property('visual_mesh').get_path_name(),
    flurry_clip=cdo.get_editor_property('flurry_clip').get_path_name(),
    bite_clip=cdo.get_editor_property('bite_clip').get_path_name())
if not (out/'before_values.json').exists():
    (out/'before_values.json').write_text(json.dumps(values,indent=2),encoding='utf8')
state=dict(values=values,game_world=bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()),
    dirty_content=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
    dirty_maps=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()])
(out/'editor_state.json').write_text(json.dumps(state,indent=2),encoding='utf8')
print(json.dumps(state),flush=True)
