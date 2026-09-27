"""Compile the existing function-body change in the already open editor."""
from datetime import datetime
from pathlib import Path
import json
import unreal as u

if Path(u.Paths.project_dir()).resolve() != Path('D:/FPS3D/FPSGAME').resolve():
    raise RuntimeError('Unexpected editor project')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
started=datetime.now().isoformat()
u.log('BOW_OPEN_SIGHT_COMPILE_BEGIN '+started)
world=editor.get_game_world() or editor.get_editor_world()
u.SystemLibrary.execute_console_command(world,'LiveCoding.CompileSync')
(Path(__file__).parent/'compile-request.json').write_text(json.dumps({
    'started':started,'returned':datetime.now().isoformat(),'command':'LiveCoding.CompileSync',
    'status':'Compiler output determines success; command return is not confirmation.',
    'runtime_tested':False},indent=2),encoding='utf8')
u.log('BOW_OPEN_SIGHT_COMPILE_RETURNED')
