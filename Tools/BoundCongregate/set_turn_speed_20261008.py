"""Save 50 deg/s turning on the official monster Blueprint; no gameplay test."""
from pathlib import Path
import json
import unreal as u

if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Preserve the active PIE session before compiling this Blueprint.')

bp = u.load_asset('/Game/Monsters/BoundCongregate/BP_BoundCongregate')
cdo = u.get_default_object(bp.generated_class())
movement = cdo.get_editor_property('character_movement')
rotation = movement.get_editor_property('rotation_rate')
previous_yaw = rotation.yaw
rotation.yaw = 50.0
bp.modify()
movement.set_editor_property('rotation_rate', rotation)
u.BlueprintEditorLibrary.compile_blueprint(bp)
if not u.EditorLoadingAndSavingUtils.save_packages([bp.get_outermost()], False):
    raise RuntimeError('Turning speed save failed.')

report = dict(saved=True, previous_yaw_deg_s=previous_yaw,
              yaw_deg_s=50.0, animation_reference_deg_s=14.0,
              animation_rate_at_full_turn=50.0 / 14.0, gameplay_tested=False)
Path('D:/FPS3D/FPSGAME/Saved/bound-turn-speed-20261008.json').write_text(
    json.dumps(report, indent=2), encoding='utf8')
print('BOUND_TURN_SPEED_SAVED ' + json.dumps(report))
