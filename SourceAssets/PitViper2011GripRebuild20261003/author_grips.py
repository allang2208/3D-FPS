"""Compatibility entry: produce the current VIP and shared longitudinal skins."""
import runpy
from pathlib import Path
O=Path(__file__).parent
for batch in ('PitViper2011ViperLongitudinalGrip20261003','PitViper2011CommonLongitudinalGrips20261003'):
    runpy.run_path(str(O.parent/batch/'author_grip.py'),run_name='__main__')
