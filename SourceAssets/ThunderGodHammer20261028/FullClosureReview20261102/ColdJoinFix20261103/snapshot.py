from pathlib import Path
import difflib
import hashlib
import json

OUT = Path(__file__).parent
SOURCE = Path('D:/FPS3D/FPSGAME/Source/FPSGAME/Characters')
patch, rows = [], []
for before in sorted((OUT / 'Before').glob('*')):
    current = SOURCE / before.name
    old = before.read_text(encoding='utf-8-sig')
    new = current.read_text(encoding='utf-8-sig')
    if old == new:
        continue
    relative = 'Source/FPSGAME/Characters/' + before.name
    patch.extend(difflib.unified_diff(old.splitlines(True), new.splitlines(True), fromfile='a/' + relative, tofile='b/' + relative))
    rows.append({'file': relative, 'before_sha256': hashlib.sha256(before.read_bytes()).hexdigest(), 'after_sha256': hashlib.sha256(current.read_bytes()).hexdigest()})
(OUT / 'source-changes.patch').write_text(''.join(patch), encoding='utf-8')
(OUT / 'source-changes.json').write_text(json.dumps({'scope': 'Local before snapshots, not a clean Git baseline', 'files': rows}, indent=2), encoding='utf-8')
print('Recorded', len(rows), 'changed source files')
