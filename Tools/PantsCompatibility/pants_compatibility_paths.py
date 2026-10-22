"""Distinct module name for safe reuse inside the shared UE Python interpreter."""
import json,os
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME')
R=Path(os.environ.get('FPS_PANTS_FIT_ROOT',str(P/'SourceAssets/PantsCompatibility20261022')))
DEST='/Game/Characters/ModularOutfit20260924/PantsCompatibility20261022'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,d):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
def disk(path):return P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
