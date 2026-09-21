"""Resume the known V06 source import after fixing its native bind operation."""
from pathlib import Path
WITCH_V06_RESUME_SOURCE=True
exec(compile(Path('D:/FPS3D/FPSGAME/Tools/Witch/import_clean_robe_v06.py').read_text(encoding='utf-8'),'import_clean_robe_v06.py','exec'))
