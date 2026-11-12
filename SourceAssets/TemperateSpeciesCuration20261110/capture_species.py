"""Read the actual biome palette without loading a map or running gameplay."""
import json
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/TemperateSpeciesCuration20261110')
da=u.load_asset('/Game/WorldGeneration/TemperateHills/DA_TemperateHillsStreaming')
fields=('trees','forest_saplings','forest_shrubs','forest_ferns','shrubs','grass','grass_accents',
        'meadow_flowers','river_ground_cover','river_reeds','river_bank_grasses','river_understory','backdrop_trees')
report={'asset':da.get_path_name(),'fields':{},'game_run':False,'assets_saved':False}
for field in fields:
    report['fields'][field]=[obj.get_path_name() for obj in da.get_editor_property(field)]
report['finished_at']=datetime.now().astimezone().isoformat()
(ROOT/'Receipts/species-before.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('HILLS_PALETTE_READ '+str({k:len(v) for k,v in report['fields'].items()}))
