"""Restore the user's local Fab Boots package without replacing existing files."""
import hashlib
import json
import zipfile
from pathlib import Path

PROJECT = Path('D:/FPS3D/FPSGAME')
RECORDS = PROJECT / 'SourceAssets/BootsEquipment20261004'
ARCHIVE = PROJECT.parent / 'VaultCache/FabLibrary/MetaHuman_Boots-c6596c37/metahuman/UE_5.7/oa_boots.mhpkg'
RECORDS.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(ARCHIVE) as package:
    manifest = json.loads(package.read('Manifest.json'))
    root = '/Game/Outfits/Boots'
    if manifest['assetData']['objectPath'] != root + '/OA_Boots.OA_Boots':
        raise RuntimeError('Unexpected Boots archive root')
    dest_root = (PROJECT / 'Content/Outfits/Boots').resolve()
    copied = []
    for name in package.namelist():
        if not name.endswith(('.uasset', '.ubulk', '.uexp')):
            continue
        destination = (dest_root / name).resolve()
        if not destination.is_relative_to(dest_root):
            raise RuntimeError('Archive path is outside the Boots folder')
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open('xb') as output:
                output.write(package.read(name))
            copied.append(str(destination.relative_to(PROJECT)))
    record = {'archive': str(ARCHIVE), 'sha256': hashlib.file_digest(ARCHIVE.open('rb'), 'sha256').hexdigest(),
              'manifest': manifest, 'copied': copied, 'use': 'User-owned local Fab package; no redistribution.'}
    (RECORDS / 'provenance.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print('BOOTS_PACKAGE_RESTORED', len(copied), flush=True)
