"""Read the current M870 skin meshes (changed by the M870 session after the V8 pass) into SnapshotsM870/."""
from pathlib import Path
R = Path('D:/FPS3D/FPSGAME/SourceAssets/BareHandAudit20261016')
SNAP_SUBDIR = 'SnapshotsM870'
ONLY_PATHS = ['/Game/Weapons/M870/Tactical20261015/SK_M870_V7.SK_M870_V7',
              '/Game/Weapons/M870/Arms20261016/SK_M870_BareArmsV7.SK_M870_BareArmsV7']
exec(compile((R / 'snapshot_ue.py').read_text(), 'snapshot_ue.py', 'exec'))
