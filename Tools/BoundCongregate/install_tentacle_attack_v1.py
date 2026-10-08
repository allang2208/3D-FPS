"""Persist the native tentacle attack tuning on the existing F6 blueprint."""
from pathlib import Path
import json
import unreal as u

out = Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006/TentacleAttackV1')
out.mkdir(parents=True, exist_ok=True)
path = '/Game/Monsters/BoundCongregate/BP_BoundCongregate'
dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if path in dirty:
    raise RuntimeError('Preserve unsaved BoundCongregate blueprint edits')
bp = u.load_asset(path)
if not bp:
    raise RuntimeError('Production BoundCongregate blueprint is missing')
cdo = u.get_default_object(bp.generated_class())
tuning = dict(tentacle_range=360., tentacle_cooldown=9., tentacle_windup_seconds=.75,
              tentacle_strike_seconds=.48, tentacle_wrap_seconds=.4,
              tentacle_hold_seconds=3.5, tentacle_recover_seconds=.65,
              tentacle_impact_damage=20., tentacle_tick_damage=8.,
              tentacle_damage_interval=.5, tentacle_pull_speed=65.)
for key, value in tuning.items():
    cdo.set_editor_property(key, value)
u.BlueprintEditorLibrary.compile_blueprint(bp)
if not u.EditorAssetLibrary.save_loaded_asset(bp, False):
    raise RuntimeError('Failed to save BoundCongregate tentacle settings')
(out / 'delivery.json').write_text(json.dumps(dict(
    saved=True, blueprint=bp.get_path_name(), tuning=tuning,
    animation='native 13-bone curl/feeler control on existing RigV3 mesh',
    tested=False, editor_window_opened=False), indent=2), encoding='utf-8')
print('BOUND_CONGREGATE_TENTACLE_V1_SAVED', flush=True)
