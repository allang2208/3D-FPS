"""Publish only the M24 tactical fields, retaining unrelated concurrent work."""
import json,runpy
from pathlib import Path
O=Path(__file__).resolve().parent;P=O.parents[1]
path=P/'Content/ColdSteelData/gunsmith.json'
text=path.read_text(encoding='utf-8-sig');data=json.loads(text)
start=text.rfind('{',0,text.index('"id": "ue_m24"'))
old,length=json.JSONDecoder().raw_decode(text[start:])
row=next(w for w in data['weapons'] if w['id']=='ue_m24')
before=O/'catalog_m24_before.json'
if not before.exists():before.write_text(json.dumps(old,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
runpy.run_path(str(P/'SourceAssets/M24AdvancedAction20261029/catalog.py'))['apply_tactical'](data,row)
indent=' '*len(text[text.rfind('\n',0,start)+1:start])
block=json.dumps(row,ensure_ascii=False,indent=2).replace('\n','\n'+indent)
if path.read_text(encoding='utf-8-sig')!=text:raise RuntimeError('Catalog changed during publication; preserve current file.')
path.write_text(text[:start]+block+text[start+length:],encoding='utf-8')
(O/'catalog_receipt.json').write_text(json.dumps({'weapon':'ue_m24','slot':'tactical','options':[o['id'] for o in row['options']['tactical']],'advanced_body_stats':next(o['stats'] for o in row['options']['body'] if o['id']=='m24_advanced_action'),'saved':True,'runtime_tested':False},indent=2),encoding='utf-8')
print('M24_TACTICAL_CATALOG_SAVED')
