"""Merge the exclusive legendary blade into the live workbench and model recipe."""
from pathlib import Path
import json,shutil,runpy
P=Path(__file__).resolve().parent;ROOT=P.parents[1];DATA=ROOT/'Content/ColdSteelData'
WEAPON='ue_frost_crystal_sword';ID='star_marrow'
DESCRIPTION='魔晶双手剑限定。长款晶体双刃内嵌三枚星髓晶核，保留原有护手与握柄接口；兼容红魔晶与高能魔晶。'
SPECIAL=['充能 [G]｜消耗最大魔法值的20%，进入30秒充能状态；当前魔法值不足时无法释放。', '充能增幅｜持续期间造成的攻击伤害+30%，全部转化为魔法伤害，按目标魔法防御结算；覆盖普攻、重击、突刺、快速近战、武技与攻击魔法。', '蓝焰附刃｜充能期间剑身持续燃烧蓝色火焰。持续期间不可重复开启，无额外冷却；到期、切换武器、卸下星髓长锋或死亡时解除。']
OPTION=dict(id=ID,name='星髓长锋',tier='legendary',weapons=[WEAPON],description=DESCRIPTION,
    stats={'range_mult':1.25,'magic_attack_mult':1.1},effects=[{'text':'攻击距离+25%','benefit':1},{'text':'魔法攻击+10%','benefit':1}],special_effects=SPECIAL)
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
    data['slots']['blade_1'][ID]=dict(mesh='/Game/Weapons/FrostCrystalSword20260915/StarMarrow20261102/SM_FrostSword_Blade_star_marrow',
        location_cm=[0,0,0],interface='frost_hilt_v1',**{k:exports[k] for k in ['trace_base_cm','trace_tip_cm','rune_dimensions_cm']})
    return data
if __name__=='__main__':
    receipt=json.loads((P/'import-receipt.json').read_text(encoding='utf8'))
    if not receipt.get('assets_saved'):raise RuntimeError('Import/save must finish before publishing')
    publish('melee-gunsmith.json',option);publish('frost-sword-modules.json',model)
    publish('whirlwind-temporal-materials.json',lambda data:dict(data,**receipt['temporal_bindings']))
    shutil.copy2(P/'Export/StarMarrow_Icon_Framed.png',DATA/'AttachmentIcons20260913'/f'{WEAPON}_blade_1_{ID}.png')
    print('STAR_MARROW_CATALOG_SAVED')
