"""Publish the runtime sparse layers after the five animation replacements."""
import unreal as u,importlib.util,json
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir())).resolve()!=(P/'Content').resolve():raise RuntimeError('Wrong project content')
spec=importlib.util.spec_from_file_location('hk416_refresh_profiles',O.parent/'HK416CommonAttachments20260930/import_grip_profiles.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
report=module.refresh_empty_drum_profiles(O)
file=O/'import_receipt.json';receipt=json.loads(file.read_text());receipt['runtime_profiles']=report;receipt['status']='mesh, five animations and runtime grip corrections saved; source catalogs published'
file.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('HK416_RUNTIME_DRUM_LAYERS_SAVED',json.dumps(report),flush=True)
