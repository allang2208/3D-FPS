"""Publish native 715 reload timing to the RSH objects only."""
import json,importlib.util
from pathlib import Path
O=Path(__file__).parent
spec=importlib.util.spec_from_file_location('rsh_catalog',O.parent/'RSH12SingleAction20261003/publish_catalog.py')
catalog=importlib.util.module_from_spec(spec);spec.loader.exec_module(catalog);catalog.O=O
receipt=json.loads((O/'import_receipt.json').read_text(encoding='utf8'))
if not receipt.get('complete') or receipt.get('revision')!='native-715-v1':raise RuntimeError('Native assets not saved')
def item(v):
    v['desc']='俄罗斯大口径双动左轮，使用12.7毫米弹药与五发弹巢。沿用715原生握持和动作，单持、双持与副手均逐发装填；空仓先退壳，非空仓保留余弹。'
def weapon(v):
    # Empty five-round source: 1.5 + 5*1.1 + .7. Normal baseline:
    # .6 + 5*1.1 + .7. The runtime selects the actual missing-round clip.
    v['base'].update(fire_interval=.4,reload_time=6.8,empty_reload_time=7.7)
    for option in v['options'].get('reload_device',[]):
        if option['id']=='false':option.update(name='逐发装填',description='五发弹巢；非空仓保留余弹，空仓先退壳，沿用715原生逐发装填动作。')
    for trait in v.get('traits',[]):
        if any(s in trait.get('text','') for s in ('速装','逐发','单动','拨锤')):
            trait['text']='双动左轮；五发弹巢，原生715动作与逐发装填。'
data=O.parents[1]/'Content/ColdSteelData'
a=catalog.write_object(data/'items.json','ue_rsh12',item)
b=catalog.write_object(data/'gunsmith.json','ue_rsh12',weapon,'weapons')
(O/'catalog.json').write_text(json.dumps(dict(item=a,weapon=b,revision='native-715-v1'),ensure_ascii=False,indent=2),encoding='utf8')
print('RSH12_NATIVE_715_CATALOG_SAVED')
