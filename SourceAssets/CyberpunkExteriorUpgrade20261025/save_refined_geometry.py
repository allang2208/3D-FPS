"""Save the additional landmark edge fabrication without rebuilding the city blueprints."""
from pathlib import Path
import runpy,json
R=Path(__file__).resolve().parent
d=runpy.run_path(str(R/'build_assets.py'))
d['report'].update(json.loads((R/'assets_saved.json').read_text()))
pending=R/'landmark_uv_repair.json'
d['remainder'](only='landmarks' if pending.exists() else None)
d['record']()
if pending.exists():pending.write_text(json.dumps(dict(stage='assets_saved')),encoding='utf8')
print('EXTERIOR_REFINED_GEOMETRY_SAVED',len(d['report']['meshes']),flush=True)
