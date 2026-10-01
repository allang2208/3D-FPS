"""Save only Blizzard's cloud system lifetime; do not start or alter gameplay."""
import json
import sys
from pathlib import Path
import unreal as u

root = Path(u.Paths.project_dir())
sys.path.insert(0, str(root / 'Tools/Skills'))
from build_fireball_assets import save
from build_fireball_flight import expression

paths = ['/Game/Skills/Blizzard/ChargedV3/NS_BlizzardGatherCloud',
         '/Game/Skills/Blizzard/ChargedV3/NS_BlizzardStormCloud']
dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(path in dirty for path in paths):
    raise RuntimeError('Preserve unsaved Blizzard cloud assets')
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():
    raise RuntimeError('Preserve the current Blizzard diagnostic cast; save after PIE ends')
for path in paths:
    system = u.load_asset(path)
    if not system:
        raise RuntimeError('Missing Blizzard cloud system: ' + path)
    expression(system, '', 'SystemUpdateScript', 'SystemState', 'Loop Duration',
               'max(.6,User.StormDuration+.6)')
    save(system)
receipt = {'saved_assets': paths, 'system_loop_duration': 'max(.6,User.StormDuration+.6)',
           'missing_cloud_root_cause_confirmed': False, 'gameplay_tested': False, 'rendered': False}
(root / 'Saved/BlizzardCloudVisibility20261001/cloud-lifetime-repair.json').write_text(
    json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('BLIZZARD_CLOUD_LIFETIME_SAVED ' + json.dumps(receipt))
