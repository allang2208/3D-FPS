"""Headless authoring entry: each bounded import writes its own completion state."""
from pathlib import Path
import json
source=Path('D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260924')
script=Path('D:/FPS3D/FPSGAME/Tools/ModularOutfit/import_equipment.py')
for batch in range(6):
    exec(compile(script.read_text(encoding='utf-8'),str(script),'exec'),{'__name__':'__main__'})
    current=json.loads((source/'imported.json').read_text(encoding='utf-8'))
    expected=json.loads((source/'authored.json').read_text(encoding='utf-8'))
    if set(current['profiles'])==set(expected):break
else:raise RuntimeError('Outfit authoring did not finish all profiles')
print('ALL_OUTFIT_ASSETS_SAVED',len(current['profiles']))
