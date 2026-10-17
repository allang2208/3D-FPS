import json,copy
from pathlib import Path
O=Path('SourceAssets/M870CommonFurniture20261016');p=Path('Content/ColdSteelData/gunsmith.json');text=p.read_text(encoding='utf-8-sig');d=json.loads(text)
source=next(w for w in d['weapons'] if w['id']=='ue_super90')
a=text.rfind('{',0,text.index('"ue_m870"'));old,n=json.JSONDecoder().raw_decode(text[a:]);new=copy.deepcopy(old)
for slot in ('stock','underbarrel'):
 factory=next(copy.deepcopy(v) for v in old['options'][slot] if v['id']=='false')
 new['options'][slot]=[factory]+[copy.deepcopy(v) for v in source['options'][slot] if v['id']!='false']
 for v in new['options'][slot][1:]:
  v['description']=v.get('description','').replace('SUPER90','M870').replace('Super90','M870').replace('M4A1','M870').replace('HK416','M870')
 if slot not in new['allowed']:new['allowed'].append(slot)
new['allowed']=[s for s in new['allowed'] if s!='reargrip']
new['options'].pop('reargrip',None)
indent=len(text[text.rfind('\n',0,a)+1:a]);rep=json.dumps(new,ensure_ascii=False,indent=2).replace('\n','\n'+' '*indent)
b=O/'Before/gunsmith.json';b.parent.mkdir(exist_ok=True)
if not b.exists():b.write_bytes(p.read_bytes())
p.write_text(text[:a]+rep+text[a+n:],encoding='utf-8')
(O/'catalog_receipt.json').write_text(json.dumps({'weapon':'ue_m870','slots':{s:[v['id'] for v in new['options'][s]] for s in ('stock','underbarrel')},'source':'ue_super90','stats_icons_and_save_ids_reused':True,'runtime_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
p=Path('Source/FPSGAME/Weapons/M870FurnitureAssets.cpp');s=p.read_text()
keys=list(json.loads((O/'models.json').read_text())['parts'])
old='    return TEXT("/Game/Weapons/M870/CommonFurniture20261016/Meshes/SM_M870_")+Part;'
new='\n'.join('    if(Part==TEXT("'+k+'"))return TEXT("/Game/Weapons/M870/CommonFurniture20261016/Meshes/SM_M870_'+k+'");' for k in keys)+'\n    return FString();'
s=s.replace(old,new)
s=s.replace('    return TEXT("/Game/Weapons/M870/CommonFurniture20261016/Profiles/DA_M870_")+Family.ToString();','\n'.join('    if(Family==TEXT("'+k+'"))return TEXT("/Game/Weapons/M870/CommonFurniture20261016/Profiles/DA_M870_'+k+'");' for k in ('vertical','canted','prism','angled'))+'\n    return FString();')
p.write_text(s)
