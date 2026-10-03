"""Normal shutdown for the user-authorized native build; never discard edits."""
import json
from pathlib import Path
import unreal

content = unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
maps = unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
state = {
    'dirty_content': [p.get_name() for p in content],
    'dirty_maps': [p.get_name() for p in maps],
    'action': 'leave_open' if content or maps else 'normal_quit',
}
Path(unreal.Paths.project_dir(), 'SourceAssets/FireMagicPolish20260921/close-editor-state.json').write_text(json.dumps(state, indent=2), encoding='utf8')
print(state)
if not content and not maps:
    unreal.SystemLibrary.quit_editor()
