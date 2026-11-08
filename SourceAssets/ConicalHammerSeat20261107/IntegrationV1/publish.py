"""Merge the conical seat into all common-seat hosts without replacing catalogs."""
import json,os
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2]
saved=json.loads((P.parent/'BuildV1/import_receipt.json').read_text('utf-8'))
thunder=json.loads((P/'import_receipt.json').read_text('utf-8'))
if not saved['complete'] or not thunder['complete']:raise RuntimeError('Save all three fitted models before publishing')
option={'id':'conical_seat','name':'锥形锤座','tier':'special',
    'description':'切面钢锥从中央锤座向前伸出，阶梯承力肩与沉入式紧固件连接锻钢座体。',
    'appearance':'切面钢锥 · 凹刻折纹 · 阶梯承力肩',
    'stats':{'physical_damage_mult':1.05,'quick_combat_damage_add':.20,'quick_combat_aoe':True,'quick_combat_weapon_damage':True},
    'effects':[{'text':'物理伤害+5%','benefit':1},{'text':'快速近战伤害+20%','benefit':1}],
    'special_effects':['锥锋前顶｜快速近战改为双手持锤向前顶击，对前方范围内的目标造成伤害并击退。',
        '武器传力｜以当前战锤物理伤害代入快速近战伤害公式，随快速近战技能等级和相关增伤结算。']}
jobs=[('Content/ColdSteelData/common-hammer-seats.json','option',option)]
for variant,stem,author,interface,source in [
    ('Steel','warhammer','SteelWarhammer20261014','warhammer_factory_v1',saved),
    ('Runebound','runebound-warhammer','RuneboundWarhammer20261022','runebound_warhammer_modular_v1',saved),
    ('ThunderGod','thunder-god-hammer','ThunderGodHammer20261028','thunder_god_hammer_modular_v1',thunder)]:
    row=source['parts'][variant]
    entry=dict(mesh=row['mesh'],materials=row['materials'],location_cm=[0,0,0],appearance=option['appearance'],
        interface=interface,shared_option_library='common-hammer-seats.json',model_revision='ConicalSeatV1_20261107')
    jobs.append(('Content/ColdSteelData/'+stem+'-modules.json','model',entry))
    jobs.append(('SourceAssets/'+author+'/ModulesV1/catalog_base.json','model',entry))
written=[]
for relative,kind,entry in jobs:
    path=R/relative;before=path.read_bytes();data=json.loads(before.decode('utf-8-sig'))
    if kind=='option':
        data['options']=[v for v in data['options'] if v['id']!=option['id']]+[entry]
    else:data['slots']['head_mount'][option['id']]=entry
    backup=P/'Before'/relative;backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_bytes(before)
    if path.read_bytes()!=before:raise RuntimeError('Concurrent catalog edit '+relative)
    temp=path.with_name(path.name+'.conical-seat.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if path.read_bytes()!=before:raise RuntimeError('Concurrent catalog edit before replace '+relative)
    os.replace(temp,path);written.append(relative)
(P/'catalog_option.json').write_text(json.dumps(option,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(P/'publication.json').write_text(json.dumps({'complete':True,'catalogs':written,'hosts':['ue_steel_warhammer','ue_runebound_warhammer','ue_thunder_god_hammer'],
    'option':option,'icon_revision':'IconV2 user accepted','game_tested':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('CONICAL_SEAT_COMMON_MODIFICATION_PUBLISHED')
