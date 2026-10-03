"""Normal exit for changed static catalogs, only with no play or unsaved work."""
import json
from datetime import datetime
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
receipt = json.loads((P / 'install_receipt.json').read_text(encoding='utf-8'))
if not receipt['complete']:
    raise RuntimeError('Broadblade installation is incomplete; do not restart.')
dirty = list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages()) + list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())
pie = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world() is not None
state = {'time': datetime.now().isoformat(), 'dirty_packages': [p.get_path_name() for p in dirty],
         'pie': pie, 'exit_requested': not dirty and not pie,
         'reason': 'Refresh process-cached modular sword catalog after new broadblade option'}
(P / 'editor-refresh.json').write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
if not dirty and not pie:
    u.log('HIGHLAND_BROADBLADE_NORMAL_CATALOG_REFRESH')
    u.SystemLibrary.quit_editor()
else:
    u.log('HIGHLAND_BROADBLADE_INSTALLED_EDITOR_REFRESH_DEFERRED')
print(json.dumps(state, ensure_ascii=False))
