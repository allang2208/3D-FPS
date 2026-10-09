"""Export current M-05 motion inputs without starting playback."""
from pathlib import Path
source=Path('D:/FPS3D/FPSGAME/Tools/FacelessResearcher/export_waist_inputs_v03.py').read_text(encoding='utf-8')
source=source.replace("ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessResearcher20261009/V03')", "ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessResearcher20261009/V04')")
exec(compile(source,'researcher_v04_inputs','exec'))
