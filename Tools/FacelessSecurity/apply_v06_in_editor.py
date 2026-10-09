"""End an active play session if needed, otherwise perform the asset import."""
import unreal as u
from pathlib import Path
level=u.get_editor_subsystem(u.LevelEditorSubsystem)
if level.is_in_play_in_editor():
    level.editor_request_end_play()
    print('SECURITY_V06_PIE_STOP_REQUESTED_NO_IMPORT: end-play will complete on the next editor tick; rerun this import entry after it completes.')
else:
    path=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/import_security_v06.py')
    exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'))
