"""Apply the existing arrow recovery function changes to the open editor."""
from datetime import datetime
from pathlib import Path
import json
import unreal as u

if Path(u.Paths.project_dir()).resolve()!=Path('D:/FPS3D/FPSGAME').resolve():
    raise RuntimeError('Unexpected editor project')
out=Path('D:/FPS3D/FPSGAME/Saved/BowArrowRecovery20260927')
out.mkdir(parents=True,exist_ok=True)
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=editor.get_game_world() or editor.get_editor_world()
started=datetime.now().isoformat()
u.log('BOW_ARROW_RECOVERY_COMPILE_BEGIN '+started)
u.SystemLibrary.execute_console_command(world,'LiveCoding.CompileSync')
(out/'compile-request.json').write_text(json.dumps({
    'started':started,'returned':datetime.now().isoformat(),
    'command':'LiveCoding.CompileSync','source':'Source/FPSGAME/Weapons/Bow/BowArrow.cpp',
    'runtime_tested':False,'status':'Compiler output determines success'},indent=2),encoding='utf8')
u.log('BOW_ARROW_RECOVERY_COMPILE_RETURNED')
