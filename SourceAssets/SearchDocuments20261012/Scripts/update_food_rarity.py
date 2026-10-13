"""Set the two authorized catalog tiers without changing other item fields."""
from pathlib import Path
from collections import Counter
import json
import re
PROJECT=Path(__file__).resolve().parents[3]
path=PROJECT/'Content/ColdSteelData/items.json'
text=path.read_text('utf-8-sig')
for identity in ('soda_can','baguette_bread'):
    start=text.index('  "'+identity+'": {')
    end=text.find('\n  },',start)
    if end<0:end=len(text)
    block=text[start:end]
    block=re.sub(r'("rarity"\s*:\s*")[^"]+("\s*,)',r'\g<1>uncommon\2',block,count=1)
    text=text[:start]+block+text[end:]
path.write_text(text,encoding='utf-8')
design=PROJECT/'Docs/Gameplay/search-item-catalog-v2-20261012.json'
data=json.loads(design.read_text('utf-8'))
for item in data['items']:
    if item['id'] in ('soda_can','baguette_bread'):
        item['rarity']='uncommon'
        item['source_definition']['rarity']='uncommon'
data['counts']['rarities']=dict(Counter(i['rarity'] for i in data['items']))
design.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
document=design.with_suffix('.md')
text=document.read_text('utf-8')
text=text.replace('4件白色物品是已有生存补给，2件绿色物品是木工材料','2件白色物品是矿泉水与普通面包，4件绿色物品是汽水、法棍及两种木工材料')
for code,name in (('D02','罐装汽水'),('D04','法棍面包')):
    text=text.replace(f'| {code} {name} | 普通·白 |',f'| {code} {name} | 优秀·绿 |')
text=text.replace('已有食物饮水保留现有颜色、效果、占格和堆叠','汽水与法棍按用户要求提升至绿色档；已有食物饮水保留效果、占格和堆叠')
document.write_text(text,encoding='utf-8')
print('FOOD_RARITY_SAVED soda_can=uncommon baguette_bread=uncommon')
