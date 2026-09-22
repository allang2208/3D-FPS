"""Reuse the known UE capture job with a separate revision output gallery."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];S=ROOT/'Scripts'
script=(S/'capture_v2.py').read_text(encoding='utf-8')
script=script.replace("Previews/DungeonAtmosphereV2_20260921'","Previews/DungeonAtmosphereV2_20260921/TilePolish'")
script=script.replace('Receipts/capture-state.json','Receipts/tile-polish-capture-state.json')
start=script.index('VIEWS=[');end=script.index('\nAA=',start)
script=script[:start]+'''VIEWS=[
    ('01_corridor',[180,-210,165],[2050,-210,175],82),
    ('02_mortar_and_fragments',[320,-245,142],[415,-385,107],63),
    ('03_ceramic_detail',[433,-313,133],[444,-385,116],50),
    ('04_workshop_wall',[580,35,160],[651,403,120],70),
    ('05_damp_wall',[222,-132,136],[150,-15,90],65),
]'''+script[end:]
(S/'capture_tile_polish.py').write_text(script,encoding='utf-8')
wrapper=(S/'capture_v2.ps1').read_text(encoding='utf-8')
wrapper=wrapper.replace('Receipts/capture-state.json','Receipts/tile-polish-capture-state.json').replace('bridge-capture-','bridge-tile-capture-').replace("'capture_v2.py'","'capture_tile_polish.py'")
(S/'capture_tile_polish.ps1').write_text(wrapper,encoding='utf-8')
