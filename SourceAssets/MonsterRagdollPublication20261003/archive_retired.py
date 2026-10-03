"""Archive this ragdoll/pounce task's replaced snapshots without deleting inputs."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path('D:/FPS3D/FPSGAME').resolve()
DEST = (ROOT / 'trash/monster-ragdoll-retired-20261003').resolve()
PACKS = [
    'MonsterGunHitFeedback20261002', 'MonsterRagdollStandard20261003',
    'MonsterRagdollPerformance20261003', 'WitchCorpseGround20261002',
    'WitchCorpseFollow20261002', 'WitchCorpseContact20261002',
    'WitchGetUpRobe20261002', 'WitchGroundContact20261002',
    'WitchStaffDrop20261002', 'WitchPhysicalSettle20261003',
    'WitchLegRestore20261003',
]
items = []
for name in PACKS:
    folder = ROOT / 'SourceAssets' / name
    for child in folder.iterdir():
        if child.is_dir() and child.name.lower() == 'before':
            items.append((child, 'Replaced pre-edit source/asset snapshot',
                          'Current Source/FPSGAME and retained production authoring recipes'))

mutant = ROOT / 'SourceAssets/Mutant3Khaimera20260923'
items.append((mutant / 'pounce_palm_down_20261002',
              'User rejected the first palm direction; no retained recipe reads this folder',
              'V2 author input -> V3 flight -> V4 landing -> V5 windup'))
for name in ['pounce_takeoff_hands_v2_20261002', 'pounce_forward_flip_v3_20261002',
             'pounce_landing_wrist_v4_20261002', 'pounce_open_windup_v5_20261002']:
    folder = mutant / name
    if (folder / 'before_content').is_dir():
        items.append((folder / 'before_content', 'Replaced animation package backup',
                      'Retained author Blend/FBX inputs and current installed animation packages'))
    for child in folder.glob('*.blend1'):
        items.append((child, 'Blender automatic backup superseded by saved .blend',
                      str(child.with_suffix('.blend').relative_to(ROOT))))
for name in ['install_takeoff_hands.py', 'resume_owned_tracks.py', 'end_pie_for_save.py']:
    items.append((mutant / 'pounce_takeoff_hands_v2_20261002' / name,
                  'Retired V2 installation/one-time save helper restores rejected palm direction',
                  'Keep V2 author source for V3; install V3 then V4/V5'))
empty_log = ROOT / 'SourceAssets/MonsterRagdollCore20261002/build-console.log'
if empty_log.exists() and empty_log.stat().st_size == 0:
    items.append((empty_log, 'Empty failed launch output, not a build receipt',
                  'Retained successful build.json and Completion20261002/completion.json'))

def contained(path, parent):
    path.relative_to(parent)
    return path

manifest = []
for source, reason, replacement in items:
    source = contained(source.resolve(), ROOT / 'SourceAssets')
    target = contained((DEST / source.relative_to(ROOT)).resolve(), DEST)
    if target.exists():
        raise RuntimeError(f'Archive target already exists: {target}')
    if not source.exists():
        raise RuntimeError(f'Missing explicitly selected source: {source}')
    files = sorted(source.rglob('*')) if source.is_dir() else [source]
    for file in files:
        if not file.is_file():
            continue
        relative = file.relative_to(source) if source.is_dir() else Path('.')
        final = target / relative if source.is_dir() else target
        manifest.append(dict(original=str(file.relative_to(ROOT)).replace('\\', '/'),
                             archived=str(final.relative_to(ROOT)).replace('\\', '/'),
                             bytes=file.stat().st_size,
                             sha256=hashlib.sha256(file.read_bytes()).hexdigest(),
                             reason=reason, retained_replacement=replacement))

DEST.mkdir(parents=True, exist_ok=True)
(DEST / 'archive-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
for source, _, _ in items:
    target = DEST / source.relative_to(ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(target))
for entry in manifest:
    target = ROOT / entry['archived']
    if target.stat().st_size != entry['bytes'] or hashlib.sha256(target.read_bytes()).hexdigest() != entry['sha256']:
        raise RuntimeError(f'Archive read-back mismatch: {target}')

record = ROOT / 'SourceAssets/MonsterRagdollPublication20261003/archive-manifest.json'
record.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
(DEST / 'README.md').write_text(
    '# 怪物布娃娃与飞扑废案归档\n\n'
    '2026-10-03 按用户要求归档。原路径、字节数、SHA-256、原因和替代物见 archive-manifest.json；移动后逐文件读回一致。\n\n'
    '保留 V2 制作源供 V3 读取、V3 空中源供 V4、V4 源供 V5；有效输入、正式 Content、来源许可与成功构建记录没有退役。\n'
    '旧文中的 Before / before_content 指向当时位置；恢复历史快照应查此清单，当前制作不读取 trash。\n', encoding='utf-8')
print(json.dumps(dict(files=len(manifest), bytes=sum(e['bytes'] for e in manifest),
                      archive=str(DEST), manifest=str(record)), ensure_ascii=False))
