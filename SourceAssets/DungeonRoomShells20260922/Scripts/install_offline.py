"""Finish authoring while the interactive editor is closed; no tests or renders."""
from pathlib import Path
HEADLESS_AUTHORING=True
ROOM_IDS=['Drainage','ShoredBreach','Distribution_Drainage','Drainage_ShoredBreach']
scripts=Path(__file__).parent
for filename in ['import_rooms.py','install_rooms.py']:
    source=scripts/filename
    exec(compile(source.read_text(encoding='utf-8'),str(source),'exec'))
