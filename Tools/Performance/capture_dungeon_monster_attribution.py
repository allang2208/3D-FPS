"""Arm the opt-in AI/morph capture in an existing editor before user-started PIE.

Requires the MonsterCaptureVersion=1 native build. Records normal quality and
combat for 40 seconds after the first staff wave, then saves trace + F6 JSON.
Does not launch/stop PIE or disable AI, movement, clothing, shadows or ray tracing.
"""
from pathlib import Path
import unreal as u

script = Path(u.Paths.project_dir()) / 'Tools/Performance/capture_dungeon_entry.py'
exec(compile(script.read_text(encoding='utf-8-sig'), str(script), 'exec'),
     {'__name__': '__main__', 'DUNGEON_CAPTURE_MONSTERS': True})
