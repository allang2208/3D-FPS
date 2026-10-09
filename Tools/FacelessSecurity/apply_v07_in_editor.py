"""Perform the targeted mesh replacement after ending active PIE if needed."""
import unreal as u
from pathlib import Path
read_path=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/read_active_v07.py')
exec(compile(read_path.read_text(encoding='utf-8'),str(read_path),'exec'))
if cdo.get_editor_property('visual_mesh').get_name()!='SK_FacelessSecurity_V06':
    raise RuntimeError('The active security mesh is no longer V06; preserve the current asset instead of replacing it with a stale source')
level=u.get_editor_subsystem(u.LevelEditorSubsystem)
if level.is_in_play_in_editor():
    level.editor_request_end_play()
    print('SECURITY_V07_PIE_STOP_REQUESTED_NO_IMPORT')
else:
    path=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/import_fragment_v07.py')
    exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'))
