import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('publish_apartment_meshy_bed.py')),init_globals={
    'FURNITURE_REVISION':'ApartmentFastRest20261024R2','CHANGED_CAMERAS_ONLY':True})
