"""Apply the three Thor modification tiers in the existing editor; no gameplay tests."""
import unreal as u,json
from pathlib import Path
from datetime import datetime
P=Path(__file__).resolve().parent
if Path(u.Paths.project_dir()).resolve()!=Path('D:/FPS3D/FPSGAME').resolve():raise RuntimeError('Unexpected editor project')
log=Path(u.Paths.project_log_dir())/'FPSGAME.log';offset=log.stat().st_size if log.exists() else 0
receipt={'started':datetime.now().isoformat(),'command':'LiveCoding.CompileSync','runtime_tested':False,'base_dll_updated':False,'status':'requested','options':['lei_xi_pommel','lei_ming_rune','hui_xiang_rune']}
(P/'compile_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
u.log('THOR_SPECIAL_TIER_COMPILE_BEGIN')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
u.SystemLibrary.execute_console_command(editor.get_game_world() or editor.get_editor_world(),'LiveCoding.CompileSync')
u.log('THOR_SPECIAL_TIER_COMPILE_RETURNED')
receipt.update(returned=datetime.now().isoformat(),status='compile command returned; see compiler log')
(P/'compile_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
if log.exists():
 with log.open('rb') as f:f.seek(offset);text=f.read().decode('utf-8',errors='replace')
 (P/'editor_compile.log').write_text(text,encoding='utf-8')
print('THOR_SPECIAL_TIER_COMPILE_RETURNED',flush=True)
