"""Apply through the current editor's existing mutual-exclusion bridge."""
import unreal as u
from pathlib import Path
bp=u.load_asset('/Game/Monsters/FacelessSecurity/BP_FacelessSecurity');cdo=u.get_default_object(bp.generated_class())
current=cdo.get_editor_property('visual_mesh').get_name()
if current!='SK_FacelessSecurity_V09':raise RuntimeError('Source mesh changed from V09: '+current)
if cdo.get_editor_property('attack_clip').get_name()!='A_Security_Male_V06_attack':raise RuntimeError('Source attack changed from V06')
level=u.get_editor_subsystem(u.LevelEditorSubsystem)
if level.is_in_play_in_editor():
    level.editor_request_end_play();print('SECURITY_V10_PIE_STOP_REQUESTED_NO_IMPORT')
else:
    path=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/import_recovery_v10.py');exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'))
