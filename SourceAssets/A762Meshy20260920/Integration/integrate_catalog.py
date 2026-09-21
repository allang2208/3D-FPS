"""Add the A762 definition and connect existing inventory presentation routes."""
import copy,json
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME')
def edit(rel,changes):
    p=R/rel;text=p.read_text(encoding='utf-8-sig')
    for old,new in changes:
        if old not in text:raise RuntimeError('Edit anchor missing in '+rel+': '+old[:80])
        text=text.replace(old,new,1)
    p.write_text(text,encoding='utf-8',newline='')
edit('Source/FPSGAME/FPSGAMECharacterProfile.cpp', [('I->Definition==TEXT("ue_akm")||','I->Definition==TEXT("ue_akm")||I->Definition==TEXT("ue_a762")||')])
edit('Source/FPSGAME/UI/ColdSteelWeaponIcons.cpp', [
    ('I.Definition==TEXT("ue_akm")||','I.Definition==TEXT("ue_akm")||I.Definition==TEXT("ue_a762")||'),
    ('if(RigDefinition!=I.Definition){Rig->bUseM4Infima','if(RigDefinition!=I.Definition){Rig->ActiveInventoryWeaponDefinition=I.Definition;Rig->bUseM4Infima')])
edit('Source/FPSGAME/UI/ColdSteelPickupWeapon.cpp', [
    ('Item.Definition!=TEXT("ue_akm")&&','Item.Definition!=TEXT("ue_akm")&&Item.Definition!=TEXT("ue_a762")&&'),
    ('if(Created){Rig->bUseM4Infima','if(Created){Rig->ActiveInventoryWeaponDefinition=Item.Definition;Rig->bUseM4Infima')])
edit('Source/FPSGAME/UI/ColdSteelPickupStudio.cpp', [('Item.Definition!=TEXT("ue_akm")&&','Item.Definition!=TEXT("ue_akm")&&Item.Definition!=TEXT("ue_a762")&&')])
edit('Source/FPSGAME/UI/M4StandalonePreview.cpp', [('Rig->bUseM4Infima=Item.Definition','Rig->ActiveInventoryWeaponDefinition=Item.Definition;Rig->bUseM4Infima=Item.Definition')])
edit('Source/FPSGAME/UI/ColdSteelWarehouseModel.cpp', [('for (const TCHAR* Definition : {TEXT("ue_akm"),','for (const TCHAR* Definition : {TEXT("ue_a762"), TEXT("ue_akm"),')])
p=R/'Content/ColdSteelData/items.json';items=json.loads(p.read_text(encoding='utf-8-sig'))
item=copy.deepcopy(items['ue_akm']);item.update(id='ue_a762',name='A762',desc='A762 自动步枪，使用 7.62mm 弹药与 30 发弧形弹匣，配骨架枪托和顶部导轨。',icon='',ue_icon='Icons/ue_a762.png')
items['ue_a762']=item;p.write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=R/'Content/ColdSteelData/gunsmith.json';data=json.loads(p.read_text(encoding='utf-8-sig'));ak=next(x for x in data['weapons'] if x['id']=='ue_akm')
weapon={'id':'ue_a762','model':'A762Meshy','name':'A762','allowed':['optic','muzzle'],'base':copy.deepcopy(ak['base']),'options':{}}
for slot in weapon['allowed']:
    weapon['options'][slot]=copy.deepcopy(ak['options'][slot])
    for option in weapon['options'][slot]:
        if option['id']=='false':
            option['description']='使用 A762 原厂机械瞄具。' if slot=='optic' else '使用 A762 原厂枪口件。'
        elif slot=='optic':option['description']='安装于 A762 顶部导轨，装配时收起机械瞄具。'
        else:option['description']='替换 A762 原厂枪口件，沿枪管轴线安装。'
data['weapons']=[x for x in data['weapons'] if x['id']!='ue_a762']+[weapon]
p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
edit('Config/DefaultGame.ini',[('+DirectoriesToAlwaysCook=(Path="/Game/Weapons/M16A2")','+DirectoriesToAlwaysCook=(Path="/Game/Weapons/M16A2")\n+DirectoriesToAlwaysCook=(Path="/Game/Weapons/A762")')])
print('A762 catalog, inventory, warehouse and presentation routes written.')
