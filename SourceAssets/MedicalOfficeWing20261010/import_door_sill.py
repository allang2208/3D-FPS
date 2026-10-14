import json,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parent
runpy.run_path(str(ROOT.parent/'DungeonIsolationWard20260929/Scripts/import_assets.py'),init_globals={'WARD_IMPORT_NAMES':{'SM_Ward_GlassDoorFrame'}})
path=ROOT/'Receipts/doorways-install.json';report=json.loads(path.read_text('utf8'))
report['ward_sill_below_floor_cm']=.5
path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
