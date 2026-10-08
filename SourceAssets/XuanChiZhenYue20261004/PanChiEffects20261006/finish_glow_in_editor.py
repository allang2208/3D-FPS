"""Finish this repair in the current editor only after PIE has ended."""
import runpy,json
from datetime import datetime,timezone
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    print('PANCHI_GLOW_WAITING_FOR_PIE_EXIT')
else:
    runpy.run_path(str(P/'install_assets.py'),init_globals={'PANCHI_GUARD_ONLY':True})
    runpy.run_path(str(P/'capture_saved_glow.py'))
    runpy.run_path(str(P/'read_saved_glow.py'))
    (P/'glow-fix-status.json').write_text(json.dumps({'phase':'complete','detail':'Saved in current editor after PIE exit; material capture completed','updated_utc':datetime.now(timezone.utc).isoformat()},indent=2),encoding='utf-8')
    print('PANCHI_GLOW_EDITOR_FINISHED')
