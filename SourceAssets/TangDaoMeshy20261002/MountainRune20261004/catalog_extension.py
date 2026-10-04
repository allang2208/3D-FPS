"""Register only this rune and its saved material bindings in the live catalogs."""
from pathlib import Path
import json, shutil

P=Path(__file__).resolve().parent
ROOT=P.parents[2]
DATA=ROOT/'Content/ColdSteelData'
REVISION='TangDaoMountainRune20261004'
UE_ROOT='/Game/Weapons/TangDao20261002/MountainRune20261004'

def write(path,value):
    backup=P/'Before'/path.relative_to(ROOT)
    backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(path,backup)
    temp=path.with_suffix(path.suffix+'.mountain.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temp.replace(path)

def install():
    receipt=json.loads((P/'Records/import_receipt.json').read_text(encoding='utf-8'))
    if not receipt.get('complete'):raise RuntimeError('Save rune assets before registering the option')
    mapping=receipt['material_bindings']
    modules_file=DATA/'tang-dao-modules.json'
    modules=json.loads(modules_file.read_text(encoding='utf-8-sig'))
    for row in modules['slots']['blade_1'].values():
        for slot,old in row.get('materials',{}).items():
            row['materials'][slot]=mapping.get(old,old)
    modules['mountain_rune_revision']=REVISION
    write(modules_file,modules)
    bindings_file=P.parent/'SurfaceV2/bindings.json'
    bindings=json.loads(bindings_file.read_text(encoding='utf-8-sig'))
    for materials in bindings.get('slots',{}).get('blade_1',{}).values():
        for slot,old in materials.items():materials[slot]=mapping.get(old,old)
    bindings['mountain_rune_revision']=REVISION
    write(bindings_file,bindings)
    temporal_file=DATA/'whirlwind-temporal-materials.json'
    temporal=json.loads(temporal_file.read_text(encoding='utf-8-sig'))
    temporal.update(receipt['temporal_bindings']);write(temporal_file,temporal)
    file=DATA/'melee-gunsmith.json'
    catalog=json.loads(file.read_text(encoding='utf-8-sig'))
    column=next(c for c in catalog['columns'] if c['key']=='blade_2')
    option={'id':'mountain_rune','name':'山岳符文','weapons':['ue_tang_dao'],
        'description':'唐刀专属。三峰主印与层叠岩脉沿刀身展开，土黄刻纹间缓缓浮起琥珀微光。借山岳之重增强攻击、击退与削韧。',
        'appearance':'三峰山印 · 层岩刻纹 · 土黄微光',
        'effects':[{'text':'全部近战攻击伤害 +10%（含属性、附加伤害及快速近战）','benefit':1},
                   {'text':'攻击时所有击退效果 +50%（含快速近战、旋风、冲刺斩）','benefit':1},
                   {'text':'攻击韧性伤害 +50%','benefit':1}],
        'stats':{'all_attack_damage_mult':1.1,'all_attack_knockback_mult':1.5,'toughness_damage_mult':1.5}}
    existing=next((i for i,o in enumerate(column['options']) if o['id']=='mountain_rune'),None)
    if existing is None:column['options'].append(option)
    else:column['options'][existing]=option
    # Idempotent user target: keep +10%, never add another 10% each run.
    cloud=next(o for o in column['options'] if o['id']=='auspicious_cloud_rune')
    cloud['stats']['attack_speed_mult']=1.1
    cloud['effects']=[e for e in cloud['effects'] if not e['text'].startswith('攻击速度')]
    cloud['effects'].insert(0,{'text':'攻击速度 +10%','benefit':1})
    write(file,catalog)
    print('TANGDAO_MOUNTAIN_RUNE_REGISTERED',flush=True)

if __name__=='__main__':install()
