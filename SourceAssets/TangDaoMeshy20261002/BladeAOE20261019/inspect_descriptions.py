"""Requested check of the two blades on Tang Dao and Zhanmadao; no game launch."""
import json
import runpy
from pathlib import Path

P=Path(__file__).resolve().parent
ROOT=P.parents[2]
DATA=ROOT/'Content/ColdSteelData'
read=lambda path:json.loads(path.read_text('utf-8-sig'))
catalog=read(DATA/'melee-gunsmith.json')
options={o['id']:o for c in catalog['columns'] if c['key']=='blade_1' for o in c['options']}
report={'scope':['ue_tang_dao','ue_zhanmadao'],'checks':[],'game_tested':False,'ui_rendered':False}
for option,folder,attack in [('yanling_edge','YanlingBlade20261002','sprint_overhead_rectangle'),
                            ('tengyun_dragon','TengyunBlade20261002','rising_dragon')]:
    part=options[option]
    generated={'columns':[{'key':'blade_1','options':[]}]}
    runpy.run_path(str(P.parent/folder/'catalog_extension.py'))['add_option'](generated)
    authored=generated['columns'][0]['options'][0]
    for key in ('stats','effects','special_effects'):
        if part[key]!=authored[key]:raise RuntimeError(f'Reimport would restore different {option} {key}')
    damage_percent=round((part['stats']['combo_third_damage_mult']-1)*100)
    if sum(f'第三段伤害提高{damage_percent}%' in text for text in part['special_effects'])!=1:
        raise RuntimeError(f'Missing or duplicated finisher damage description: {option}')
    for weapon,file in [('ue_tang_dao','tang-dao-modules.json'),('ue_zhanmadao','zhanmadao-modules.json')]:
        if weapon not in part['weapons']:raise RuntimeError(f'Compatibility missing: {weapon} {option}')
        if read(DATA/file)['slots']['blade_1'][option]['combo_third_attack']!=attack:
            raise RuntimeError(f'Wrong active motion route: {weapon} {option}')
        report['checks'].append({'weapon':weapon,'option':option,'attack_route':attack,
            'stats':part['stats'],'special_effects':part['special_effects'],
            'existing_rows_retained':['攻击体力消耗 +10%','格挡减伤倍率 ×0.90'] if option=='yanling_edge' else ['攻击速度 +10%','准备时间 -50%','无韧性或破韧时击飞'],
            'added_description':f'第三段伤害 +{damage_percent}%', 'reimport_consistent':True})
report['display_route']='MeleeGunsmith loads special_effects; M4GunsmithSelectedDetails displays each special effect and existing modifier cards.'
(P/'description-inspection.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('BLADE_DESCRIPTIONS_CHECKED',len(report['checks']),flush=True)
