"""Merge only the approved exclusive blade into the live catalogs."""
from pathlib import Path
import json,shutil
P=Path(__file__).resolve().parent;ROOT=P.parents[1];DATA=ROOT/'Content/ColdSteelData'
ID='rift_piercer';WEAPON='ue_frost_crystal_sword'
OPTION=dict(id=ID,name='裂穹长锋',tier='legendary',weapons=[WEAPON],
    description='魔晶双手剑限定。细长晶刃与连续晶脊，保留原有护手、握柄及配重接口；兼容红魔晶与高能魔晶。',
    stats={'range_mult':1.10,'attack_speed_mult':1.20},
    effects=[{'text':'攻击距离+10%','benefit':1},{'text':'攻击速度+20%','benefit':1}],
    special_effects=[
        '裂穹突刺｜普通攻击连段第3下突刺出手时，从剑柄连接处至最大攻击距离瞬间形成完整巨剑，同时贯穿沿途目标；前两下挥空也可触发。重击、快速近战与武技不单独触发。',
        '贯穿长锋｜巨剑长度为当前普通突刺距离的4倍（+300%）；对每个命中目标造成普通第3段突刺200%的伤害和200%的韧性伤害。保留原突刺伤害，每个目标仅结算1次；场景遮挡会截断巨剑。剑形原地残留0.3秒后，用0.22秒消散，残影不重复造成伤害。',
        '破势升空｜剑气命中无韧性保护的普通怪物或已破韧怪物时将其击飞；本次剑气打破韧性时同样可以击飞。',
        '晶体共鸣｜剑气保留魔晶附伤及已安装材质的吸血、回蓝效果，按各目标实际造成的伤害分别结算。剑气不积蓄晶能，不递归产生追加攻击。'])
def publish(name,transform):
    path=DATA/name;before=path.read_bytes();data=transform(json.loads(before.decode('utf-8-sig')))
    backup=P/'BeforeCatalog'/name;backup.parent.mkdir(exist_ok=True)
    if not backup.exists():backup.write_bytes(before)
    if path.read_bytes()!=before:raise RuntimeError('Concurrent catalog edit '+name)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def option(data):
    options=next(c['options'] for c in data['columns'] if c['key']=='blade_1')
    old=next((o for o in options if o['id']==ID),None)
    if old is None:options.append(OPTION)
    else:old.update(OPTION)
    return data
def model(data):
    exports=json.loads((P/'exports.json').read_text(encoding='utf8'))
    data['slots']['blade_1'][ID]=dict(mesh='/Game/Weapons/FrostCrystalSword20260915/RiftPiercer20261102/SM_FrostSword_Blade_rift_piercer',location_cm=[0,0,0],interface='frost_hilt_v1',appearance='裂穹长锋 · 细长晶脊',**{k:exports[k] for k in ['trace_base_cm','trace_tip_cm','rune_dimensions_cm']})
    return data
if __name__=='__main__':
    if not json.loads((P/'import-receipt.json').read_text(encoding='utf8')).get('assets_saved'):raise RuntimeError('Assets must be saved first')
    publish('melee-gunsmith.json',option);publish('frost-sword-modules.json',model)
    shutil.copy2(P/'Export/RiftPiercer_Icon_Framed.png',DATA/'AttachmentIcons20260913'/f'{WEAPON}_blade_1_{ID}.png')
    print('RIFT_PIERCER_CATALOG_SAVED')
