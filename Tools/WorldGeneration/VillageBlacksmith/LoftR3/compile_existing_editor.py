"""Compile the regenerated village vegetation reservations in the already-open editor."""
from pathlib import Path
from datetime import datetime
import json
import unreal as u
OUT=Path(__file__).resolve().parents[4]/'SourceAssets/HillsVillageBlacksmith20261117/LoftR3'
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world():raise RuntimeError('Preserve active PIE')
started=datetime.now().isoformat()
u.SystemLibrary.execute_console_command(editor.get_editor_world(),'LiveCoding.CompileSync')
(OUT/'compile-request.json').write_text(json.dumps(dict(started=started,returned=datetime.now().isoformat(),source='TemperateVillageLayout.inl',status='See LiveCoding compiler output',runtime_tested=False),indent=2),encoding='utf-8')
u.log('BLACKSMITH_LOFT_R3_COMPILE_RETURNED')
