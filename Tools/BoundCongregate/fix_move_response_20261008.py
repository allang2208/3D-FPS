"""Apply the requested 2x movement response, with the original gait reference."""
from pathlib import Path
import json
import unreal as u

if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Preserve the active PIE session before compiling this Blueprint.')
bp=u.load_asset('/Game/Monsters/BoundCongregate/BP_BoundCongregate')
cdo=u.get_default_object(bp.generated_class())
movement=cdo.get_editor_property('character_movement')
before=dict(speed=cdo.get_editor_property('walk_speed'),
            acceleration=movement.get_editor_property('max_acceleration'),
            braking=movement.get_editor_property('braking_deceleration_walking'))
cdo.set_editor_property('walk_speed',120.0)
movement.set_editor_property('max_walk_speed',120.0)
movement.set_editor_property('max_acceleration',300.0)
movement.set_editor_property('braking_deceleration_walking',480.0)
bp.modify()
u.BlueprintEditorLibrary.compile_blueprint(bp)
if not u.EditorLoadingAndSavingUtils.save_packages([bp.get_outermost()],False):
    raise RuntimeError('Movement response save failed.')
cdo=u.get_default_object(bp.generated_class())
report=dict(saved=True,before=before,speed=120,acceleration=300,braking=480,
            animation_reference=cdo.get_editor_property('animation_walk_speed'))
Path('D:/FPS3D/FPSGAME/Saved/bound-movement-response-20261008.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('BOUND_MOVEMENT_RESPONSE_SAVED '+json.dumps(report))
