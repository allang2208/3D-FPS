import json,os
from pathlib import Path
import unreal
dirty=unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()+unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
game=bool(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world())
state={'pid':os.getpid(),'dirty':[p.get_name() for p in dirty],'game_world':game,'closing':not dirty and not game}
(Path(unreal.Paths.project_dir())/'SourceAssets/CastingPalmPush20260920/WristRepairV5/native-close.json').write_text(json.dumps(state),encoding='utf-8')
print(json.dumps(state))
if state['closing']:unreal.SystemLibrary.quit_editor()
