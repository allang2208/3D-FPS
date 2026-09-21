"""Rebuild the existing V06 mesh and cage with matched FBX centimetre units."""
from pathlib import Path
WITCH_V06_REPORT_FILE='D:/FPS3D/FPSGAME/SourceAssets/WitchMeshy20260919/ue_clean_robe_v06_visibility_fix.json'
exec(compile(Path('D:/FPS3D/FPSGAME/Tools/Witch/import_clean_robe_v06.py').read_text(encoding='utf-8'),'import_clean_robe_v06.py','exec'))
