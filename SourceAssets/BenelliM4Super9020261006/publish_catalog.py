import json,copy
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');C=P/'Content/ColdSteelData'
def read(n):return json.loads((C/(n+'.json')).read_text(encoding='utf-8-sig'))
def save(n,d):(C/(n+'.json')).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
d=read('items');d['ue_super90']={'id':'ue_super90','name':'M4 Super90','category':'weapon','type':'武器','equipSlot':'weapon','weaponType':'shotgun','weaponTypeTag':'霰弹枪','isTwoHanded':True,'rarity':'common','stack_max':1,'grid_w':4,'grid_h':2,'icon':'Icons/ue_super90.png','ue_icon':'Icons/ue_super90.png','stats':[{'name':'基础伤害','value':'80'},{'name':'弹仓容量','value':'7'}],'desc':'使用 12 号鹿弹的半自动霰弹枪。每次扣扳机发射一发弹药，散布的八颗弹丸分别结算命中，近距离集中火力更强。管式弹仓逐发补弹，空仓装填后释放枪机；装弹时开火可提前结束补弹。'}
for id,name,slot,defense,desc in [('ue_hardknuckle_gloves','硬壳战术手套','gloves',5,'硬质护指关节与织物掌背，沿用源模型的独立手套网格和 PBR 表面。'),('ue_st6_sleeves','ST6 战术衣袖','armor',6,'独立的 ST6 战术衣袖，保留源模型的袖口、布料纹理与褶皱。此装备为双臂衣袖。')]:
 d[id]={'id':id,'name':name,'category':'equipment','type':'护甲','equipSlot':slot,'rarity':'common','stack_max':1,'maxStack':1,'price':35,'grid_w':2 if slot=='gloves' else 3,'grid_h':2,'defense':{'base':defense,'perEnhance':1},'desc':desc,'ue_icon':'Icons/Super90Source20261006/'+id+'.png','icon_fallback':'手' if slot=='gloves' else '衣','world_mesh':'/Game/Characters/ModularOutfit20260924/Super90Source20261006/Pickups/SM_'+id+'.SM_'+id,'ue_equipment_icon_mesh':'/Game/Characters/ModularOutfit20260924/Super90Source20261006/Pickups/SM_'+id+'.SM_'+id,'world_material':''}
d['ammo_12g']={'id':'ammo_12g','name':'12 号鹿弹','category':'ammo','type':'弹药','stack_max':60,'maxStack':60,'grid_w':1,'grid_h':1,'rarity':'common','icon':'Icons/Super90Source20261006/ammo_12g.png','ue_icon':'Icons/Super90Source20261006/ammo_12g.png','desc':'12 号霰弹枪弹药，每发内含八颗鹿弹弹丸。'}
save('items',d)
d=read('ammo_types');d['types']=[r for r in d['types'] if r['id']!='ammo_12g'];d['types'].append({'id':'ammo_12g','group':'ammo_12g','group_name':'12 gauge','name':'00 Buck','tier_name':'绿阶','tier_color':'#4CAA70','description':'八弹丸鹿弹，适用于管式弹仓霰弹枪。','icon':'Icons/Super90Source20261006/ammo_12g.png','order':100,'enabled':True,'allow_infinite_reserve':True,'damage_multiplier':1.0,'physical_armor_penetration':0.0});save('ammo_types',d)
d=read('gunsmith');d['weapons']=[r for r in d['weapons'] if r['id']!='ue_super90'];slots={'optic':'原厂鬼环瞄具','muzzle':'原厂枪口','underbarrel':'原厂护木','stock':'原厂枪托','magazine':'原厂管式弹仓'};d['weapons'].append({'id':'ue_super90','model':'M4Super90','name':'M4 Super90','allowed':list(slots),'base':{'ammo_item_id':'ammo_12g','mag_size':7,'ads_smooth':12,'recoil':145,'camera_shake':120,'spread_mult':1.5,'fire_interval':.65,'reload_time':1.65/1.3,'empty_reload_time':(424/60)/1.3,'damage':80,'bullet_speed':380,'effective_range':35,'stability_mult':1},'options':{k:[{'id':'false','name':v,'description':'使用 M4 Super90 原装结构。','effects':[],'stats':{}}] for k,v in slots.items()},'traits':[{'icon':'mechanic','text':'半自动；一发鹿弹产生八颗独立命中的弹丸，面板显示整发合计伤害'},{'icon':'mechanic','text':'逐发补弹；空仓装填后闭合枪机；开火可结束补弹'},{'icon':'drawback','text':'弹丸向外扩散，远距离命中率与伤害降低'},{'icon':'neutral','text':'保留原厂机械分件，本次目录提供原厂配置'}]});save('gunsmith',d)
d=read('combat-weapon-formulas');f=copy.deepcopy(read('source-combat-items')['Super90']['attackFormula']);f.pop('variants',None);f['source']='Super90 (eight-pellet aggregate)';f['base']*=8;f['enhanceFlat']*=8
for row in f['attrs']:row['base']*=8;row['perEnhance']*=8
d['ue_super90']=f;save('combat-weapon-formulas',d)
p=P/'Source/FPSGAME/UI/ColdSteelWarehouseModel.cpp';s=p.read_text(encoding='utf-8-sig');s=s.replace('{TEXT("ue_hk416"), TEXT("ue_pit_viper2011")','{TEXT("ue_super90"), TEXT("ue_hk416"), TEXT("ue_pit_viper2011")',1).replace('FString(Definition)==TEXT("ue_svd")?10:','FString(Definition)==TEXT("ue_super90")?7:FString(Definition)==TEXT("ue_svd")?10:',1).replace('        if(FString(Definition)==TEXT("ue_svd"))','        if(FString(Definition)==TEXT("ue_super90"))\n        {\n            if(!AddAmmoToState(State,TEXT("ammo_12g"),42))return false;\n        }\n        if(FString(Definition)==TEXT("ue_svd"))',1)
anchor='    return !Changed || CommitState(State);'
new='''    for(const TCHAR* Definition:{TEXT("ue_hardknuckle_gloves"),TEXT("ue_st6_sleeves")})
    {
        if(State.ArmoryReceived.Contains(Definition))continue;
        auto Gear=CreateItem(Definition);if(Gear.Data.IsEmpty())return false;
        if(!ColdSteelWarehouse::Insert(State.Items,Gear,WarehouseCapacity()))return false;
        State.ArmoryReceived.Add(Definition);Changed=true;
    }
'''+anchor
s=s.replace(anchor,new,1);p.write_text(s,encoding='utf-8')
p=P/'Config/DefaultGame.ini';s=p.read_text(encoding='utf-8-sig');s+='\n[/Script/UnrealEd.ProjectPackagingSettings]\n+DirectoriesToAlwaysCook=(Path="/Game/Weapons/Super90/Cransh20261006")\n+DirectoriesToAlwaysCook=(Path="/Game/Characters/ModularOutfit20260924/Super90Source20261006")\n';p.write_text(s,encoding='utf-8')
print('SUPER90_CATALOG_WRITTEN')
