"""Publish the scoped source records after UE installation, preserving old source data."""
import json
import shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
receipt=json.loads((ROOT/'Receipts/install.json').read_text(encoding='utf-8'))
if receipt['stage']!='map_saved':raise RuntimeError('Finish installation before publishing source records')
dest=ROOT.parent/'DungeonTreasure20260922/Authored'
source=json.loads((ROOT/'Authored/manifest.json').read_text(encoding='utf-8'))
old=json.loads((dest/'manifest.json').read_text(encoding='utf-8'))
backup=ROOT/'Sources/treasure-manifest-before.json'
if not backup.exists():shutil.copy2(dest/'manifest.json',backup)
old['objects']=[o for o in old['objects'] if o['room']!='TreasureLink']+source['objects']
(dest/'manifest.json').write_text(json.dumps(old,indent=2),encoding='utf-8')
print('TREASURE_CONNECTOR_SOURCE_RECORDS_PUBLISHED')
