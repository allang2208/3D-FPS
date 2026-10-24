from pathlib import Path
from datetime import datetime
import runpy,json
R=Path(__file__).resolve().parent
runpy.run_path(str(R/'build_assets.py'))['main']()
runpy.run_path(str(R/'install_level.py'))['main']()
assets=json.loads((R/'assets_saved.json').read_text());saved=json.loads((R/'installed.json').read_text())
report=dict(stage='production_completed',completed_at=datetime.now().astimezone().isoformat(),map_saved_at=saved['saved_at'],mesh_count=len(assets['meshes']),triangles=sum(row['triangles'] for row in assets['meshes'].values()),shader_compiled=assets['shader_compiled'],game_tested=False,performance_measured=False,interactive_editor_started=False)
for key in ['lobbies','lookouts','terminals','moored_ferries','new_dynamic_lights','new_tick_actors','new_capture_actors']:report[key]=saved[key]
(R/'completed.json').write_text(json.dumps(report,indent=2),encoding='utf8');print('AP18_PRODUCTION_COMPLETED')
