"""Save exact capture/movement tuning without replacing accepted model/clips."""
from pathlib import Path
import json,shutil
import unreal as u

project=Path('D:/FPS3D/FPSGAME')
out=project/'SourceAssets/BoundCongregateMeshy20261006/CaptureV30';out.mkdir(exist_ok=True)
base=json.loads((out/'before_values.json').read_text(encoding='utf8'))
path='/Game/Monsters/BoundCongregate/BP_BoundCongregate'
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('End PIE before saving tuning')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if path in dirty:raise RuntimeError('Preserve the unsaved monster blueprint')
bp=u.load_asset(path);cdo=u.get_default_object(bp.generated_class());move=cdo.get_editor_property('character_movement')
backup=out/'before';backup.mkdir(exist_ok=True)
source=project/'Content/Monsters/BoundCongregate/BP_BoundCongregate.uasset'
if not (backup/source.name).exists():shutil.copy2(source,backup/source.name)
values={'walk_speed':base['walk_speed']*2,'tentacle_pull_speed':base['tentacle_pull_speed']*3,
        'tentacle_max_health':300.}
for key,value in values.items():
    if key in base and min(abs(cdo.get_editor_property(key)-base[key]),abs(cdo.get_editor_property(key)-value))>.001:
        raise RuntimeError('Changed tuning must be preserved: '+key)
    cdo.set_editor_property(key,value)
move.set_editor_property('max_walk_speed',values['walk_speed'])
rotation=move.get_editor_property('rotation_rate');rotation.yaw=base['rotation_yaw']*2
move.set_editor_property('rotation_rate',rotation)
move.set_editor_property('max_acceleration',base['max_acceleration']*2)
move.set_editor_property('braking_deceleration_walking',base['braking_deceleration_walking']*2)
u.BlueprintEditorLibrary.compile_blueprint(bp)
if not u.EditorAssetLibrary.save_loaded_asset(bp,False):raise RuntimeError('Blueprint save failed')
result=dict(saved=True,gameplay_tested=False,tuning=values,turn_speed=rotation.yaw,
    retained_visual=cdo.get_editor_property('visual_mesh').get_path_name(),
    retained_flurry=cdo.get_editor_property('flurry_clip').get_path_name(),
    retained_bite=cdo.get_editor_property('bite_clip').get_path_name(),
    bleed_stacks=3,cripple_seconds=5,tentacle_health=300,
    capture='persistent; F three contacts, firearm depletion or close bite handoff; death/destruction cleanup')
(out/'delivery.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print('BOUND_CAPTURE_V30_SAVED '+json.dumps(result),flush=True)
