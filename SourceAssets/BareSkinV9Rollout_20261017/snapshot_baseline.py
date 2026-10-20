"""Copy the user-approved V9 bare-hand state (10-19) out of the project: the 111 meshes, every animation this rollout
rewrote, the V9 skin materials / textures. Target D:/FPS3D/FPSGAME_Backups/BareSkinV9Baseline20261019 (outside the
repository, after the 10-19 loss of the in-repo Before/ copies). Writes manifest.json with sha256 per file.
Run with no UE process writing these assets."""
import hashlib, json, shutil, glob, os
from pathlib import Path
P = Path('D:/FPS3D/FPSGAME'); R = P / 'SourceAssets/BareSkinV9Rollout_20261017'
OUT = Path('D:/FPS3D/FPSGAME_Backups/BareSkinV9Baseline20261019')


def rd(f):
    try: return json.loads(Path(f).read_text())
    except Exception: return None


paths = {r['path'] for f in glob.glob(str(R / 'Installed/*.json')) if Path(f).stem.count('.') == 0 for r in [rd(f)] if r}
for d in ('InstalledRaw', 'InstalledBranch', 'InstalledArm', 'InstalledArm2', 'InstalledArm3'):
    for f in glob.glob(str(R / d / '*.json')):
        r = None if f.endswith('.failed.json') else rd(f)
        if r and r.get('sha256'): paths.add(r['path'])
files = [P / 'Content' / (p.removeprefix('/Game/') + '.uasset') for p in sorted(paths)]
for folder in ('Characters/ModularOutfit20260924/BareSkinV9', 'Characters/ModularOutfit20260924/BareSkinV9M4'):
    files += sorted((P / 'Content' / folder).rglob('*.uasset'))
manifest = []
for f in files:
    if not f.exists(): manifest.append(dict(file=str(f), missing=True)); continue
    dst = OUT / f.relative_to(P); dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(f, dst)
    manifest.append(dict(file=str(f.relative_to(P)).replace(os.sep, '/'), bytes=f.stat().st_size, sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
(OUT / 'manifest.json').write_text(json.dumps(dict(note='User-approved V9 bare hands, 2026-10-19 (after R3c). Restore = copy Content/ back with UE closed.',
                                                   files=manifest), indent=1))
print('copied', sum(1 for m in manifest if not m.get('missing')), 'missing', sum(1 for m in manifest if m.get('missing')),
      'GB %.2f' % (sum(m.get('bytes', 0) for m in manifest) / 2 ** 30))
