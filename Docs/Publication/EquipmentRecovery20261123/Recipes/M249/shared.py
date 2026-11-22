from pathlib import Path
import json,re,hashlib,os,sys,zipfile,shutil
from collections import Counter,defaultdict
W=Path(__file__).resolve().parent; R=Path('D:/FPS3D/FPSGAME'); S=R/'SourceAssets/M249Orpind20261107'; C=R/'Content'
REC=Path('F:/FPSGAME-Recovery-Work-20261120');Y=Path('Y:/FPSGAME_恢复_20261120')
def read(p):return json.loads(Path(p).read_bytes().decode('utf-8-sig'))
def write(p,d):(W/p).write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def game(pkg):return 'Content/'+pkg.removeprefix('/Game/').split('.')[0]+'.uasset'
def own(k):return k.startswith('/Game/') and ('/M249/' in k or 'm249' in k.rsplit('/',1)[-1].lower())
