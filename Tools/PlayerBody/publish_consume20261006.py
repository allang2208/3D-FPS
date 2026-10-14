"""Publish only the fitted baguette profile and saved third-person consume assets."""
import json
import runpy
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/Consume20261006'
convert=runpy.run_path(str(ROOT/'SourceAssets/FoodGrip20261003/publish_food_motion.py'))['runtime_family']
profile=json.loads((OUT/'baguette-grip.json').read_text())
for path,key,value in [
    (ROOT/'Content/ColdSteelData/potion_use_motion.json','baguette_bread',convert('baguette_bread',profile)),
    (ROOT/'SourceAssets/FoodGrip20261003/grip_profiles.json','baguette_bread',profile),
]:
    data=json.loads(path.read_text(encoding='utf-8-sig'));data[key]=value
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
receipt=OUT/'assets-saved.json'
if receipt.exists():
    saved=json.loads(receipt.read_text())
    path=ROOT/'Content/ColdSteelData/player_body.json'
    data=json.loads(path.read_text(encoding='utf-8-sig'))
    data['clips'].update(saved['runtime_clips'])
    data['consume_mouth_in_head']=saved['mouth_in_head']
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('CONSUME_CONFIGURATION_PUBLISHED')
