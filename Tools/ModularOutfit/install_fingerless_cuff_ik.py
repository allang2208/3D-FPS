"""Save the accepted fixed-hand cuff-clearance candidates, then read actual assets."""
import json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2'
for folder in ('CuffArmClearance','CuffShoulderClearance'):
    manifest=json.loads((R/folder/'manifest.json').read_text())
    if any(v['remaining_sample_cross_mm']>.03 for v in manifest):raise RuntimeError('Unresolved '+folder)
    exec((P/'Tools/ModularOutfit/install_fingerless_tip_clearance.py').read_text(),dict(CORRECTION_DIRECTORY=folder))
exec((P/'Tools/ModularOutfit/read_final_fingerless_clearance.py').read_text())
