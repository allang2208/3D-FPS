"""Merge only Zhufeng's option from its authoring source into the live catalog."""
import json,runpy
from pathlib import Path
P=Path(__file__).resolve().parent
ROOT=P.parents[2]
path=ROOT/'Content/ColdSteelData/melee-gunsmith.json'
before=path.read_bytes()
data=json.loads(before.decode('utf-8-sig'))
option=next(x for c in data['columns'] if c['key']=='blade_1' for x in c['options'] if x['id']=='zhufeng')
runpy.run_path(str(P.parent/'ZhufengBladeV1/catalog_extension.py'))['extend_option'](option)
backup=P/'melee-gunsmith-before.json'
if not backup.exists():backup.write_bytes(before)
if path.read_bytes()!=before:raise RuntimeError('Catalog changed during merge; retained existing file')
temporary=path.with_suffix('.zhufeng-damage.tmp')
temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
temporary.replace(path)
(P/'publication.json').write_text(json.dumps({
    'catalog_saved':True,'option':'zhufeng','stats':option['stats'],
    'description':option['description'],'special_effects':option['special_effects'],
    'bonus_semantics':'add 0.5 to the whirlwind skill multiplier before damage calculation',
    'game_tested':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('ZHUFENG_DAMAGE_BONUS_AND_COPY_SAVED')
