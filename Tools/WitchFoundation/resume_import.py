"""Resume the interrupted, task-owned first import after correcting its API call."""
from pathlib import Path
WITCH_FOUNDATION_RESUME_OWN_IMPORT=True
exec(compile(Path('D:/FPS3D/FPSGAME/Tools/WitchFoundation/import_candidate.py').read_text(encoding='utf-8'),
             'D:/FPS3D/FPSGAME/Tools/WitchFoundation/import_candidate.py','exec'))
