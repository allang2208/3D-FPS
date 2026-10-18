"""Publish only the new appearance fields and its actual rendered inventory icon."""
import json,shutil
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME');OUT=Path(__file__).resolve().parent
receipt=json.loads((OUT/'ue-assets.json').read_text())
path=ROOT/'Content/ColdSteelData/items.json'
catalog=json.loads(path.read_text(encoding='utf-8-sig'))
item=catalog['spoiled_food'];item['ue_icon']='Icons/spoiled_food.png';item['world_mesh']=receipt['mesh']
shutil.copy2(OUT/'spoiled_food.png',ROOT/'Content/ColdSteelData/Icons/spoiled_food.png')
path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'catalog-published.json').write_text(json.dumps({'id':'spoiled_food','ue_icon':item['ue_icon'],
    'world_mesh':item['world_mesh'],'gameplay_fields_changed':False,'icon_copied':True},indent=2))
print('Spoiled food catalog and PNG saved.')
