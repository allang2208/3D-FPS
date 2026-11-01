"""Register only Guan Lei seat after the owned mesh and animation save batch."""
import json
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2];D='/Game/Weapons/ThunderGodHammer20261028/ThunderThrowV1'
if not json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))['complete']:raise RuntimeError('Finish asset import first')
icon=R/'Content/ColdSteelData/AttachmentIcons20260913/ue_thunder_god_hammer_head_mount_guan_lei_seat.png'
if not icon.is_file():raise RuntimeError('Finish production icon first')
def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def save(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path=R/'Content/ColdSteelData/thunder-god-hammer-gunsmith.json';book=load(path)
seat=next(c for c in book['columns'] if c['key']=='head_mount')
option={'id':'guan_lei_seat','name':'贯雷锤座','tier':'legendary','weapons':['ue_thunder_god_hammer'],
        'description':'雷神之锤专属。交织银纹锁住中央锤座，折线导雷脊贯穿两侧，将蓄满的重击化为旋转飞锤。',
        'appearance':'北欧交织银纹 · 双侧折线导雷脊 · 蓝钢嵌槽',
        'stats':{'physical_damage_mult':1.1},'effects':[{'text':'物理伤害+10%','benefit':1}],
        'special_effects':['贯雷投掷｜蓄满重击后出现抛物线指示器；松开攻击键，将头顶举起的战锤向前竖劈投出，飞行中持续翻转。',
                           '雷霆落锤｜落地释放重击冲击波与垂直雷击；半径3米内结算原有重击物理伤害和100%魔法攻击力的魔法伤害，并叠加2层感电、施加1.5秒眩晕。精英控制遵循破韧规则。',
                           '雷锤召回｜落地后按普通攻击键召回，战锤旋转飞回，对沿途每个敌人造成一次普通攻击的物理伤害；右手伸掌接住握柄，左手扶回后恢复持握。冲刺攻击保持原有招式。']}
seat['options']=[o for o in seat['options'] if o['id']!='guan_lei_seat']+[option]
for trait in book.get('traits',[]):
    if trait.get('text','').startswith('按住左键蓄力'):
        trait['text']='按住左键蓄力，蓄满后松开释放重击；落点产生冲击波和雷击。安装贯雷锤座后改为向前投掷，落地后按左键召回。'
save(path,book)
path=R/'Content/ColdSteelData/thunder-god-hammer-modules.json';catalog=load(path)
catalog['slots']['head_mount']['guan_lei_seat']={'mesh':D+'/SM_ThunderHammer_GuanLeiSeat.SM_ThunderHammer_GuanLeiSeat',
    'location_cm':[0,0,0],'appearance':option['appearance'],'interface':catalog['interface'],
    'model_revision':'GuanLeiThrowV1','source_mesh':'SM_ThunderHammer_GuanLeiSeat'}
save(path,catalog)
(P/'publish_receipt.json').write_text(json.dumps({'complete':True,'option':'guan_lei_seat','weapon':'ue_thunder_god_hammer',
    'slot':'head_mount','tier':'legendary','runtime_tested':False},indent=2),encoding='utf-8')
print('GUAN_LEI_SEAT_PUBLISHED')
