"""Create only new native animation packages using the existing serialized editor bridge."""
import runpy
from pathlib import Path
for script in ('save_chair_reuse.py','read_meshy_bed_saved.py','read_kaitlin_bed_arms.py'):
    runpy.run_path(str(Path(__file__).with_name(script)),init_globals={'FURNITURE_REVISION':'ApartmentLegTransfer20261024R2'})
