"""User-requested offline balance calculations and scoped catalog consistency."""
import json,math
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[3];DATA=ROOT/'Content/ColdSteelData'
read=lambda p:json.loads(p.read_text('utf-8-sig'))
catalog=read(DATA/'tactical-hatchet-gunsmith.json')
prior=read(P/'Before/tactical-hatchet-gunsmith.json')
shared=read(DATA/'shared-knife-component-options.json')
local=next(c for c in catalog['columns'] if c['key']=='grip')['options']
old=next(c for c in prior['columns'] if c['key']=='grip')['options']
common=next(c for c in shared['columns'] if c['key']=='grip')['options']
byid={o['id']:o for o in local+common};before={o['id']:o for o in old}
design=read(P.parent/'design.json');entry=read(P.parent/'agile_grip.json')
assert byid['hatchet_grip_agile']['stats']==entry['stats']==design['stats']
assert byid['hatchet_grip_agile']['name']==entry['name']==design['name']=='破阵握柄'
assert byid['hatchet_grip_long']==before['hatchet_grip_long']
assert 'attack_speed_mult' not in design['stats'] and 'physical_damage_mult' not in design['stats']
mesh=read(DATA/'tactical-hatchet-modules.json')['slots']['grip']['hatchet_grip_agile']['mesh']
assert mesh==read(P.parent/'import_receipt.json')['parts'][0]['mesh']
assert (ROOT/'Content'/(mesh.split('.')[0].removeprefix('/Game/')+'.uasset')).is_file()
def numbers(option):
    s=option['stats'];damage=s.get('physical_damage_mult',1);speed=s.get('attack_speed_mult',1);cost=s.get('stamina_mult',1)
    return {'name':option['name'],'physical_damage_mult':damage,'attack_speed_mult':speed,
            'attack_interval_mult':1/speed,'stamina_mult':cost,
            'unarmored_physical_dps_proxy':damage*speed,'physical_damage_per_stamina_proxy':damage/cost,
            'physical_penetration':s.get('physical_armor_penetration',0),'toughness_mult':s.get('toughness_damage_mult',1)}
previous=numbers(before['hatchet_grip_agile']);leather=numbers(byid['knife_grip_leather'])
comparisons=[numbers(o) for o in common+local]
def defense(damage,armor,penetration):
    effective=math.floor(armor*(1-penetration))
    return max(math.floor(damage*60/(effective+60)),math.floor(damage*.1))
rows=[{'physical_damage_before_defense':96,'armor':armor,'factory_damage':defense(96,armor,0),
       'breaker_damage':defense(96,armor,.25)} for armor in (0,30,60,120,180)]
report={'scope':'configuration calculation; not a measured gameplay DPS result',
        'assumptions':'same physical attack cycle, no attack-speed cap, no criticals, enchantments or temporary buffs',
        'previous_agile':previous,'leather':leather,
        'old_agile_vs_leather_dps_delta':previous['unarmored_physical_dps_proxy']/leather['unarmored_physical_dps_proxy']-1,
        'old_agile_vs_leather_efficiency_delta':previous['physical_damage_per_stamina_proxy']/leather['physical_damage_per_stamina_proxy']-1,
        'grip_comparison':comparisons,'armor_examples':rows,
        'checks':{'author_runtime_design_synced':True,'long_option_unchanged':True,'asset_recipe_retained':True,
                  'attack_speed_and_damage_penalty_removed':True},'new_design':design}
(P/'balance_review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'old_dps_delta':report['old_agile_vs_leather_dps_delta'],
                  'old_efficiency_delta':report['old_agile_vs_leather_efficiency_delta'],'armor_examples':rows,'catalog_checks':'passed'},ensure_ascii=False))
