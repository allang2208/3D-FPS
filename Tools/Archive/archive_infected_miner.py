"""Archive the user-rejected miner branch with per-file recovery hashes."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path('D:/FPS3D/FPSGAME').resolve()
ARCHIVE = (ROOT / 'trash/infected-miner-rejected-20260913').resolve()
DOCS = ROOT / 'Docs/Rejected'
MANIFEST = DOCS / 'infected-miner-archive-20260913.json'
ROOTS = ['Content/Monsters/InfectedMiner', 'Content/Tests/InfectedMiner',
         'SourceAssets/InfectedMiner20260912', 'SourceAssets/InfectedMiner20260913',
         'Tools/InfectedMiner', 'Saved/InfectedMiner']

def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def files():
    selected = set()
    for name in ROOTS:
        folder = (ROOT / name).resolve()
        assert folder.is_relative_to(ROOT) and not folder.is_relative_to(ARCHIVE)
        selected.update(p for p in folder.rglob('*') if p.is_file())
    for pattern in ('InfectedMiner*', 'MinerStateAnimInstance*'):
        selected.update((ROOT / 'Source/FPSGAME/Monsters').glob(pattern))
    selected.update((ROOT / 'Docs').glob('InfectedMiner*'))
    selected.update(p for p in (ROOT / 'Saved').rglob('*')
                    if p.is_file() and ('InfectedMiner' in p.as_posix()
                    or p.name.startswith(('A_Miner_', 'SK_InfectedMiner', 'PA_InfectedMiner'))))
    selected.update((ROOT / 'Content/__ExternalActors__/Tests/InfectedMiner').rglob('*'))
    selected.update((ROOT / 'Content/__ExternalObjects__/Tests/InfectedMiner').rglob('*'))
    # Saved publication workspaces may contain junctions into the live project.
    # Canonicalize before moving so the same physical path is archived once.
    return sorted({p.resolve() for p in selected if p.is_file()})

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--move', action='store_true')
    args = parser.parse_args()
    paths = files()
    counts = {}
    for path in paths:
        group = '/'.join(path.relative_to(ROOT).parts[:2])
        row = counts.setdefault(group, {'files': 0, 'bytes': 0})
        row['files'] += 1
        row['bytes'] += path.stat().st_size
    print(json.dumps(counts, indent=2))
    if not args.move:
        return
    scene = json.loads((DOCS / 'infected-miner-scene-removal-20260913.json').read_text(encoding='utf-8'))
    assert scene['status'] == 'removed_and_saved', 'Remove scene references before moving classes/assets'
    assert ARCHIVE.is_relative_to(ROOT / 'trash')
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8')) if MANIFEST.exists() else {
        'status': 'moving', 'decision': 'User rejected the entire infected miner on 2026-09-13',
        'archive_root': ARCHIVE.relative_to(ROOT).as_posix(), 'replacement': None,
        'scene_backups': scene['backups'], 'files': []}
    assert manifest['status'] == 'moving', 'Completed archive is not modified by rerunning'
    # A previous interrupted move may have completed its final rename before journaling.
    for entry in manifest['files']:
        original = (ROOT / entry['source']).resolve()
        target = (ROOT / entry['target']).resolve()
        assert original.is_relative_to(ROOT) and target.is_relative_to(ARCHIVE)
        assert not original.exists() and target.is_file()
        assert target.stat().st_size == entry['bytes'] and sha256(target) == entry['sha256']
        entry['state'] = 'archived'
    # Resolve every source/destination before the first move; rename stays on this drive.
    pairs = []
    for source in paths:
        assert not source.is_symlink()
        source = source.resolve()
        assert source.is_relative_to(ROOT) and not source.is_relative_to(ROOT / 'trash')
        destination = (ARCHIVE / source.relative_to(ROOT)).resolve()
        assert destination.is_relative_to(ARCHIVE) and not destination.exists()
        pairs.append((source, destination))
    DOCS.mkdir(parents=True, exist_ok=True)
    def save():
        MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for source, destination in pairs:
        size, digest = source.stat().st_size, sha256(source)
        entry = {'source': source.relative_to(ROOT).as_posix(),
                 'target': destination.relative_to(ROOT).as_posix(), 'bytes': size,
                 'sha256': digest, 'reason': 'Entire infected miner rejected; all iterations retired',
                 'replacement': None, 'state': 'pending'}
        manifest['files'].append(entry)
        save()
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.rename(destination)
        assert destination.stat().st_size == size and sha256(destination) == digest
        entry['state'] = 'archived'
    # Only remove now-empty directories inside the explicit source roots.
    for name in ROOTS:
        folder = (ROOT / name).resolve()
        assert folder.is_relative_to(ROOT) and not folder.is_relative_to(ROOT / 'trash')
        if folder.exists():
            for child in sorted((p for p in folder.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
                child.rmdir()
            folder.rmdir()
    manifest['status'] = 'archived_hashes_read_back'
    manifest['file_count'] = len(manifest['files'])
    manifest['bytes'] = sum(p['bytes'] for p in manifest['files'])
    save()
    (ARCHIVE / 'archive-manifest.json').write_bytes(MANIFEST.read_bytes())
    print(json.dumps({k: manifest[k] for k in ('status', 'file_count', 'bytes')}))

if __name__ == '__main__':
    main()
