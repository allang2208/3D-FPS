"""Read only the package ownership needed before this task writes shared Content."""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
host = u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path()).replace('\\', '/')
if '/FPSGAME/' not in host and '/FPSGAME-mp/' not in host:
    raise RuntimeError('The active editor does not use this task shared Content.')
packages = ['/Game/GameMaps/DayNight_Lighting']
for file in ('ue_delivery.json', 'gameplay_delivery.json'):
    if (ROOT/file).exists():
        packages.extend(a.split('.')[0] for a in json.loads((ROOT/file).read_text(encoding='utf-8')).get('assets', []))
result = {'host_project': host, 'loaded_packages_in_task_scope': [p for p in sorted(set(packages)) if u.find_object(None, p)]}
print(json.dumps(result, ensure_ascii=False))
(ROOT/'loaded_package_ownership.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
