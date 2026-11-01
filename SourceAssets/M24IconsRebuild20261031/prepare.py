"""Archive exact inputs and copy built-in imagegen outputs without image edits."""
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[1]
DISK = PROJECT / 'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms'
TEXTURES = PROJECT / 'Content/UI/AttachmentIcons20260913/FramedFirearms'
manifest = json.loads((OUT / 'production.json').read_text(encoding='utf-8'))
baseline_path = OUT / 'baseline.json'
if baseline_path.exists():
    raise RuntimeError('Baseline already exists; do not overwrite the production history')
baseline = {'created_utc': datetime.now(timezone.utc).isoformat(), 'files': {}}

def archive(path, destination):
    baseline['files'][str(path)] = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    if path.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)

for item in manifest['items']:
    shutil.copy2(item['output'], OUT / item['workspace_output'])
    shutil.copy2(DISK / (item['key'] + '.png'), OUT / 'Inputs' / (item['key'] + '.png'))
    for key in item['destinations']:
        archive(DISK / (key + '.png'), OUT / 'Before/PNG' / (key + '.png'))
        archive(TEXTURES / ('T_' + key + '.uasset'), OUT / 'Before/Textures' / ('T_' + key + '.uasset'))
shutil.copy2(manifest['frame_master'], OUT / 'Inputs/muzzle_brake_framed_v2.png')
shutil.copy2(PROJECT / 'SourceAssets/SkeletonSniperStock20261031/Icons/production.json', OUT / 'Inputs/model_sources.json')
baseline_path.write_text(json.dumps(baseline, indent=2), encoding='utf-8')
print('Prepared', len(manifest['items']), 'master images and', sum(len(i['destinations']) for i in manifest['items']), 'destination keys')
