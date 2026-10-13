"""Apply the requested GPU footprint and keep current authoring metadata in sync."""
from pathlib import Path
import json,re,shutil
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
path=PROJECT/'Content/ColdSteelData/items.json';raw=path.read_text('utf-8-sig')
match=re.search(r'^  "search_graphics_card":\s*',raw,re.M);start=match.end()
item,length=json.JSONDecoder().raw_decode(raw[start:]);before=dict(item)
item.update(grid_w=2,grid_h=1)
block=json.dumps(item,ensure_ascii=False,indent=2).replace('\n','\n  ')
path.write_text(raw[:start]+block+raw[start+length:],encoding='utf-8')
design_path=PROJECT/'Docs/Gameplay/search-item-catalog-v2-20261012.json'
design=json.loads(design_path.read_text('utf-8'))
gpu=next(i for i in design['items'] if i['id']=='search_graphics_card')
previous_design=dict(gpu)
gpu.update(grid_w=2,grid_h=1,sell_souls_per_cell=1200.0,full_stack_sell_souls_per_cell=1200.0,
    pickup_reason='基础出售收益1200灵魂/格，单件就有带回价值，不要求先攒满一叠。')
design_path.write_text(json.dumps(design,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for name in ('model_manifest.json','texture_manifest.json'):
    source=PROJECT/'SourceAssets/ServerOriginalMarks20261013'/name
    shutil.copy2(source,ROOT/'Receipts'/('previous_gpu_'+name))
    data=json.loads(source.read_text('utf-8'));data['assets']['GPU'].update(grid_w=2,grid_h=1)
    source.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'Receipts/footprint.json').write_text(json.dumps(dict(id=item['id'],before=before,after=item,
    previous_design=previous_design,price_changed=False,save_files_edited=False),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('GPU_FOOTPRINT_CONFIGURED',item['grid_w'],item['grid_h'])
