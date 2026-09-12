"""Add the independent visual option without inventing numerical bonuses."""
import json
from pathlib import Path
P=Path(__file__).parent;target=P.parent.parent/'Content/ColdSteelData/gunsmith.json'
s=target.read_text(encoding='utf-8-sig');doc=json.loads(s)
for weapon in doc['weapons']:
 if weapon['id'] not in ['ue_m4a1','ue_akm']:continue
 # The existing catalog names its option groups explicitly; retain all siblings.
 groups=weapon.get('attachments',weapon.get('options',{}))
 if 'stock' not in groups:
  groups=next(v for v in weapon.values() if isinstance(v,dict) and isinstance(v.get('stock'),list))
 stocks=groups['stock'];entry={'id':'qr_performance','name':'QR高性能后托','description':'宽贴腮面、镂空斜撑后架与橡胶肩垫，使用对应枪型的安装接口。','effects':[],'stats':{}}
 for i,old in enumerate(stocks):
  if old['id']=='qr_performance':stocks[i]=entry;break
 else:stocks.append(entry)
target.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Catalog updated: M4 and AKM / qr_performance; factory statistics retained')
