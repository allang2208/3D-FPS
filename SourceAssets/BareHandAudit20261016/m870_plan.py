"""Offline plan for the M870 meshes in SnapshotsM870/ (same rules as plan_ue.py)."""
import json
from pathlib import Path
from plan_ue import run

O = Path(__file__).parent
rows, plans = [], []
for f in sorted((O / 'SnapshotsM870').glob('*.json')):
    if f.stem == 'index': continue
    r, p = run(f); rows.append(r)
    if p: plans.append(p)
    print(r['path'], {k: r.get(k) for k in ('before', 'after', 'notes', 'normal_corners', 'max_change_mm', 'plan_ok')})
(O / 'ue_plans_m870.json').write_text(json.dumps(plans))
(O / 'ue_findings_m870.json').write_text(json.dumps(rows, indent=1))
print('PLANNED', len(plans))
