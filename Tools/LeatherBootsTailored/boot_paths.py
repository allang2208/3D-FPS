import json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/LeatherBootsUpgrade20261022/TailoredV2';OLD=P/'SourceAssets/BrownLeatherSet20261004'
PREVIOUS=P/'SourceAssets/LeatherBootsUpgrade20261022'
DEST='/Game/Characters/ModularOutfit20260924/LeatherBootsUpgrade20261022/TailoredV2'
SLOTS=['AgedSteel','BootLeather','RubberOutsole','WaxedThread','ReinforcedLeather','StackedWelt','DarkLining']
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,d):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
