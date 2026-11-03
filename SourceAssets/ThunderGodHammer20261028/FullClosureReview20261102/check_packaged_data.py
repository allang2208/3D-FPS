"""Check hammer data and the two repaired icons in the actual staged UFS pak."""
from pathlib import Path
import json
import re

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = Path(__file__).parent
listing = (OUT / 'packaged-ufs-list.log').read_text(encoding='utf-8-sig')
paths = [
    'ColdSteelData/thunder-god-hammer-modules.json',
    'ColdSteelData/thunder-god-hammer-gunsmith.json',
    'ColdSteelData/AttachmentIcons20260913/ue_thunder_god_hammer_grip_static_field_grip.png',
    'ColdSteelData/AttachmentIcons20260913/ue_thunder_god_hammer_grip_coil_grip.png',
]
rows = []
for relative in paths:
    pak_path = 'FPSGAME/Content/' + relative
    match = re.search(r'"' + re.escape(pak_path) + r'" offset: (\d+), size: (\d+) bytes, sha1: (\w+), compression: (\w+)\.', listing)
    rows.append({
        'path': relative,
        'source_exists': (ROOT / 'Content' / relative).is_file(),
        'loose_staged_exists': (OUT / 'Package/Windows/FPSGAME/Content' / relative).is_file(),
        'present_in_actual_pak': bool(match),
        'pak_path': pak_path,
        'pak_entry': match.group(0) if match else None,
    })
result = {
    'passed': all(row['source_exists'] and row['present_in_actual_pak'] for row in rows),
    'method': 'UnrealPak -List of the actual archived FPSGAME-Windows.pak; UFS entries do not require loose copies',
    'checks': len(rows),
    'files': rows,
}
(OUT / 'staged-data-check.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print('Hammer UFS data/icon entries:', len(rows), 'passed:', result['passed'])
raise SystemExit(0 if result['passed'] else 1)
