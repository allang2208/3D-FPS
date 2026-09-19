"""Add the independent core_stock option to the three supported rifle catalogs."""
import json,copy,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=Path('D:/FPS3D/FPSGAME')
before=P/'Before';before.mkdir(exist_ok=True)
for relative in ['Content/ColdSteelData/gunsmith.json','Source/FPSGAME/Weapons/SkeletonStockVisual.cpp','Source/FPSGAME/Weapons/QBZ191Attachments.h','Config/DefaultGame.ini']:
    dest=before/Path(relative).name
    if not dest.exists():shutil.copy2(ROOT/relative,dest)
path=ROOT/'Content/ColdSteelData/gunsmith.json';data=json.loads(path.read_text(encoding='utf-8-sig'))
option={
    'id':'core_stock','name':'镂空轻型枪托',
    'description':'轻量化镂空枪托，使用对应枪型的安装接口。提升后坐力控制和枪械稳定性，不影响ADS瞄准时间。',
    'effects':[{'text':'后坐力控制提高10%','benefit':1},{'text':'枪械稳定性增加5%','benefit':1}],
    'stats':{'recoil_mult':.9,'stability_mult':1.05}}
changed=[]
for weapon in data['weapons']:
    if weapon['id'] not in {'ue_m4a1','ue_akm','ue_qbz191'}:continue
    stocks=weapon['options']['stock'];existing=next((i for i,e in enumerate(stocks) if e['id']=='core_stock'),None)
    if existing is None:stocks.insert(next(i for i,e in enumerate(stocks) if e['id']=='skeleton')+1,copy.deepcopy(option))
    else:stocks[existing]=copy.deepcopy(option)
    changed.append(weapon['id'])
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(P/'catalog_authoring.json').write_text(json.dumps({'weapon_ids':changed,'option':option,'existing_skeleton_values_unchanged':True,'ads_duration_multiplier_when_used_alone':1.,'runtime_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('CORE_STOCK_CATALOG_WRITTEN',','.join(changed))
