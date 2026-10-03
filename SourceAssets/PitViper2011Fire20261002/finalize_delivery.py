"""Record actual production receipts; no asset inspection or runtime test."""
import json
from pathlib import Path
from datetime import datetime, timezone

job = Path(__file__).parent
def read(name, default):
    path = job / name
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else default
sources = read('source_receipt.json', {})
assets = read('import_receipt.json', {})
build = read('build_receipt.json', {'status': 'pending_regular_editor_build'})
receipt = dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(),
    definition='ue_pit_viper2011', reference='M1911 pistol',
    source_status=sources.get('status'), source_clip_count=len(sources.get('clips', [])),
    asset_status=assets.get('status'), saved_animation_count=len(assets.get('saved', [])),
    native_build_status=build.get('status'), native_build=build,
    runtime_tested=False, acceptance_rendered=False)
family_keys = {'Single': 'single', 'Dual/r': 'r', 'Dual/l': 'l'}
receipt['current_sources_imported'] = bool(sources.get('clips')) and all(
    assets.get('animations', {}).get(family_keys[row['family']] + '/' + row['kind'], {}).get('source_sha256') == row['sha256']
    for row in sources.get('clips', []))
receipt['complete'] = receipt['source_status'] == 'saved' and receipt['asset_status'] == 'imported_and_saved' and receipt['native_build_status'] == 'Succeeded' and receipt['current_sources_imported']
(job / 'delivery_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf8')
print('PIT_VIPER_FIRE_DELIVERY_RECORDED', json.dumps(receipt, ensure_ascii=False))
