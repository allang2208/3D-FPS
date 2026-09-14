"""Add only the two requested attachment categories to the 715 catalog row."""
import copy, json
from pathlib import Path
O=Path(__file__).parent;file=O.parents[1]/'Content/ColdSteelData/gunsmith.json'
text=file.read_text(encoding='utf-8');data=json.loads(text)
source=next(w for w in data['weapons'] if w['id']=='ue_m1911')
weapon=next(w for w in data['weapons'] if w['id']=='ue_dan_wesson715')
old=json.dumps(weapon,ensure_ascii=False,indent=2)
for slot in ['optic','tactical']:
    if slot not in weapon['allowed']:weapon['allowed'].append(slot)
    weapon['options'][slot]=copy.deepcopy(source['options'][slot])
for option in weapon['options']['optic']:
    if option['id']=='false':option['description']='使用 715 原厂照门与准星。'
    elif option['id']=='holographic':option['description']='手枪尺寸全息瞄具，专用上护罩底座与独立放大的分划；固定于枪体，不随弹仓摆动。'
    elif option['id']=='panoramic_red_dot':option['description']='手枪尺寸全景红点瞄具，保留开阔镜窗与清晰红点，使用 715 曲面安装座。'
# Replace the isolated JSON object, retaining all other rows and formatting.
start=text.index('    {\n      "id": "ue_dan_wesson715"')
decoder=json.JSONDecoder();_,count=decoder.raw_decode(text[start+4:]);end=start+4+count
replacement='\n'.join('    '+line for line in json.dumps(weapon,ensure_ascii=False,indent=2).splitlines())
file.write_text(text[:start]+replacement+text[end:],encoding='utf-8')
(O/'catalog-options.json').write_text(json.dumps({k:weapon[k] for k in ['id','allowed','options']},ensure_ascii=False,indent=2),encoding='utf-8')
print('DW715_CATALOG_UPDATED')
