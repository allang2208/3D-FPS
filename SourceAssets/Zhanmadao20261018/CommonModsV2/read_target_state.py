import json
from pathlib import Path
import unreal as u
p=Path(__file__).resolve().parent
editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
state={'project':u.Paths.project_dir(),'is_playing':bool(editor and editor.is_in_play_in_editor()),
       'has_level_editor_subsystem':editor is not None,
       'has_unreal_editor_subsystem':u.get_editor_subsystem(u.UnrealEditorSubsystem) is not None,
       'command_line':u.SystemLibrary.get_command_line(),
       'dirty_target_packages':[x.get_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
           if '/Zhanmadao20261018/' in x.get_name() or '/ue_zhanmadao_' in x.get_name()]}
(p/'target_state.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
print('ZHANMADAO_TARGET_STATE '+json.dumps(state))
