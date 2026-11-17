"""Activate saved V6 assets through the existing centralized runtime contract.

Only three soft paths, the matching smoke budget and one Cook directory change.
Run outside UE after the author receipt. Native binaries still require a build.
"""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/MeteorCombustionV6_20261114'
DEST = '/Game/Skills/FireMagic20260921/MeteorCombustionV6'


def edit(relative, replacements):
    path = ROOT / relative
    raw = path.read_bytes()
    content = raw.decode('utf-8-sig')
    newline = '\r\n' if b'\r\n' in raw else '\n'
    modified = content
    for old, new in replacements:
        old, new = old.replace('\n', newline), new.replace('\n', newline)
        if new in modified:
            continue
        if modified.count(old) != 1:
            raise RuntimeError('Current source changed; preserve ' + relative)
        modified = modified.replace(old, new, 1)
    if modified == content:
        return
    backup = OUT / 'Before' / relative
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(path, backup)
    if path.read_bytes() != raw:
        raise RuntimeError('Concurrent edit; preserve ' + relative)
    encoding = 'utf-8-sig' if raw.startswith(b'\xef\xbb\xbf') else 'utf-8'
    path.write_bytes(modified.encode(encoding))
    print('METEOR_V6_INTEGRATED ' + relative, flush=True)


def main():
    receipt = json.loads((OUT / 'asset-receipt.json').read_text(encoding='utf-8'))
    if not receipt.get('complete'):
        raise RuntimeError('Finish background asset authoring before activation')
    replacements = []
    for old, name in [
        ('RealisticV5/NS_MeteorNaturalMantle.NS_MeteorNaturalMantle', 'NS_MeteorSheathV6'),
        ('RealisticV5/NS_MeteorNaturalWake.NS_MeteorNaturalWake', 'NS_MeteorSlipstreamV6'),
        ('MeteorImpactWeightV5/NS_MeteorImpact.NS_MeteorImpact', 'NS_MeteorCollisionV6')]:
        replacements.append(('/Game/Skills/FireMagic20260921/' + old, DEST + '/' + name + '.' + name))
    edit('Source/FPSGAME/Skills/MeteorAssets.h', replacements)
    edit('Source/FPSGAME/Skills/FPSMeteorStrike.cpp', [
        ('Budget->ConfigureSmoke(FX,18,bWaterContact)', 'Budget->ConfigureSmoke(FX,16,bWaterContact)')])
    cook = '+DirectoriesToAlwaysCook=(Path="' + DEST + '")'
    previous = '+DirectoriesToAlwaysCook=(Path="/Game/Skills/FireMagic20260921/MeteorImpactWeightV5")'
    edit('Config/DefaultGame.ini', [(previous, previous + '\n' + cook)])
    (OUT / 'integration-receipt.json').write_text(json.dumps(dict(
        integrated=True, assets=receipt['saved_assets'], native_build_required=True,
        protected=['rock', 'ground fire V4', 'damage', 'radius', 'duration', 'casting', 'replication', 'sound', 'camera'],
        runtime_tested=False), indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
