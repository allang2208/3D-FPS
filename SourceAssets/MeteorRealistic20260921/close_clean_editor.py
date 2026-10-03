import json
from pathlib import Path
import unreal as u
content=u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
maps=u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
state={'dirty_content':[p.get_name() for p in content],'dirty_maps':[p.get_name() for p in maps],
       'action':'leave_open' if content or maps else 'normal_quit_for_native_build'}
(Path(u.Paths.project_dir()).resolve()/'SourceAssets/MeteorRealistic20260921/close-state.json').write_text(json.dumps(state,indent=2),encoding='utf8')
print(state)
if not content and not maps:u.SystemLibrary.quit_editor()
