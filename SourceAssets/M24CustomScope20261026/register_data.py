"""Register this M24 and its NATO ammunition; preserve unrelated live entries."""
import copy,json
from pathlib import Path
O=Path(__file__).resolve().parent; P=O.parents[1]; D=P/'Content/ColdSteelData'
receipt={'definition':'ue_m24','written':[],'runtime_tested':False}
def update(name,fn):
    path=D/name; original=path.read_bytes(); data=json.loads(original)
    fn(data)
    # Refuse a concurrent write instead of restoring a stale whole catalog.
    if path.read_bytes()!=original:raise RuntimeError('Concurrent catalog edit: '+name)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    receipt['written'].append(name)
def add(data,key,value):
    if key in data and data[key]!=value:raise RuntimeError('Existing M24 entry differs: '+key)
    data[key]=value
def append(rows,value):
    old=next((x for x in rows if x['id']==value['id']),None)
    if old is not None and old!=value:raise RuntimeError('Existing M24 row differs: '+value['id'])
    if old is None:rows.append(value)
ammo={'id':'ammo_m24_762x51','category':'material','type':'弹药','name':'7.62×51mm NATO',
      'desc':'7.62×51mm NATO 步枪弹，自动计入弹药袋。','icon':'Icons/ammo_762.png','ue_icon':'Icons/ammo_762.png',
      'icon_fallback':'▥','rarity':'common','stack_max':999}
weapon={'id':'ue_m24','name':'M24','category':'weapon','type':'武器','equipSlot':'weapon','weaponType':'sniper','critDamageBonus':1.,
        'weaponTypeTag':'栓动狙击步枪','isTwoHanded':True,'stack_max':1,'grid_w':5,'grid_h':2,
        'icon':'Icons/ue_m24.png','ue_icon':'Icons/ue_m24.png',
        'stats':[{'name':'弹匣容量','value':'5'}],
        'desc':'源自雷明顿栓动步枪体系的军用狙击步枪。本款采用定制光学瞄具、消音器与可拆卸弹匣，击发后由右手完成抬栓、退壳和闭锁。适合稳定瞄准后逐发射击，换位与补枪需要留出操作枪栓的时间。'}
update('items.json',lambda d:(add(d,'ue_m24',weapon),add(d,ammo['id'],ammo)))
entry={'id':'ue_m24','model':'M24','name':'M24','allowed':[],'options':{},'inherit_common_options':False,
       'base':{'ammo_item_id':ammo['id'],'mag_size':5,'ads_smooth':8.,'recoil':260,'camera_shake':150,
               'spread_mult':5.,'fire_interval':55/30,'reload_time':84/30,'empty_reload_time':134/30,
               'damage':150,'bullet_speed':820,'effective_range':650,'stability_mult':1.3},
       'traits':[{'icon':'mechanic','text':'栓动；每次扣扳机击发一发，完成拉栓后才能再次射击。'},
                 {'icon':'mechanic','text':'原装配置包含定制六倍瞄具与消音器。'},
                 {'icon':'neutral','text':'当前使用完整原装配置。'}]}
update('gunsmith.json',lambda d:append(d['weapons'],entry))
formula={'source':'M24_NATIVE_BALANCE_20261028','base':40,'enhanceFlat':2.75,
         'attrs':[{'key':'int','base':2.5,'perEnhance':.275},{'key':'wis','base':5.,'perEnhance':.4375}]}
update('combat-weapon-formulas.json',lambda d:add(d,'ue_m24',formula))
atype={'id':ammo['id'],'group':ammo['id'],'group_name':'7.62×51mm NATO','name':'标准弹',
       'description':'用于 7.62×51mm 枪械的标准弹种。','icon':'Icons/ammo_762.png','order':75,
       'enabled':True,'allow_infinite_reserve':True,'damage_multiplier':1.,'physical_armor_penetration':0.}
update('ammo_types.json',lambda d:append(d['types'],atype))
recipe={'id':'craft_ammo_m24_762x51','inputs':[{'item':'copperIngot','count':1},{'item':'leadOre','count':1},{'item':'sulfurOre','count':1}],
        'output':{'item':ammo['id'],'count':20}}
update('ammo-crafting-recipes.json',lambda d:append(d['recipes'],recipe))
def outfit(d):
    profile=copy.deepcopy(d['profiles']['/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416.SK_M4_FoldingSights_HK416'])
    imported=json.loads((O/'gameplay_import_receipt.json').read_text())
    profile['hide_source_materials']=imported['arm_materials']
    profile['native_bare_arms']=True
    add(d['profiles'],'/Game/Weapons/M24/Gameplay20261026/SK_M24_V9.SK_M24_V9',profile)
update('modular_outfits.json',outfit)
(O/'data_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('M24_DATA_REGISTERED',len(receipt['written']),'catalogs')
