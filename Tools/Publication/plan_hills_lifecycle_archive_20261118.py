"""Inventory this batch only; never follow authoring-host junctions."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Docs/Publication/HillsVillageLifecycle20261118'
ARCHIVE = ROOT / 'trash/hills-village-lifecycle-20261118'
SAVED = [
    'Saved/HillsNetLoad20261118', 'Saved/HillsContinuity20261118',
    'Saved/HillsVillageInteractionAudit20261118', 'Saved/VillageBlacksmithArtR2',
    'Saved/VillageBlacksmithLoftR3', 'Saved/VillageBlacksmithWindowR7Production',
]
AUTHOR = [
    'SourceAssets/ChapelFurniture20261116', 'SourceAssets/ChapelShrineForecourt20261116',
    'SourceAssets/HillsVillageBlacksmith20261117', 'SourceAssets/HillsHilltopVillage20261117',
    'SourceAssets/HillsVillageBiome20261117', 'SourceAssets/HillsVillagePerimeter20261117',
]
RETAIN = [
    'Saved/HillsNetLoad20261118/fixed02/OriginalSaveBackup/',
    'Saved/HillsNetLoad20261118/lifecycle06/Host/Binaries/Win64/',
]

def scan(path):
    for entry in os.scandir(path):
        stat = entry.stat(follow_symlinks=False)
        if stat.st_file_attributes & 0x400:
            yield Path(entry.path), stat, True
        elif entry.is_dir(follow_symlinks=False):
            yield from scan(entry.path)
        else:
            yield Path(entry.path), stat, False

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def selected(rel):
    if any(rel.startswith(p) for p in RETAIN):
        return False
    if any(rel.startswith(p + '/') for p in SAVED):
        return True
    parts = Path(rel).parts
    # These directories are diagnostic renders / rollback snapshots, not textures.
    if any(p in {'Before', 'Check', 'Candidate', 'Preview', 'PreviewR1', 'Previews', 'Screenshots', 'Logs', '__pycache__'} for p in parts):
        return True
    if Path(rel).suffix.lower() in {'.log', '.gif', '.mp4', '.pyc'}:
        return True
    if Path(rel).name.endswith(('.before.cpp', '.before.json')):
        return True
    if Path(rel).name in {'sign-mask-review.png', 'layout-r3.png'}:
        return True
    return False

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / 'archive-receipt.json').exists():
        raise RuntimeError('This batch is already archived; preserve its original manifest.')
    rows = []
    for base in SAVED + AUTHOR:
        path = ROOT / base
        if not path.exists():
            continue
        for source, stat, link in scan(path):
            relative = source.relative_to(ROOT).as_posix()
            if not selected(relative):
                continue
            rows.append(dict(source=relative, destination=(ARCHIVE / relative).relative_to(ROOT).as_posix(),
                kind='junction' if link else 'file', bytes=0 if link else stat.st_size,
                sha256=None if link else digest(source),
                link_target=os.readlink(source) if link else None,
                reason='Completed diagnostic output, rebuildable isolated host, or superseded rollback snapshot',
                replacement='Current production source/assets and retained compact evidence; see README'))
    (OUT / 'retired-files.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    summary = dict(files=sum(r['kind']=='file' for r in rows), junctions=sum(r['kind']=='junction' for r in rows),
        bytes=sum(r['bytes'] for r in rows), images=sum(Path(r['source']).suffix.lower() in {'.png','.jpg','.jpeg'} for r in rows),
        gifs=sum(Path(r['source']).suffix.lower()=='.gif' for r in rows), retain=RETAIN)
    (OUT / 'archive-plan.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
