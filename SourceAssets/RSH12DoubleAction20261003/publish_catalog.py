"""Update only RSH catalog objects after the new revision is actually saved."""
from pathlib import Path
import json, importlib.util
O=Path(__file__).parent
spec=importlib.util.spec_from_file_location('rsh_catalog',O.parent/'RSH12SingleAction20261003/publish_catalog.py')
catalog=importlib.util.module_from_spec(spec);spec.loader.exec_module(catalog)
catalog.O=O
receipt=json.loads((O/'import_receipt.json').read_text(encoding='utf8'))
if not receipt.get('complete') or receipt.get('revision')!='double-action-v1':raise RuntimeError('Current asset revision has not been saved')
def item(v):
    v['desc']='俄罗斯大口径双动左轮，使用12.7毫米弹药与五发弹巢。扣动扳机联动击锤和转轮，射后保持双手握持。下置枪管带来鲜明的枪体轮廓，单持以五发速装器整组装填；双持与副手沿用单手逐发装填。'
def weapon(v):
    v['base'].update(fire_interval=.4,reload_time=500/120,empty_reload_time=520/120)
    for option in v['options']['trigger']:
        if option['id']=='false':option.update(name='原厂双动扳机',description='扳机联动击锤与五发转轮，射后保持握持。')
        elif option['id']=='rsh12_lightweight_fast':option.update(description='轻量扳机机构，缩短双动击发循环。')
    for trait in v.get('traits',[]):
        text=trait.get('text','')
        if any(s in text for s in ('单动','拇指拨锤','逐发装填')):
            trait['text']='双动左轮；五发弹巢，单持整组速装，双持／副手逐发装填。'
data=O.parents[1]/'Content/ColdSteelData'
a=catalog.write_object(data/'items.json','ue_rsh12',item)
b=catalog.write_object(data/'gunsmith.json','ue_rsh12',weapon,'weapons')
(O/'catalog.json').write_text(json.dumps(dict(item=a,weapon=b,revision='double-action-v1'),ensure_ascii=False,indent=2),encoding='utf8')
print('RSH12_DOUBLE_ACTION_CATALOG_SAVED')
