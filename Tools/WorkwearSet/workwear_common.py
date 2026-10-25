import hashlib,json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME')
R=P/'SourceAssets/WorkwearSet20261024'
DEST='/Game/Characters/ModularOutfit20260924/WorkwearSet20261024'
KEY='ue_work_jacket'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,d):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
def compact(p,d):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
