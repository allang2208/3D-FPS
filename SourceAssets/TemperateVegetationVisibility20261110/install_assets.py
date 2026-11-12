import json
import runpy
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME')
receipt=root/'SourceAssets/TemperateVegetationVisibility20261110/Receipts/FPSGAMEEditor-build.json'
if not receipt.exists() or json.loads(receipt.read_text(encoding='utf-8-sig')).get('exit_code')!=0:
    raise RuntimeError('Build the matching native authoring bridge before saving visibility assets')
runpy.run_path(str(root/'Tools/WorldGeneration/fix_temperate_vegetation_visibility.py'),run_name='__main__')
