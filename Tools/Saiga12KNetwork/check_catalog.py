"""S12K-only catalog, references and requested modification contracts."""
import json,hashlib
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KNetwork20261019'
catalog=json.loads((P/'Content/ColdSteelData/gunsmith.json').read_text(encoding='utf-8-sig'))
w=next(x for x in catalog['weapons'] if x['id']=='ue_saiga12k')
root='Weapons/Saiga12K/Detail20261018';rows=[]
def check(ok,label,detail=None):rows.append({'case':label,'passed':bool(ok),'detail':detail})
def asset(path):return (P/'Content'/(path+'.uasset')).is_file()
for slot,options in w['options'].items():
 ids=[x['id'] for x in options];check(len(ids)==len(set(ids)),slot+' unique option ids')
 for x in options:
  key=x['id'];paths=[]
  if key=='false':continue
  if slot=='underbarrel':key={'angled_foregrip':'angled','vertical_foregrip':'vertical','tactical_vertical_foregrip':'tactical_vertical','canted_foregrip':'canted','prism_handstop':'prism'}.get(key,key)
  if slot in ('tactical','tactical_secondary'):paths=[root+'/Attachments/SM_Saiga12K_'+key+f'_{i}' for i in (1,2)]
  elif slot=='magazine':paths=['Weapons/Saiga12K/Drum20261018/SM_Saiga12K_Drum20' if key=='saiga12k_drum20' else root+'/SM_Saiga12K_Ext12']
  elif key=='saiga12k_bump_stock':paths=['Weapons/Saiga12K/SpecialStock20261018/SM_Saiga12K_SpecialStock']
  else:paths=[root+'/Attachments/SM_Saiga12K_'+key]
  check(all(asset(p) for p in paths),slot+'/'+x['id']+' installed mesh packages',paths)
for family in ('base','drum','angled','vertical','canted','prism'):
 check(asset('Weapons/Saiga12K/InspectClearance20261018/Profiles/DA_'+family),'installed '+family+' pose profile')
stock=next(x for x in w['options']['stock'] if x['id']=='saiga12k_bump_stock')
drum=next(x for x in w['options']['magazine'] if x['id']=='saiga12k_drum20')
check(stock['name']=='S12K撞火枪托','stock display name',stock['name'])
check(all(stock['stats'].get(k)==v for k,v in {'fire_interval_mult':.8,'hip_spread_mult':.75,'recoil_mult':1.1}.items()),'stock +25% cadence / -25% hip spread / +10% recoil',stock['stats'])
check(drum['name']=='12k 大弹鼓','drum display name',drum['name'])
capacity=drum['stats'].get('mag_size',w['base']['mag_size']+drum['stats'].get('mag_delta',0))
check(capacity==20 and drum['stats'].get('reload_mult')==1.75 and drum['stats'].get('ads_percent')==.1,'drum capacity and costs',{'effective_capacity':capacity,**drum['stats']})
for path in ('Weapons/Saiga12K/GameDevAudio20261018/S_Saiga12K_Fire','Weapons/CommonShotgun/Suppressor20261015/Audio/S_Super90_Suppressed',root+'/SK_Saiga12K_Manny'):
 check(asset(path),'installed native dependency',path)
result={'checks':len(rows),'failures':sum(not r['passed'] for r in rows),'results':rows,'runtime_tested':False}
(O/'Receipts/catalog.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k!='results'},ensure_ascii=False))
for r in rows:
 if not r['passed']:print(json.dumps(r,ensure_ascii=False))
