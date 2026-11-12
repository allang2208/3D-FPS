import runpy
import json
from pathlib import Path
receipt=Path('D:/FPS3D/FPSGAME/SourceAssets/TemperateForestAtmosphere20261110/Receipts/FPSGAMEEditor-build.json')
if not receipt.exists() or json.loads(receipt.read_text(encoding='utf-8-sig')).get('exit_code')!=0:
    raise RuntimeError('Complete the atmosphere native build before saving assets')
runpy.run_path('D:/FPS3D/FPSGAME/Tools/WorldGeneration/build_temperate_forest_atmosphere.py',run_name='__main__')
