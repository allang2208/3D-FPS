"""Add this consumable to the current catalogs, preserving all other rows."""
import json
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME/Content/ColdSteelData')
path=root/'items.json'
items=json.loads(path.read_text(encoding='utf-8-sig'))
items['mineral_water']={
    'id':'mineral_water','name':'矿泉水','category':'consumable','type':'消耗品',
    'desc':'清澈的瓶装矿泉水。每次恢复30点水分，一瓶可饮用两次；喝完半瓶后拧盖收回。',
    'rarity':'common','level':1,'price':30,'grid_w':1,'grid_h':2,
    'stack':1,'stack_max':1,'maxStack':1,'remainingUses':2,'maxUses':2,
    'useEffect':{'hydration':30},'useCooldown':0,
    'stats':[{'name':'恢复水分','value':'+30 / 次'},{'name':'可饮用次数','value':'2次'}],
    'icon':'','icon_fallback':'💧','ue_icon':'Icons/mineral_water_full.png',
    'half_icon':'Icons/mineral_water_half.png'
}
path.write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path=root/'potion_visuals.json'
visuals=json.loads(path.read_text(encoding='utf-8-sig'))
dest='/Game/Items/Consumables/MineralWater20261003'
def asset(name):return dest+'/'+name+'.'+name
water={
    'tier':'mineral_water','definitions':['mineral_water'],'height_cm':22,'grip_height_cm':17.2,
    'shell':asset('SM_MineralWater_Shell'),'liquid':asset('SM_MineralWater_Liquid'),
    'stopper':asset('SM_MineralWater_Cap'),'closed':asset('SM_MineralWater_Full'),
    'half_closed':asset('SM_MineralWater_Half'),
    'liquid_material':dest+'/Materials/M_MineralWater_Liquid.M_MineralWater_Liquid',
    'liquid_bottom_cm':.35,'liquid_full_cm':18.4
}
visuals['tiers']=[v for v in visuals['tiers'] if v['tier']!='mineral_water']+[water]
path.write_text(json.dumps(visuals,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path=root/'potion_use_motion.json'
motion=json.loads(path.read_text(encoding='utf-8-sig'))
family=json.loads(json.dumps(motion['hp_potion']))
family['grip_height']=17.2
family['times']=dict(motion['times'],drink_end=3.08,contact=3.08,release=3.72,recover=3.72,duration=4.00)
# Two seconds at the mouth, followed by one continuous lowering movement.
family['keys']=[k for k in motion['keys'] if k['time']<=1.30]+[
    {'time':3.08,'grip':[13,-3.5,-6],'rotation':[111,0,2]},
    {'time':3.72,'grip':[23,-23,-35],'rotation':[0,-8,0]}
]
motion['mineral_water']=family
path.write_text(json.dumps(motion,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
