"""Compare current catalogues with the user's approved warhammer tables."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent;D=P.parents[1]/'Content/ColdSteelData'
def read(name):return json.loads((D/name).read_text(encoding='utf-8-sig'))
cases={
 'common-hammer-heads.json':{
  'light_drum':{'physical_damage_mult':.9},
  'pointed_hammer':{'physical_damage_mult':1.3,'attack_speed_mult':1.05,'stamina_mult':1.15,'toughness_damage_mult':.75,'physical_armor_penetration':.15}},
 'common-hammer-seats.json':{
  'heavy_forged_seat':{'physical_damage_mult':1.1,'attack_speed_mult':.95,'stamina_mult':1.1,'toughness_damage_mult':1.15},
  'light_ribbed_seat':{'physical_damage_mult':.95,'attack_speed_mult':1.1,'stamina_mult':.9,'toughness_damage_mult':.9},
  'laminated_buffer_seat':{'physical_damage_mult':1.05,'attack_speed_mult':1.05,'stamina_mult':.85,'toughness_damage_mult':.85}},
 'common-hammer-grips.json':{
  'bias_speed_wrap':{'attack_speed_mult':1.15,'stamina_mult':.9,'toughness_damage_mult':.85},
  'layered_cushion_wrap':{'stamina_mult':.75},
  'diamond_power_wrap':{'attack_speed_mult':1.05,'stamina_mult':1.1,'heavy_charge_speed_bonus':.25}},
 'common-hammer-pommels.json':{
  'octagonal_impact':{'physical_damage_mult':1.05,'attack_speed_mult':.95,'stamina_mult':1.05,'toughness_damage_mult':1.1},
  'caged_agility':{'physical_damage_mult':.95,'attack_speed_mult':1.1,'stamina_mult':.9},
  'twin_disc_balance':{'stamina_mult':.8,'toughness_damage_mult':.9,'martial_cooldown_mult':.8},
  'no_pommel':{'attack_speed_mult':1.05,'stamina_mult':.95,'heavy_charge_speed_bonus':.1,'heavy_release_stamina_mult':1.1}}
}
rows=[];inventory=[]
def check(name,actual,expected):rows.append({'check':name,'actual':actual,'expected':expected,'pass':actual==expected})
for filename,expected in cases.items():
    options=read(filename)['options'];by_id={o['id']:o for o in options}
    # Human-approved seat names are stable even when their authored IDs differ.
    if filename=='common-hammer-seats.json':
        names=['厚壁重铸座','镂肋轻型座','叠片缓冲座']
        expected={next(o['id'] for o in options if o['name']==name):value for name,value in zip(names,expected.values())}
    for ident,stats in expected.items():
        for key,value in stats.items():check(filename+'/'+ident+'/'+key,by_id.get(ident,{}).get('stats',{}).get(key,1),value)
    inventory += [{'library':filename,**o} for o in options]
hammer=read('warhammer-gunsmith.json')
check('five selectable slots with shaft removed',[c['key'] for c in hammer['columns']],['hammer_heads','head_mount','rune','grip','pommel'])
head=next(c for c in hammer['columns'] if c['key']=='hammer_heads')
meteor=next(o for o in head['options'] if o['id']=='meteor_core')
for key,value in {'physical_damage_mult':1.4,'attack_speed_mult':.85,'stamina_mult':1.25,'toughness_damage_mult':1.4,'shockwave_radius_mult':1.5}.items():check('meteor_core/'+key,meteor['stats'].get(key),value)
runes=next(c['options'] for c in read('melee-gunsmith.json')['columns'] if c['key']=='blade_2')
for ident,key,value in [('strength_rune','physical_damage_mult',1.1),('resonance_rune','skill_cooldown_mult',.85)]:
    check(ident+'/'+key,next(o for o in runes if o['id']==ident)['stats'].get(key),value)
report={'passed':all(r['pass'] for r in rows),'checks':rows,'parts':inventory,'exclusive_head':meteor,
 'scope':'approved data values and slot configuration; not runtime testing'}
(P/'catalog_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':report['passed'],'checks':len(rows),'failed':[r for r in rows if not r['pass']]},ensure_ascii=True))
