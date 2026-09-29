"""Publish only the two refined exports into the original assembly source manifest."""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT.parent / 'DungeonFacilityScenes20260927' / 'Authored'
BACKUP = ROOT / 'Backup' / 'AuthorChain'
BACKUP.mkdir(parents=True, exist_ok=True)
source = json.loads((ROOT / 'Authored/manifest.json').read_text(encoding='utf-8'))
manifest_path = DEST / 'manifest.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
replacements = {item['name']: item for item in source['objects']}

for path in [manifest_path] + [DEST / (name + '.fbx') for name in replacements]:
    backup = BACKUP / path.name
    if path.exists() and not backup.exists():
        shutil.copy2(path, backup)

for index, item in enumerate(manifest['objects']):
    if item['name'] not in replacements:
        continue
    replacement = dict(replacements[item['name']])
    dest = DEST / (item['name'] + '.fbx')
    shutil.copy2(replacement['fbx'], dest)
    replacement['fbx'] = str(dest)
    manifest['objects'][index] = replacement
manifest['prop_refinement_source'] = str(ROOT / 'Authored/FacilityProps_Polished.blend')
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print('FACILITY_PROP_SOURCE_PUBLISHED', len(replacements))
