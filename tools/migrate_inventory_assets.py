"""Copy original definitions and their UI imagery, preserving relative paths."""
import json
import shutil
from pathlib import Path

SOURCE = Path('E:/无尽轮回/长期备份/2026-7-13-1/game-dev')
TARGET = Path(__file__).resolve().parents[1]
data = json.loads((SOURCE / 'data/equipment.json').read_text(encoding='utf-8-sig'))
copied, missing = [], []
for item in data['equipment'].values():
    for key in ('slotImage', 'iconImage'):
        value = item.get(key)
        if not isinstance(value, str) or not value.startswith('assets/'):
            continue
        src = SOURCE / value
        dest = TARGET / 'assets/original_ui' / value
        if src.is_file():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            copied.append(value)
        else:
            missing.append(value)
(TARGET / 'assets/data/equipment.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
for src in (SOURCE / 'assets/ui/cursors').glob('*.png'):
    dest = TARGET / 'assets/original_ui/assets/ui/cursors' / src.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
manifest = {'source': str(SOURCE), 'definitions': len(data['equipment']), 'copied': sorted(set(copied)), 'missing': sorted(set(missing))}
(TARGET / 'assets/data/inventory-migration.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'definitions': manifest['definitions'], 'images': len(manifest['copied']), 'missing': manifest['missing']}, ensure_ascii=False))
