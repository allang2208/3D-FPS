"""Record the completed sound import and the shared ordinary Editor build."""
from pathlib import Path
from datetime import datetime
import json

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
build_log = PROJECT / 'Saved/BuildEditor/build-20260927-233829.log'
build = build_log.read_text(encoding='utf-8-sig', errors='replace')
imports = json.loads((ROOT / 'import_receipt.json').read_text(encoding='utf-8'))
if len(imports) != 4 or not all(row['saved'] for row in imports):
    raise RuntimeError('Four saved fire assets are required before recording completion')
if 'Result: Succeeded' not in build or 'Compile [x64] FPSGAMECharacter.cpp' not in build:
    raise RuntimeError('The recorded normal Editor build is not complete')
receipt = {
    'weapon_id': 'ue_lmg201', 'status': 'authored_imported_and_editor_module_built',
    'completed_at': datetime.now().astimezone().isoformat(),
    'source_url': 'https://www.bilibili.com/video/BV11xwQz5EHS/',
    'source_request_start': 25,
    'audio_variants': imports,
    'provenance': 'provenance.json',
    'native_files': ['Source/FPSGAME/FPSGAMECharacter.cpp', 'Source/FPSGAME/Weapons/LMG201WeaponAssets.h'],
    'native_source_written_at': '2026-09-27T23:37:32+08:00',
    'ordinary_editor_build': str(build_log.relative_to(PROJECT)),
    'build_started_after_source_change': True,
    'shared_build_compiled_character_translation_unit': True,
    'editor_dll': 'Binaries/Win64/UnrealEditor-FPSGAME.dll',
    'editor_dll_written_at': '2026-09-27T23:40:31+08:00',
    'editor_or_game_started_for_this_task': False,
    'auditioned': False, 'game_tested': False,
    'scope': '201 unsuppressed fire one-shot and repeat-fire variants only',
}
(ROOT / 'DELIVERY.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('LMG201_FIRE_DELIVERY_RECORDED', len(imports))
