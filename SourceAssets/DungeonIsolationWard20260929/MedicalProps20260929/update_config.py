import json,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parent
props=runpy.run_path(str(ROOT/'prop_design.py'))['build_props']()
for name in ('room.json','module-draft.json'):
    path=ROOT.parent/'Config'/name
    cfg=json.loads(path.read_text(encoding='utf-8'));cfg['room_props']=props
    path.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
print('WARD_MEDICAL_PROPS_CONFIGURED',flush=True)
