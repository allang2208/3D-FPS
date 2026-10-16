"""Update only the installed duckbill's cosmetic description, retaining stats."""
from pathlib import Path
import json,shutil
O=Path(__file__).parent;P=O.parents[1];path=P/'Content/ColdSteelData/gunsmith.json'
text=path.read_text(encoding='utf-8-sig');catalog=json.loads(text)
weapon=next(w for w in catalog['weapons'] if w['id']=='ue_super90')
option=next(o for o in weapon['options']['muzzle'] if o['id']=='shotgun_duckbill')
old=option['description']
new='封闭侧壁将上下鸭舌连接成扁宽壳体，前方保留横向开口；收腰肩部、浅槽与刻槽安装环采用分区金属表面。'
before=O/'Before';before.mkdir(exist_ok=True)
if not (before/'gunsmith.json').exists():shutil.copy2(path,before/'gunsmith.json')
if old!=new:
    old_json=json.dumps(old,ensure_ascii=False);new_json=json.dumps(new,ensure_ascii=False)
    if text.count(old_json)!=1:raise RuntimeError('Description has multiple owners; preserve catalog')
    path.write_text(text.replace(old_json,new_json,1),encoding='utf-8',newline='\n')
# Keep the existing catalog authoring entrypoint from restoring the old wording.
for name in ('integrate_catalog.py','prepare_pipeline.py'):
    source=P/'SourceAssets/Super90DuckbillV2_20261016'/name
    content=source.read_text(encoding='utf-8')
    content=content.replace('上下双层鸭舌向前展开，侧面留出开口，收腰肩部连接刻槽安装环；唇缘、浅槽与沉入式紧固件采用分区金属表面。',new)
    source.write_text(content,encoding='utf-8')
(O/'catalog_receipt.json').write_text(json.dumps({'part':option['id'],'description':new,
    'stats_preserved':option['stats'],'special_effects_preserved':option['special_effects']},ensure_ascii=False,indent=2),encoding='utf-8')
print('DUCKBILL_DESCRIPTION_UPDATED')
