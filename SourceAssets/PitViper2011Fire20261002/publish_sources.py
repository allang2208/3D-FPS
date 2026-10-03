"""Publish only this batch's fire FBX files and authoring rows."""
import hashlib
import json
import shutil
from pathlib import Path

job = Path(__file__).parent
canonical = job.parent / 'PitViper2011Integration20261002'
rows = []
for relative in ('Single', 'Dual/r', 'Dual/l'):
    source = job / relative
    target = canonical / relative
    new = json.loads((source / 'authoring.json').read_text(encoding='utf8'))
    metadata = target / 'authoring.json'
    original = metadata.read_text(encoding='utf8')
    merged = json.loads(original)
    backup = job / 'BeforeSources' / relative
    backup.mkdir(parents=True, exist_ok=True)
    if not (backup / 'authoring.json').exists():
        shutil.copy2(metadata, backup / 'authoring.json')
    for kind, clip in new['clips'].items():
        destination = target / clip['file']
        old = backup / clip['file']
        if destination.exists() and not old.exists():
            old.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(destination, old)
        shutil.copy2(source / clip['file'], destination)
        merged['clips'][kind] = clip
        rows.append(dict(family=relative, kind=kind, file=str(destination),
                         sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
                         duration=clip['duration'], fire_motion=clip['fire_motion']))
    if metadata.read_text(encoding='utf8') != original:
        raise RuntimeError('Authoring metadata changed during publication: ' + str(metadata))
    metadata.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding='utf8')
(job / 'source_receipt.json').write_text(json.dumps(dict(status='saved', clips=rows,
    editable_sources=[str(job / p / ('PitViper2011_' + side + '_Editable.blend'))
                      for p, side in [('Single', 'single'), ('Dual/r', 'r'), ('Dual/l', 'l')]],
    runtime_tested=False), ensure_ascii=False, indent=2), encoding='utf8')
print('PIT_VIPER_FIRE_SOURCES_PUBLISHED', len(rows))
