"""Exit normally only while the editor has no active play or unsaved packages."""
import json
from datetime import datetime
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())
pie=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world() is not None
state={'time':datetime.now().isoformat(),'dirty_packages':[p.get_path_name() for p in dirty],'pie':pie,'exit_requested':not dirty and not pie}
(P/'normal-build-close.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
if dirty or pie:raise RuntimeError('Editor kept open due to active play or unsaved work: '+json.dumps(state))
u.log('HIGHLAND_INTEGRATION_NORMAL_BUILD_CLOSE')
u.SystemLibrary.quit_editor()
