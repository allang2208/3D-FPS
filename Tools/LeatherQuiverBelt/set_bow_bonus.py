"""Set quiver-belt archery bonuses, preserving all other item fields."""
import json,os,sys,uuid
from pathlib import Path
P=Path(__file__).resolve().parents[2];R=P/'SourceAssets/LeatherQuiverBelt20261025';OUT=R/'BowBonus20261025'
sys.path.insert(0,str(P/'Tools/BrownLeatherSet'));import json_entries
fields=dict(bonusStats=dict(bowNockSpeed=.50,bowDrawSpeed=.05),
    bonusPerEnhance=dict(bowNockSpeed=.02,bowDrawSpeed=.01),enhancement=dict(maxLevel=15))
path=P/'Content/ColdSteelData/items.json';raw=path.read_bytes();text=raw.decode('utf-8-sig');key='ue_leather_quiver_belt';item=json.loads(text)[key]
for field,value in fields.items():item.setdefault(field,{}).update(value)
updated=json_entries.replace(text,[key],item)
temp=path.with_name(path.name+'.quiver-bonus-'+uuid.uuid4().hex+'.tmp')
temp.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+updated.encode('utf-8'))
if path.read_bytes()!=raw:raise RuntimeError('Item catalog changed during scoped update; retain current file')
os.replace(temp,path)
OUT.mkdir(exist_ok=True)
(OUT/'catalog_receipt.json').write_text(json.dumps(dict(saved=True,item=key,fields=fields,
    maximum_bonus=dict(bowNockSpeed=.80,bowDrawSpeed=.20),speed_semantics='time divided by (1 + speed bonus)',
    nocking_paths=['manual R','quick take','chain take'],runtime_tested=False,multiplayer_tested=False),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
published=R/'published.json'
if published.exists():
    report=json.loads(published.read_text(encoding='utf-8-sig'))
    for field,value in fields.items():report['item'].setdefault(field,{}).update(value)
    report['archery_bonus_receipt']='BowBonus20261025/catalog_receipt.json'
    published.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('QUIVER_ARCHERY_BONUSES_SAVED: nock +50% +2pp/level; draw +5% +1pp/level; cap +15')
