"""Merge only the five final V3 attachments, checking CRCs and content hashes."""
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
ROOT = PROJECT / 'SourceAssets/CropsV3_20261022'
SOURCE = ROOT / 'Source'
DOWNLOADS = Path('C:/Users/allan/Downloads')
PACKAGES = [
    'Crops_V3_01_RootCropModels.zip',
    'Crops_V3_02_TomatoWheatModels.zip',
    'Crops_V3_03_LeafTextures.zip',
    'Crops_V3_04_PlantSurfaceTextures.zip',
    'Crops_V3_05_GroundAndWheatTextures.zip',
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    files, packages, duplicates = {}, [], []
    for name in PACKAGES:
        path = DOWNLOADS / name
        with zipfile.ZipFile(path) as archive:
            bad = archive.testzip()
            if bad:
                raise RuntimeError(f'CRC failure: {name}/{bad}')
            for entry in archive.infolist():
                rel = Path(entry.filename)
                if rel.is_absolute() or '..' in rel.parts or ':' in entry.filename or '\\' in entry.filename:
                    raise RuntimeError(f'Unsafe archive path: {entry.filename}')
                if entry.is_dir():
                    continue
                data = archive.read(entry)
                if entry.filename in files:
                    if files[entry.filename] != data:
                        raise RuntimeError(f'Conflicting duplicate: {entry.filename}')
                    duplicates.append(entry.filename)
                else:
                    files[entry.filename] = data
        packages.append({'filename': name, 'bytes': path.stat().st_size,
                         'sha256': sha(path.read_bytes()), 'crc_ok': True})
    verification = json.loads(files['package_verification.json'])
    expected = verification['files']
    for name, digest in expected.items():
        if name not in files or sha(files[name]) != digest:
            raise RuntimeError(f'Missing or mismatched package content: {name}')
    payload = {n for n in files if n.endswith(('.fbx', '.png'))}
    if payload != set(expected):
        raise RuntimeError('Unexpected model/texture files')
    manifest = json.loads(files['variant_manifest.json'])
    models = [n for n in files if n.endswith('.fbx')]
    textures = [n for n in files if n.endswith('.png')]
    if len(models) != 108 or len(textures) != 44:
        raise RuntimeError(f'Unexpected counts {len(models)}, {len(textures)}')
    for name, data in files.items():
        target = SOURCE / name
        if target.exists() and target.read_bytes() != data:
            raise RuntimeError(f'Existing source differs: {target}')
    SOURCE.mkdir(parents=True, exist_ok=True)
    (ROOT / 'Packages').mkdir(exist_ok=True)
    (ROOT / 'Receipts').mkdir(exist_ok=True)
    for name, data in files.items():
        target = SOURCE / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(data)
    for name in PACKAGES:
        target = ROOT / 'Packages' / name
        if target.exists() and sha(target.read_bytes()) != sha((DOWNLOADS / name).read_bytes()):
            raise RuntimeError(f'Existing package differs: {target}')
        if not target.exists():
            shutil.copy2(DOWNLOADS / name, target)
    from PIL import Image
    images = []
    for name in sorted(textures):
        with Image.open(SOURCE / name) as im:
            im.verify()
        with Image.open(SOURCE / name) as im:
            images.append({'file': name, 'size': list(im.size), 'mode': im.mode})
    report = {'packages': packages, 'unique_files': len(files), 'identical_duplicates': len(duplicates),
              'fbx_count': len(models), 'lod0_count': sum('_LOD' not in n for n in models),
              'lod_files': sum('_LOD' in n for n in models), 'texture_count': len(textures),
              'verified_payload_sha256': expected, 'images': images,
              'import_script_in_package': any(n.endswith('.py') for n in files),
              'editable_blend_in_package': any(n.endswith('.blend') for n in files),
              'manifest_keys': list(manifest), 'runtime_tested': False}
    (ROOT / 'Receipts/package-audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('images', 'verified_payload_sha256', 'packages')}, indent=2))
    print('Manifest keys:', list(manifest))
    print('Manifest first record:', json.dumps(next(v for v in manifest.values() if isinstance(v, list) and v and isinstance(v[0], dict))[0], indent=2))


if __name__ == '__main__':
    main()
