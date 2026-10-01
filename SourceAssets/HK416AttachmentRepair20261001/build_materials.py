"""Compile HK416 attachment shader resources; no level, capture or gameplay."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;prior=json.loads((O/'actual_assets.json').read_text());report={}
for path in prior['materials']:
 if '/HK416/CommonAttachments20260930/Materials/' not in path:continue
 m=u.load_asset(path);errors=u.MaterialEditingLibrary.recompile_material(m)
 report[path]=[str(e) for e in errors]
 if not errors:u.EditorLoadingAndSavingUtils.save_packages([m.get_outermost()],False)
 (O/'shader_build.json').write_text(json.dumps(report,indent=2))
 print('HK416_SHADER_BUILD',m.get_name(),len(errors),flush=True)
