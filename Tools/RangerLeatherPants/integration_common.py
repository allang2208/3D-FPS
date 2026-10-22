"""Paths for the selected RealisticCutV3 integration; no UE or authoring side effects."""
import json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME')
SOURCE=P/'SourceAssets/RangerLeatherPants20261021/RealisticCutV3'
R=SOURCE/'Integration20261022'
DEST='/Game/Characters/ModularOutfit20260924/RangerLeatherPants20261021/RealisticCutV3'
PROFILES=('Jason','Jason_ShortBootsFit','Jason_HighBootsFit')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,d):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
