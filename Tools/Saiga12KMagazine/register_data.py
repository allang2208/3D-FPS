import json,shutil
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KMagazine20261017'
f=P/'Content/ColdSteelData/gunsmith.json';backup=O/'SourceBefore/gunsmith.json'
if not backup.exists():shutil.copy2(f,backup)
d=json.loads(f.read_text(encoding='utf-8-sig'));w=next(x for x in d['weapons'] if x['id']=='ue_saiga12k')
option={'id':'saiga12k_ext12','name':'加长弹匣','description':'弧形聚合物匣体沿原有筋条向下延伸，保留原厂插接颈与独立底板。','effects':[{'text':'弹匣容量增加4发','benefit':1},{'text':'装填耗时增加25%','benefit':-1},{'text':'开镜耗时增加5%','benefit':-1}],'stats':{'mag_delta':4,'reload_mult':1.25,'ads_percent':.05}}
w['options']['magazine']=[x for x in w['options']['magazine'] if x['id']!=option['id']]+[option]
for t in w.get('traits',[]):t['text']=t['text'].replace('使用可拆卸八发弹匣补弹','使用可拆卸弹匣补弹')
f.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('SAIGA_EXT12_CATALOG_SAVED')
