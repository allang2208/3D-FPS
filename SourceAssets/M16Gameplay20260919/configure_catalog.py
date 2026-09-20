"""Publish the M16 factory rifle and balance values into the shared catalogs."""
import copy,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'Content/ColdSteelData'
def read(name):return json.loads((DATA/name).read_text(encoding='utf-8-sig'))
def save(name,data):(DATA/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
items=read('items.json')
item=copy.deepcopy(items['ue_m4a1'])
item.update(id='ue_m16a2',name='M16A2',desc='5.56 mm 三连发步枪。每次扣动扳机发射一组，适合中远距离点射。',
    icon='Icons/ue_m16a2.png',ue_icon='Icons/ue_m16a2.png',grid_w=5,grid_h=2)
item['stats']=[{'name':'物理攻击','value':'34'},{'name':'弹匣容量','value':'30'}]
items['ue_m16a2']=item
save('items.json',items)
catalog=read('gunsmith.json')
m4=next(w for w in catalog['weapons'] if w['id']=='ue_m4a1')
def factory(name,description):return {'id':'false','name':name,'description':description,'effects':[],'stats':{}}
gun={'id':'ue_m16a2','model':'M16A2','name':'M16A2','hit_stagger':False,
    'allowed':['optic','magazine','muzzle','underbarrel','stock','reargrip'],
    'base':{'ammo_item_id':'ammo_556','ads_smooth':math.log(20)/.28,'mag_size':30,
        'recoil':90,'camera_shake':85,'fire_interval':.08,'burst_count':3,'burst_delay':.18,
        'reload_time':2.35,'empty_reload_time':2.95,'damage':34,'bullet_speed':95,'effective_range':110},
    'options':{
        'optic':[factory('提把机械瞄具','保留 M16A2 原厂提把照门与前准星。')],
        'magazine':[factory('30 发原厂弹匣','M16A2 原厂金属弹匣。')],
        'muzzle':[factory('原厂消焰器','保留 M16A2 原厂消焰器。')]+[
            copy.deepcopy(p) for p in m4['options']['muzzle'] if p['id'] in ['true','brake']],
        'underbarrel':[factory('原厂护木','左手直接支撑原厂圆形护木。')],
        'stock':[factory('原厂固定枪托','保留 M16A2 固定枪托。')],
        'reargrip':[factory('原厂后握把','保留 M16A2 原厂后握把。')]}}
catalog['weapons']=[w for w in catalog['weapons'] if w['id']!='ue_m16a2']+[gun]
save('gunsmith.json',catalog)
formulas=read('combat-weapon-formulas.json')
formulas['ue_m16a2']={'source':'M16A2_BURST_BALANCE','base':9,'enhanceFlat':.65,
    'attrs':[{'key':key,'base':.32,'perEnhance':.05} for key in ['int','wis']]}
save('combat-weapon-formulas.json',formulas)
print('M16 catalog, shared formula and item definition written')
