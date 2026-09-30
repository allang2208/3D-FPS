"""Deploy the user-authorized remaining icon replacements, retaining originals."""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'SourceAssets/RemainingFramedIcons20260930'
CONTENT = ROOT / 'Content/ColdSteelData/AttachmentIcons20260913'
manifest = json.loads((WORK / 'deploy_manifest.json').read_text(encoding='utf-8-sig'))
sources = [(group, WORK / 'Generated' / (group['key'] + '.png')) for group in manifest['groups']]
missing = [str(source) for _, source in sources if not source.is_file()]
if missing:
    raise RuntimeError('Generation still pending: ' + ', '.join(missing))
receipt = []
for group, source in sources:
    for key in group['keys']:
        destinations = [CONTENT / (key + '.png')]
        if group['family'] == 'firearm':
            destinations.append(CONTENT / 'FramedFirearms' / (key + '.png'))
        for destination in destinations:
            relative = destination.relative_to(CONTENT)
            for suffix in ('.png', '.uasset'):
                old = destination.with_suffix(suffix)
                backup = ROOT / 'trash/modification-icons-20260930/RemainingFramedIcons20260930/Original' / relative.with_suffix(suffix)
                if old.is_file() and not backup.exists():
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(old, backup)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            receipt.append({'source': str(source.relative_to(ROOT)).replace('\\', '/'), 'destination': str(destination.relative_to(ROOT)).replace('\\', '/'), 'key': key, 'family': group['family']})
(WORK / 'deploy_result.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('Deployed', len(receipt), 'PNG paths from', len(sources), 'generated masters')
