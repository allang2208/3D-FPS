"""Update only the requested stock entries in the three rifle catalogs."""
import json,copy,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;R=Path('D:/FPS3D/FPSGAME');before=P/'Before';before.mkdir(exist_ok=True)
for rel in ['Content/ColdSteelData/gunsmith.json','Source/FPSGAME/Weapons/SkeletonStockVisual.cpp','Source/FPSGAME/Weapons/QBZ191Attachments.h','Config/DefaultGame.ini']:
    target=before/Path(rel).name
    if not target.exists():shutil.copy2(R/rel,target)
path=R/'Content/ColdSteelData/gunsmith.json';data=json.loads(path.read_text(encoding='utf-8-sig'))
updates={
 'skeleton':{'effects':[{'text':'ADS瞄准时间减少20%','benefit':1},{'text':'后坐力增加15%','benefit':-1},{'text':'枪械稳定性增加10%','benefit':1}],'stats':{'ads_percent':-.2,'recoil_mult':1.15,'stability_mult':1.1}},
 'qr_performance':{'effects':[{'text':'后坐力减少20%','benefit':1},{'text':'枪械稳定性增加15%','benefit':1},{'text':'腰射随机散布减少30%','benefit':1}],'stats':{'recoil_mult':.8,'stability_mult':1.15,'hip_spread_mult':.7}}
}
new={'id':'tactical_telescopic','name':'战术伸缩枪托','description':'可调节贴腮面与伸缩结构，使用对应枪型的安装接口。缩短ADS瞄准时间，降低后坐力并提升枪械稳定性，但增加腰射随机散布。','effects':[{'text':'ADS瞄准时间减少5%','benefit':1},{'text':'后坐力减少15%','benefit':1},{'text':'枪械稳定性增加15%','benefit':1},{'text':'腰射随机散布增加25%','benefit':-1}],'stats':{'ads_percent':-.05,'recoil_mult':.85,'stability_mult':1.15,'hip_spread_mult':1.25}}
changed=[]
for weapon in data['weapons']:
    if weapon['id'] not in {'ue_m4a1','ue_akm','ue_qbz191'}:continue
    stocks=weapon['options']['stock']
    for item in stocks:
        if item['id'] in updates:item.update(copy.deepcopy(updates[item['id']]))
    index=next((i for i,item in enumerate(stocks) if item['id']==new['id']),None)
    if index is None:stocks.append(copy.deepcopy(new))
    else:stocks[index]=copy.deepcopy(new)
    changed.append(weapon['id'])
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(P/'catalog_changes.json').write_text(json.dumps({'weapons':changed,'updated':updates,'added':new,'core_stock':'unchanged','gameplay_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('STOCK_CATALOG_UPDATED',','.join(changed))
