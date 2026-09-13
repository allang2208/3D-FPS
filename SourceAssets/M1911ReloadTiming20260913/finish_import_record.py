"""Resolve the rig identity named by the animation-only FBX import warning."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;report=json.loads((O/'import.json').read_text())
for kind,row in report.items():
    clip=u.load_asset(row['path']);row['skeleton']=clip.get_editor_property('skeleton').get_path_name();row.pop('target_skeleton',None)
(O/'import.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('M1911_RELOAD_IMPORT_RECORD '+json.dumps(report))
