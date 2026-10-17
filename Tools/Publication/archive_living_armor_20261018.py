"""Move/restore only the reviewed LivingArmor20261018 retirement manifest.

No deletion, overwrite, engine launch, Git staging, or gameplay tests.
Run from this project's Tools/Publication: archive_living_armor_20261018.py archive
Use 'restore' only when the retired versions are deliberately needed again.
"""
import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECORDS = ROOT / 'Docs/Publication/LivingArmor20261018'
TRASH = ROOT / 'trash/living-armor-retired-20261018'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(mode):
    rows = json.loads((RECORDS / 'archive-plan.json').read_text(encoding='utf-8'))['files']
    pending = []
    for row in rows:
        original = (ROOT / row['source']).resolve()
        retired = (ROOT / row['destination']).resolve()
        if not original.is_relative_to(ROOT) or not retired.is_relative_to(TRASH):
            raise RuntimeError('Manifest path outside the reviewed roots')
        if original.is_relative_to(TRASH):
            raise RuntimeError('Original cannot already be inside this trash folder')
        source, destination = (original, retired) if mode == 'archive' else (retired, original)
        if source.exists() and destination.exists():
            raise RuntimeError('Preserve both existing files: ' + row['source'])
        present = source if source.exists() else destination
        if not present.is_file() or sha(present) != row['sha256']:
            raise RuntimeError('File missing or changed: ' + str(present))
        pending.append((source, destination, row))
    for source, destination, row in pending:
        if source.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
        if source.exists() or sha(destination) != row['sha256']:
            raise RuntimeError('Move read-back mismatch: ' + row['source'])
    receipt = {'operation': mode, 'finished_utc': datetime.now(timezone.utc).isoformat(),
               'files': len(rows), 'bytes': sum(x['bytes'] for x in rows),
               'all_file_hashes_matched': True, 'deleted_files': 0,
               'manifest': 'archive-plan.json'}
    (RECORDS / (mode + '-receipt.json')).write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['archive', 'restore'])
    run(parser.parse_args().operation)
