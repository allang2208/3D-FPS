"""Install every remaining plan, then read all installed meshes back into Final/."""
import json
from pathlib import Path
R = Path('D:/FPS3D/FPSGAME/SourceAssets/BareHandAudit20261016')
exec(compile((R / 'install_fix.py').read_text(), 'install_fix.py', 'exec'))
SNAP_SUBDIR = 'Final'
ONLY_PATHS = [json.loads(f.read_text())['path'] for f in (R / 'Installed').glob('*.json') if not f.name.endswith('.failed.json')]
exec(compile((R / 'snapshot_ue.py').read_text(), 'snapshot_ue.py', 'exec'))
