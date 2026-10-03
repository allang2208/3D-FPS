"""Exit normally only when the editor has no unsaved work or active PIE."""
import datetime,json
from pathlib import Path
import unreal as u
P=Path(__file__).parent
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
dirty += [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
pie=u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor()
state={'time':datetime.datetime.now().isoformat(),'dirty_packages':sorted(set(dirty)),
       'pie':pie,'exit_requested':not dirty and not pie}
(P/'normal-build-close.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
if dirty or pie:
    raise RuntimeError('Editor retained: active PIE or unsaved packages. '+json.dumps(state,ensure_ascii=False))
u.log('SWORD_OVERHEAD_NORMAL_BUILD_CLEAN_EXIT')
u.SystemLibrary.quit_editor()
