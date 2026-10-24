from pathlib import Path
from datetime import datetime
import runpy,json
R=Path(__file__).resolve().parent
runpy.run_path(str(R/'build_assets.py'))['main']()
runpy.run_path(str(R/'install_level.py'))['main']()
assets=json.loads((R/'assets_saved.json').read_text());saved=json.loads((R/'installed.json').read_text())
(R/'completed.json').write_text(json.dumps(dict(stage='production_completed',completed_at=datetime.now().astimezone().isoformat(),map_saved_at=saved['saved_at'],skyline_actors=len(saved['skyline_actors']),buildings=saved['buildings'],landmarks=saved['landmarks'],facade_families=saved['facade_families'],mesh_count=len(assets['meshes']),triangles=sum(row['triangles'] for row in assets['meshes'].values()),shader_compiled=assets['shader_compiled'],game_tested=False,performance_measured=False,interactive_editor_started=False),indent=2),encoding='utf8')
print('AP17_PRODUCTION_COMPLETED')
