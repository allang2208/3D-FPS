"""Normal editor exit for the updated native modifier and hit snapshot layouts."""
import json
import os
from pathlib import Path
from datetime import datetime
import unreal as u

P=Path(__file__).resolve().parent
receipt=json.loads((P/'install_receipt.json').read_text(encoding='utf-8'))
if not receipt['complete']:raise RuntimeError('Complete rune assets before building.')
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())
pie=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world() is not None
state={'time':datetime.now().isoformat(),'editor_pid':os.getpid(),
       'dirty_packages':[p.get_path_name() for p in dirty],'pie':pie,
       'exit_requested':not dirty and not pie,
       'reason':'Ordinary native build required for new melee modifier and hit-snapshot fields'}
(P/'editor-build-state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
if dirty or pie:
    raise RuntimeError('Editor preserved: active play or unsaved packages. '+json.dumps(state))
print('HIGHLAND_WILD_RUNE_NORMAL_BUILD_CLOSE '+str(os.getpid()))
u.SystemLibrary.quit_editor()
