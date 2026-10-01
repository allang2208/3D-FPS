"""Build the refined groups and shared cargo label fix; no scene rendering."""
import json,runpy,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];HALL=ROOT.parent;PROJECT=HALL.parents[1];OUT=ROOT/'Authored'
OUT.mkdir(exist_ok=True)
shutil.copy2(HALL/'Authored/atlas.json',OUT/'atlas.json')
runpy.run_path(str(HALL/'Scripts/author_warehouse.py'),init_globals=dict(EXPORT_OUT=OUT,EXPORT_SUFFIX='_V2',
    EXPORT_KINDS={'Racks','RackHardware','RackBraces','RackDecks','RackGuards','Hoist','HoistChain','HoistHook','FloorMarkings','Signs'}))
props=runpy.run_path(str(PROJECT/'SourceAssets/DungeonFacilityPropPolish20260928/Scripts/author_props.py'))
props['build_all'](output_dir=ROOT/'Cargo',only={'CargoStack'})
print('WAREHOUSE_REFINEMENT_AUTHORED')
