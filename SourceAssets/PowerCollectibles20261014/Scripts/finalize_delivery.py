"""Consolidate production receipts after map saving and required native builds."""
from datetime import datetime, timezone
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
read = lambda name: json.loads((ROOT / name).read_text('utf-8-sig'))
assets = read('Receipts/installation.json')
scene = read('Receipts/scene.json')
build = read('Receipts/build.json')
data = read('Receipts/data-installation.json')
presentation = read('presentation.json')
models = read('Receipts/ue-import.json')
completed = {row['target'] for row in build['results'] if row['exit_code'] == 0}
ready = (assets['stage'] == 'assets_installed' and scene['stage'] == 'map_saved'
         and {'FPSGAME', 'FPSGAMEEditor'} <= completed)
blocked_path = ROOT / 'Receipts/editor-build-blocked.json'
blocked = json.loads(blocked_path.read_text('utf-8-sig')) if blocked_path.exists() and not ready else None
report = dict(stage='assets_data_map_and_native_builds_delivered' if ready else 'integration_pending',
              timestamp_utc=datetime.now(timezone.utc).isoformat(),
              assets=models['meshes'], icons=presentation['icons'],
              saved_packages=assets['packages'], new_bindings=data['bindings'],
              map=scene, builds=build['results'],
              editor_build_blocker=blocked,
              old_unbound_containers_completed=10, new_toolboxes=2,
              power_searchable_containers=14, separate_existing_treasure_chests=1,
              multiplayer='Existing server-authoritative shared-container path with run-scoped storage, revisions and journal commits',
              tests_run=False, game_run=False, multiplayer_tested=False,
              presentation='Requested inventory icons rendered from delivered Blender geometry; no UE runtime preview')
(ROOT / 'delivery.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
print('POWER_COLLECTIBLES_DELIVERY', report['stage'])
