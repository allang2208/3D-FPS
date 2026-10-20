"""Restore every animation this rollout rewrote to its pre-rollout original (Before/), so twist and bad-key
repairs can be redone with the reliable data-model reader. Only files still in one of this rollout's own
saved states are restored; anything changed by someone else since is left and listed. UE must be closed."""
import json, glob, hashlib, os, shutil
from pathlib import Path

R = Path('D:/FPS3D/FPSGAME/SourceAssets/BareSkinV9Rollout_20261017'); P = Path('D:/FPS3D/FPSGAME')
mine = {}
for d in ('InstalledAnims', 'InstalledGlitch', 'InstalledGlitch2', 'InstalledGlitch3', 'InstalledGlitch_raw', 'InstalledGlitch2_loose'):
    for f in glob.glob(str(R / d / '*')):
        if f.endswith('.failed.json'): continue
        try: r = json.loads(Path(f).read_text())
        except Exception: continue
        if not r.get('path'): continue
        s = mine.setdefault(r['path'], set())
        for k in ('sha256', 'sha_before'):
            if r.get(k): s.add(r[k])
restored, skipped, untouched = [], [], 0
for path, shas in sorted(mine.items()):
    rel = path.removeprefix('/Game/') + '.uasset'; cur = P / 'Content' / rel; bak = R / 'Before' / 'Content' / rel
    if not bak.exists(): untouched += 1; continue
    h = hashlib.sha256(cur.read_bytes()).hexdigest()
    if h == hashlib.sha256(bak.read_bytes()).hexdigest(): untouched += 1; continue
    if h not in shas: skipped.append(path); continue
    shutil.copy2(bak, cur); restored.append(path)
park = R / ('Receipts_pre_reader_' + str(len(list(R.glob('Receipts_pre_reader_*'))))); park.mkdir()
for d in ('InstalledAnims', 'InstalledGlitch', 'InstalledGlitch2', 'InstalledGlitch3'):
    if (R / d).exists(): shutil.move(str(R / d), str(park / d))
(R / 'Work/restore_anims.json').write_text(json.dumps(dict(restored=restored, skipped=skipped), indent=1))
print('restored', len(restored), 'already original', untouched, 'skipped (changed by others)', len(skipped)); print(skipped[:10])
