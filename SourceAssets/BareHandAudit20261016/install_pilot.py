"""Pilot: install the plan on one standalone bare-arm mesh, then read it back into Final/."""
from pathlib import Path
R = Path('D:/FPS3D/FPSGAME/SourceAssets/BareHandAudit20261016')
PILOT = '/Game/Characters/ModularOutfit20260924/BarePalmV7/M4/SK_M4_BareArmsV7.SK_M4_BareArmsV7'
ONLY = [PILOT]
exec(compile((R / 'install_fix.py').read_text(), 'install_fix.py', 'exec'))
SNAP_SUBDIR = 'Final'; ONLY_PATHS = [PILOT]
exec(compile((R / 'snapshot_ue.py').read_text(), 'snapshot_ue.py', 'exec'))
