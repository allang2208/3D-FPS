"""Repair every authored boundary wall in place, retaining village circulation."""
import json
from wall_support import SOURCE,fit_plan

plan=json.loads((SOURCE/'layout.json').read_text(encoding='utf-8'))
fit_plan(plan)
(SOURCE/'layout.json').write_text(json.dumps(plan,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print('GROUNDED_BOUNDARY_WALLS',sum(len(w['native_instances']) for w in plan['yard_walls']))
