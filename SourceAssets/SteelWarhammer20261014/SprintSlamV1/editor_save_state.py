import json,unreal as u
from pathlib import Path
p=Path(__file__).resolve().parent
state={'project':u.Paths.project_dir(),
       'dirty_content':[x.get_path_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
       'dirty_maps':[x.get_path_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]}
(p/'editor_save_state.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
print(json.dumps(state))
