"""Apply through the already-running editor; do not launch or restart it."""
import unreal as u
from pathlib import Path
bp=u.load_asset('/Game/Monsters/FacelessSecurity/BP_FacelessSecurity');cdo=u.get_default_object(bp.generated_class())
current=cdo.get_editor_property('visual_mesh').get_name()
if current!='SK_FacelessSecurity_V08':raise RuntimeError('Active mesh changed from V08: '+current)
level=u.get_editor_subsystem(u.LevelEditorSubsystem)
if level.is_in_play_in_editor():
    level.editor_request_end_play();print('SECURITY_V09_PIE_STOP_REQUESTED_NO_IMPORT')
else:
    path=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/import_native_uniform_v09.py')
    exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'))
