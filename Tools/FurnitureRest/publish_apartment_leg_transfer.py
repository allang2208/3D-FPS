"""Publish the two saved apartment transitions and their native camera clocks."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('publish_apartment_meshy_bed.py')),init_globals={
    'FURNITURE_REVISION':'ApartmentLegTransfer20261024R2','CHANGED_CAMERAS_ONLY':True})
