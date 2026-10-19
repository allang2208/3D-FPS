"""Scoped disk/catalog review requested by the user; no asset authoring or savegame changes."""
import copy,json,runpy
from pathlib import Path
P=Path(__file__).resolve().parent
ROOT=P.parents[2]
data=json.loads((ROOT/'Content/ColdSteelData/melee-gunsmith.json').read_text(encoding='utf-8-sig'))
options=next(c['options'] for c in data['columns'] if c['key']=='blade_1')
rows=[]
def check(name,ok):rows.append({'case':name,'passed':bool(ok)})
for key,folder,expected in [
    ('zhufeng','ZhufengBladeV1',{'range_mult':1.2,'physical_damage_mult':1.1,'whirlwind_damage_add':.5}),
    ('chixiao','ChixiaoLegendaryV1',{'physical_damage_mult':1.1,'attack_speed_mult':1.15})]:
    matches=[v for v in options if v['id']==key]
    check(key+' unique option',len(matches)==1)
    option=matches[0]
    check(key+' configured stats',all(option['stats'].get(k)==v for k,v in expected.items()))
    check(key+' legendary exclusive',option['tier']=='legendary' and option['weapons']==['ue_zhanmadao'])
    rebuilt=runpy.run_path(str(P.parent/folder/'catalog_extension.py'))['extend_option'](copy.deepcopy(option))
    check(key+' reimport preserves current gameplay and copy',rebuilt==option)
    check(key+' standard framed icon published',(ROOT/f'Content/ColdSteelData/AttachmentIcons20260913/ue_zhanmadao_blade_1_{key}.uasset').exists())
    check(key+' mechanism text separate from passive cards',bool(option.get('special_effects')) and
          all('text' in row and 'benefit' in row for row in option['effects']))
modules=json.loads((ROOT/'Content/ColdSteelData/zhanmadao-modules.json').read_text(encoding='utf-8-sig'))
part=modules['slots']['blade_1']['zhufeng']
check('Zhufeng dash replacement is active recipe',part.get('dash_attack')=='zhufeng_whirlwind')
check('Zhufeng blade trace endpoints differ',part['trace_base_cm']!=part['trace_tip_cm'])
for path in [part['mesh'],*part['materials'].values()]:
    check('published dependency '+path,(ROOT/'Content'/Path(path.split('.')[0].removeprefix('/Game/')).with_suffix('.uasset')).exists())
check('packaged weapon directory includes cyan material','Path="/Game/Weapons/Zhanmadao20261018"' in (ROOT/'Config/DefaultGame.ini').read_text(encoding='utf-8-sig'))
result={'checks':len(rows),'failures':sum(not r['passed'] for r in rows),'results':rows,'visual_tested':False}
(P/'catalog-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
raise SystemExit(bool(result['failures']))
