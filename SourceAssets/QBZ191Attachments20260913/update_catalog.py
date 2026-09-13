import json,copy
from pathlib import Path
P=Path(__file__).parents[2]/'Content/ColdSteelData/gunsmith.json'
raw=P.read_text(encoding='utf-8-sig');data=json.loads(raw);m4=next(x for x in data['weapons'] if x['id']=='ue_m4a1');qbz=next(x for x in data['weapons'] if x['id']=='ue_qbz191')
qbz['allowed']=copy.deepcopy(m4['allowed'])
for slot in ['magazine','muzzle','stock']:qbz['options'][slot]=copy.deepcopy(m4['options'][slot])
for slot,options in qbz['options'].items():
 for option in options:
  option['description']=option.get('description','').replace('M4','QBZ-191')
  if option['id']=='large_drum':option['description']='50 发弹鼓，使用 QBZ-191 专用供弹颈及环抱换弹动作。'
  if option['id']=='skeleton':option['description']='镂空战术枪托，使用 QBZ-191 专用机匣连接座与贴合肩垫。'
  if option['id']=='qr_performance':option['description']='QR 性能枪托，保留缓冲肩垫及调节结构，通过专用连接座贴合 QBZ-191 机匣。'
# Replace only this weapon's JSON object, preserving the other concurrent entries.
start=raw.rfind('    {',0,raw.index('"id": "ue_qbz191"'));decoder=json.JSONDecoder();old,used=decoder.raw_decode(raw[start+4:])
formatted=json.dumps(qbz,ensure_ascii=False,indent=2);replacement='\n'.join('    '+line for line in formatted.splitlines())
P.write_text(raw[:start]+replacement+raw[start+4+used:],encoding='utf-8')
print('QBZ_CATALOG_UPDATED')
