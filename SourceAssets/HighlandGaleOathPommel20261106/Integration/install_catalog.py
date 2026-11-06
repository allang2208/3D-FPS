"""Merge only the Gale Oath option and its native pommel mount into live data."""
from pathlib import Path
from datetime import datetime
import json
import shutil

P=Path(__file__).resolve().parent
ROOT=P.parents[2]
DATA=ROOT/'Content/ColdSteelData'
ID='highland_gale_oath'
option={
    'id':ID,'name':'风誓轻量配重锤','weapons':['ue_highland_claymore'],
    'description':'高地双手剑专属。镂空盾形银钢剑首饰以编结金边与浅蓝风星。',
    'effects':[{'text':'奔跑体力消耗-15%','benefit':1},
               {'text':'重击蓄力速度+20%','benefit':1}],
    'stats':{'sprint_stamina_mult':0.85,'heavy_charge_speed_bonus':0.2},
    'special_effects':[]}
mesh='/Game/Weapons/HighlandClaymore20260922/GaleOath20261106/SurfaceR2/Meshes/SM_Highland_Pommel_GaleOath_R2.SM_Highland_Pommel_GaleOath_R2'
mount={'location_cm':[0.,0.,-22.699999809265137],'mesh':mesh,'interface':'highland_hilt_v1'}
before=P/'Before'/datetime.now().strftime('%Y%m%d-%H%M%S');before.mkdir(parents=True,exist_ok=True)
for name in ['melee-gunsmith.json','highland-claymore-modules.json']:
    file=DATA/name;original=file.read_bytes();value=json.loads(original.decode('utf-8-sig'))
    if name=='melee-gunsmith.json':
        entries=next(c for c in value['columns'] if c['key']=='pommel')['options']
        existing=next((o for o in entries if o['id']==ID),None)
        if existing is None:
            index=next(i for i,o in enumerate(entries) if o['id']=='highland_thorn_crown')+1
            entries.insert(index,option)
        else:existing.update(option)
    else:value['slots']['pommel'][ID]=mount
    if file.read_bytes()!=original:raise RuntimeError('Catalog changed during merge: '+name)
    shutil.copy2(file,before/name)
    temp=file.with_suffix('.gale-oath.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if file.read_bytes()!=original:raise RuntimeError('Preserving concurrent catalog changes: '+name)
    temp.replace(file)
(P/'catalog_receipt.json').write_text(json.dumps({'part':ID,'name':option['name'],
    'weapon':'ue_highland_claymore','tier':'special','stats':option['stats'],'mesh':mesh,
    'backup':str(before),'runtime_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('GALE_OATH_CATALOG_INSTALLED')
