"""Import and prepare catalogue after the native build. All editor writes use one bridge batch."""
import runpy,gc
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def stage(path):
    state=runpy.run_path(str(path),run_name='__main__')
    del state;gc.collect()
stage(ROOT/'Scripts/import_threshold.py')
stage(ROOT/'Scripts/import_through_room.py')
stage(ROOT.parent/'DungeonDoorTransitions20260922/Scripts/import_transition.py')
stage(ROOT.parent/'DungeonTreasure20260922/Scripts/import_treasure.py')
stage(ROOT/'Scripts/route_fluid_materials.py')
stage(ROOT.parent/'DungeonSlimeSheet20260922/Scripts/install_scene.py')
stage(ROOT/'Scripts/read_start_layout.py')
stage(ROOT/'Scripts/build_catalog.py')
print('ROUTE_ASSETS_AND_CATALOG_READY')
