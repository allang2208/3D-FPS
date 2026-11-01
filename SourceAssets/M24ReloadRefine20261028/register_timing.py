import json
from pathlib import Path
O=Path(__file__).resolve().parent;root=O.parents[1]
path=root/'Content/ColdSteelData/gunsmith.json'
data=json.loads(path.read_text(encoding='utf-8-sig'))
weapon=next(w for w in data['weapons'] if w['id']=='ue_m24')
before={k:weapon['base'][k] for k in ('reload_time','empty_reload_time')}
weapon['base'].update(reload_time=84/30,empty_reload_time=134/30)
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(O/'timing_receipt.json').write_text(json.dumps({'before':before,'after':{k:weapon['base'][k] for k in before},'shared_source_frames':[0,8,18,26,32,38,42,50,54], 'paced_frames':[0,8,24,38,44,54,62,74,78]},indent=2))
print('M24_RELOAD_TIMING_SAVED',84/30,134/30)
