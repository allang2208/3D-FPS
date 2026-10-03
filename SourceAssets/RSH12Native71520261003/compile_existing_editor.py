"""Compile these native edits in the existing editor; do not start PIE."""
import unreal as u,json
from pathlib import Path
from datetime import datetime,timezone
O=Path(__file__).parent
if Path(u.Paths.project_dir()).resolve()!=O.parents[1].resolve():raise RuntimeError('Unexpected project')
if u.EditorLevelLibrary.get_game_world():raise RuntimeError('Preserve current PIE; compile after the user ends it')
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
(O/'compile_request.json').write_text(json.dumps(dict(requested_at_utc=datetime.now(timezone.utc).isoformat(),mode='existing-editor LiveCoding.CompileSync',runtime_tested=False),indent=2))
print('RSH12_NATIVE_715_COMPILE_BEGIN',flush=True)
u.SystemLibrary.execute_console_command(world,'LiveCoding.CompileSync')
print('RSH12_NATIVE_715_COMPILE_RETURNED; build status is recorded in the actual Live Coding log',flush=True)
