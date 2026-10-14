from pathlib import Path
import json,hashlib,datetime
W=Path(__file__).resolve().parent;P=Path('D:/FPS3D/FPSGAME');rel='Source/FPSGAME/UI/ColdSteelWoodworkingWidget.cpp'
r=json.loads((W/'code_publish_receipt.json').read_text());rec=next(x for x in r['files'] if x['path']==rel)
p=P/rel;assert hashlib.sha256(p.read_bytes()).hexdigest()==rec['sha256']
s=p.read_text(encoding='utf-8');line='#include "../Building/WoodworkingSawVisualComponent.h"\n';assert s.startswith(line)
s=s[len(line):];anchor='#include "ColdSteelWoodworkingWidget.h"\n';assert s.startswith(anchor)
s=s.replace(anchor,anchor+line,1);p.write_text(s,encoding='utf-8');(W/'Staged'/rel).write_text(s,encoding='utf-8')
rec['sha256']=hashlib.sha256(p.read_bytes()).hexdigest();r['include_fix_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
(W/'code_publish_receipt.json').write_text(json.dumps(r,indent=2));print('INCLUDE_ORDER_FIXED')
