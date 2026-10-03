"""Compatibility entry: save the two current grip meshes and private VIP maps."""
import runpy
from pathlib import Path
O=Path(__file__).parent
for batch,entry in (('PitViper2011ViperLongitudinalGrip20261003','import_assets.py'),
                    ('PitViper2011CommonLongitudinalGrips20261003','import_grip.py')):
    runpy.run_path(str(O.parent/batch/entry),run_name='__main__')
