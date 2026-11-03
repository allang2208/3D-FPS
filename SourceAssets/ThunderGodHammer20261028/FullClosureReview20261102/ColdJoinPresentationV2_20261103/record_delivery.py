import difflib
import hashlib
import json
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
receipt = json.loads((HERE / 'build-receipt.json').read_text(encoding='utf-8-sig'))
if not receipt.get('compiled') or not receipt.get('owned_sources_unchanged_during_build'):
    raise RuntimeError('Final build did not finish with unchanged owned sources')

rows, patch = [], []
for before in sorted((HERE / 'Before').iterdir()):
    relative = Path('Source/FPSGAME/Characters') / before.name
    after = ROOT / relative
    old, new = before.read_bytes(), after.read_bytes()
    rows.append(dict(file=relative.as_posix(), before_sha256=hashlib.sha256(old).hexdigest(), after_sha256=hashlib.sha256(new).hexdigest()))
    patch.extend(difflib.unified_diff(old.decode('utf-8-sig').splitlines(keepends=True), new.decode('utf-8-sig').splitlines(keepends=True), fromfile='before/'+relative.as_posix(), tofile='after/'+relative.as_posix()))
(HERE / 'source-changes.patch').write_bytes(''.join(patch).encode('utf-8'))
(HERE / 'source-changes.json').write_text(json.dumps(dict(scope='local before snapshots, not a clean Git baseline', files=rows), indent=2), encoding='utf-8')
delivery = dict(date=datetime.now().astimezone().isoformat(), implemented=True, compiled=True, runtime_tested=False,
                status='implemented_and_built_awaiting_user_test', source_files=len(rows), build=receipt,
                scope='Complete animated fallback during initial loading; aggregate head/outfit/helmet/modular readiness; retain fallback on asset failure. No new RPC or replicated fields.',
                imported_assets=False, fallback_asset='/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple.SKM_Manny_Simple')
(HERE / 'delivery.json').write_text(json.dumps(delivery, indent=2), encoding='utf-8')
print(json.dumps(dict(compiled=True, source_files=len(rows), runtime_tested=False)))
