"""Close only a fully saved, non-PIE editor for the required persistent clock build."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
status=dict(dirty_packages=len(dirty),pie_active=bool(world),close_requested=False)
if not dirty and not world:
    status['close_requested']=True
(O/'base_build_handoff.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
print(json.dumps(status),flush=True)
if status['close_requested']:
    u.SystemLibrary.execute_console_command(None,'QUIT_EDITOR')
