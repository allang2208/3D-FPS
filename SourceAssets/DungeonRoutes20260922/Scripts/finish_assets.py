"""Finish the revised through-room import and write the production module catalogue."""
import runpy,gc
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for name in ('import_through_room.py','build_catalog.py'):
    state=runpy.run_path(str(ROOT/'Scripts'/name),run_name='__main__')
    del state
    gc.collect()
print('ROUTE_ASSETS_AND_CATALOG_READY')
