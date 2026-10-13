"""Opt-in 10-second RDG capture in an existing, user-authorized PIE session.

Only run when a resource capture is requested; does not launch or stop PIE.
"""
from pathlib import Path
import unreal as u

script = Path(u.Paths.project_dir()) / 'Tools/Performance/capture_dungeon_entry.py'
exec(compile(script.read_text(encoding='utf-8-sig'), str(script), 'exec'),
     {'__name__': '__main__', 'DUNGEON_CAPTURE_RDG': True})
