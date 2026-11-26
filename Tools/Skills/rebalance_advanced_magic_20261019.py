"""Apply the requested advanced-spell damage pass and save design arithmetic.

This authors configuration and a level comparison, not a gameplay test.
"""
import json
import math
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/AdvancedMagicDamage20261019'
CHANGES={
    'meteor':dict(damageBase=80,damagePerLevel=10,magicBase=20,magicPerLevel=1.2,
                  intelligenceBase=0,intelligencePerLevel=0,
                  auraDamageBase=10,auraDamagePerLevel=1,auraMagicBase=1.3,auraMagicPerLevel=.09,
                  auraIntelligenceBase=0,auraIntelligencePerLevel=0),
    'blizzard':dict(damageBase=12,damagePerLevel=1,magicBase=1.6,magicPerLevel=.12,
                    intelligenceBase=0,intelligencePerLevel=0),
    'stormDomain':dict(damageBase=20,damagePerLevel=3,magicBase=2.2,magicPerLevel=.16,
                       intelligenceBase=0,intelligencePerLevel=0),
    'thunderLance':dict(damageBase=80,damagePerLevel=12,magicBase=18,magicPerLevel=1.25,
                       intelligenceBase=0,intelligencePerLevel=0),
    'dragonBreath':dict(damageBase=25,damagePerLevel=3,magicBase=3.4,magicPerLevel=.24,
                       intelligenceBase=0,intelligencePerLevel=0),
    'iceWall':dict(damageBase=80,damagePerLevel=12,intelligenceBase=3.5,intelligencePerLevel=.35,
                   wisdomBase=3.5,wisdomPerLevel=.35),
}


def amount(t,level,advanced=False,aura=False):
    k=level-1 if advanced else level
    prefix='aura' if aura else ''
    def value(name):
        key=prefix+name[0].upper()+name[1:] if prefix else name
        return t.get(key,0)
    return math.floor(value('damageBase')+k*value('damagePerLevel')+
                      100*(value('magicBase')+k*value('magicPerLevel'))+
                      100*(value('intelligenceBase')+k*value('intelligencePerLevel'))+
                      100*(value('wisdomBase')+k*value('wisdomPerLevel'))+1e-7)


def run():
    OUT.mkdir(parents=True,exist_ok=True)
    path=ROOT/'Content/ColdSteelData/skills.json'
    text=path.read_text(encoding='utf-8-sig')
    before_path=OUT/'skills-before.json'
    if not before_path.exists():before_path.write_text(text,encoding='utf-8')
    before=json.loads(before_path.read_text(encoding='utf-8'))
    for key,changes in CHANGES.items():
        pattern=r'(?ms)^  "'+key+r'": \{.*?^  \}'
        def replace(match):
            block=json.loads('{'+match[0]+'}')[key]
            block.update(changes)
            block['balanceRevision']='AdvancedMagicDamage20261019: K=level-1; stronger base and per-level damage; '+(
                'INT/WIS physical wall impact' if key=='iceWall' else 'flat + magic-attack scaling; no independent INT term')
            return '  "'+key+'": '+json.dumps(block,ensure_ascii=False,indent=2).replace('\n','\n  ')
        text=re.sub(pattern,replace,text,count=1)
    path.write_text(text,encoding='utf-8')
    after=json.loads(text)
    comparison={'purpose':'Design arithmetic only; no gameplay test',
                'assumptions':{'magic_attack':100,'intelligence':100,'wisdom':100,
                               'equipment_multiplier':1,'defense_critical_statuses':'excluded'},
                'levels':[]}
    for level in [1,10,20]:
        row={'level':level,'fireball_reference':math.floor(100*(8.5+.5*(level-1))),
             'ice_spike_full_volley_reference':amount(before['iceSpike'],level)*(before['iceSpike']['countBase']+(level-1)//before['iceSpike']['countLevelStep']),
             'spells':{}}
        for key in CHANGES:
            old=amount(before[key],level,advanced=key=='dragonBreath')
            new=amount(after[key],level,advanced=True)
            if key=='thunderLance':
                old=math.floor(old*before[key]['chargeBonus']);new=math.floor(new*after[key]['chargeBonus'])
            row['spells'][key]={'before':old,'after':new,'measure':'full charge' if key=='thunderLance' else 'impact' if key in ['iceWall','meteor'] else 'per tick'}
            if key=='meteor':row['spells'][key]['ground_tick']={'before':amount(before[key],level,aura=True),'after':amount(after[key],level,advanced=True,aura=True)}
        comparison['levels'].append(row)
    (OUT/'design-comparison.json').write_text(json.dumps(comparison,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(comparison,ensure_ascii=False))


if __name__=='__main__':run()
