import json,sys
from pathlib import Path
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R))
import build_assets as b
b.report=json.loads((R/'assets_saved.json').read_text('utf8'))
b.report['stage']='refreshing_final_exports';b.record()
b.meshes();b.report['stage']='assets_saved';b.record()
if not (R/'Review/texture-exports.json').exists():b.export_material_sources()
print('BP3_FINAL_EXPORTS_SAVED')
