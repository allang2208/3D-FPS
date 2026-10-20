"""Install ue_plans_m870.json (receipts in InstalledM870/), then read the meshes back into FinalM870/."""
import json
from pathlib import Path
R = Path('D:/FPS3D/FPSGAME/SourceAssets/BareHandAudit20261016')
PLANS_FILE = 'ue_plans_m870.json'; DONE_SUBDIR = 'InstalledM870'
exec(compile((R / 'install_fix.py').read_text(), 'install_fix.py', 'exec'))
SNAP_SUBDIR = 'FinalM870'
ONLY_PATHS = [p['path'] for p in json.loads((R / PLANS_FILE).read_text())]
exec(compile((R / 'snapshot_ue.py').read_text(), 'snapshot_ue.py', 'exec'))
