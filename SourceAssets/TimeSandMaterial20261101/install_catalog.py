"""Merge the approved legendary rune-sword material into the live catalogs."""
# Apply the shared workbench copy standard when publishing catalogs.
from pathlib import Path as _WorkbenchCopyPath
import runpy as _workbench_copy_runpy
_workbench_copy_root = next(p for p in _WorkbenchCopyPath(__file__).resolve().parents if (p / 'FPSGAME.uproject').exists())
_apply_workbench_copy = _workbench_copy_runpy.run_path(str(_workbench_copy_root / 'SourceAssets/WorkbenchCopy20261101/copy_rules.py'))['apply_for_target']

from pathlib import Path
import json
P=Path(__file__).resolve().parent
ROOT=P.parents[1]
appearance='符文长剑专属。香槟金剑面泛起细腻拉丝亮泽，精抛刃缘清亮，细砂在金属深处缓缓流动。'
option={
    'id':'time_sand_gold','name':'时砂秘金','description':appearance,
    'tier':'legendary','weapons':['ue_rune_sword'],
    'stats':{'stamina_mult':1.15,'time_sand_echo_ratio':0.30,'time_sand_echo_delay':0.6},
    'effects':[
        {'text':'时砂回响：剑刃命中后延迟0.6秒，追加本次实际伤害的30%。','benefit':1},
        {'text':'回响命中再次触发符文长剑的减冷却被动。','benefit':1},
        {'text':'攻击体力消耗+15%','benefit':-1}],
    'special_effects':[
        '时砂回响｜剑刃命中后延迟0.6秒，追加本次实际伤害的30%；保留原命中的物理与魔法伤害比例，不重复判定暴击。',
        '回响共鸣｜有效回响减少魔法及G飞剑剩余冷却0.5秒，装备金色符文时为1秒；同一挥的回响只结算一次减冷却。',
        '触发范围｜仅剑刃命中触发，配重锤、剑气与飞剑不触发。回响不会生成新的回响，也不触发其他命中附效。']}
for name in ['melee-gunsmith.json','rune-sword-modules.json']:
    path=ROOT/'Content/ColdSteelData'/name
    before=path.read_bytes();data=json.loads(before.decode('utf-8-sig'))
    if name=='melee-gunsmith.json':
        options=next(c for c in data['columns'] if c['key']=='blade_material')['options']
        previous=next((o for o in options if o['id']==option['id']),None)
        if previous is None:options.append(option)
        else:previous.update(option)
    else:data['slots']['blade_material'][option['id']]={'mode':7,'appearance':appearance}
    backup=P/'Before'/name;backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_bytes(before)
    if path.read_bytes()!=before:raise RuntimeError('Catalog changed during merge: '+name)
    path.write_text(json.dumps(_apply_workbench_copy(path, data),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(P/'catalog-receipt.json').write_text(json.dumps(_apply_workbench_copy(P/'catalog-receipt.json', {'option':option,'mode':7,'gameplay_tested':False}),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('TIME_SAND_CATALOG_SAVED')
