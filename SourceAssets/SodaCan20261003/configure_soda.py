"""Publish the 1x1 soda, signed bread costs and two-second can-use motion."""
from copy import deepcopy
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'Content/ColdSteelData'
path = DATA / 'items.json'
items = json.loads(path.read_text(encoding='utf-8-sig'))
for key, cost in (('bread',10),('baguette_bread',30)):
    items[key]['useEffect']['hydration'] = -cost
    items[key]['stats'] = [entry for entry in items[key].get('stats',[]) if entry.get('name') != '消耗水分']
    items[key]['stats'].insert(1, {'name':'消耗水分','value':str(-cost)})
items['soda_can'] = {
    'id':'soda_can', 'name':'罐装汽水', 'category':'consumable', 'type':'饮料',
    'desc':'铝罐密封的碳酸饮料，轻便包装适合随身携带。饮用后补充水分，清甜口感让紧绷的精神稍作放松；一罐饮用后即消耗。',
    'rarity':'common', 'level':1, 'price':25,
    'grid_w':1, 'grid_h':1, 'stack':1, 'stack_max':1, 'maxStack':1, 'maxUses':1,
    'useEffect':{'hydration':20,'sanity':10}, 'useCooldown':0, 'useDuration':2.0,
    'stats':[{'name':'恢复水分','value':'+20'}, {'name':'恢复 SAN','value':'+10'}, {'name':'饮用方式','value':'单次使用'}],
    'icon':'', 'icon_fallback':'汽水', 'ue_icon':'Icons/soda_can.png',
    'world_mesh':'/Game/Items/Consumables/SodaCan20261003/SM_SodaCan.SM_SodaCan',
}
path.write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

path = DATA / 'potion_use_motion.json'
motion = json.loads(path.read_text(encoding='utf-8-sig'))
can = deepcopy(motion['hp_potion'])
can['opens_container'] = False
can['times'] = {'grab':.14,'uncap':.22,'drink_start':.42,'drink_end':1.60,'contact':1.58,
                'release':1.94,'recover':1.94,'duration':2.0}
can['keys'] = [
    {'time':0.0,'grip':[23,-23,-35],'rotation':[0,-8,0]},
    {'time':.14,'grip':[23,-23,-35],'rotation':[0,-8,0]},
    {'time':.30,'grip':[25,-12,-16],'rotation':[5,-8,4]},
    {'time':.42,'grip':[10,-3.5,-6],'rotation':[95,0,2]},
    {'time':.54,'grip':[10,-3.5,-6],'rotation':[103,0,2]},
    {'time':1.60,'grip':[10,-3.5,-6],'rotation':[103,0,2]},
    {'time':1.94,'grip':[23,-23,-35],'rotation':[0,-8,0]},
    {'time':2.0,'grip':[23,-23,-35],'rotation':[0,-8,0]},
]
# Keep the separately authored V7 can-body grasp when republishing the item.
grip = json.loads((ROOT/'SourceAssets/SodaCanGrip20261003/grip_profile.json').read_text(encoding='utf-8'))
for field in ('grip_height','grip_in_palm','digits','authoring'):
    can[field] = deepcopy(grip[field])
motion['soda_can'] = can
path.write_text(json.dumps(motion,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('SODA_CATALOG_AND_MOTION_SAVED grid=1x1 hydration=20 sanity=10 duration=2.0')
