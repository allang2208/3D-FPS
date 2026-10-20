"""Move this task's material-probe copies out of Content/__V9Probe back to the backup folders they were copied
from (the Before/ copies were deleted externally on 10-19 12:06; these are the only remaining copies of those
versions). Run with no UE process open. Writes Work/restored_probe_copies.json."""
import hashlib, json, shutil
from pathlib import Path
P = Path('D:/FPS3D/FPSGAME'); R = P / 'SourceAssets/BareSkinV9Rollout_20261017'; TMP = P / 'Content/__V9Probe'
paths = json.loads((R / 'Work/v8_only_paths.json').read_text())
paths.append('/Game/Weapons/PitViper2011/Integrated20261002/Single/SK_PitViper2011_Manny')
by_key = {hashlib.sha256(p.encode()).hexdigest()[:12]: (p, P / 'SourceAssets/BareHandAudit20261016/Before/Content') for p in paths}
for f in (R / 'Installed').glob('*.json'):                 # rollout keys (probe of the 10-14 Pit Viper used these)
    if f.stem.count('.') == 0:
        p = json.loads(f.read_text())['path']; by_key.setdefault(f.stem, (p, P / 'SourceAssets/BareHandAudit20261016/Before/Content'))
moved = []
if TMP.exists():
    for d in sorted(x for x in TMP.iterdir() if x.is_dir()):
        for f in d.glob('*.uasset'):
            hit = by_key.get(d.name)
            if not hit or not hit[0].endswith('/' + f.stem): continue
            dst = hit[1] / (hit[0].removeprefix('/Game/') + '.uasset')
            if dst.exists(): continue
            dst.parent.mkdir(parents=True, exist_ok=True); shutil.move(str(f), str(dst)); moved.append(dict(path=hit[0], to=str(dst)))
    left = [str(x) for x in TMP.rglob('*') if x.is_file()]
    if not left: shutil.rmtree(TMP)
else:
    left = []
(R / 'Work/restored_probe_copies.json').write_text(json.dumps(dict(moved=moved, left_in_content=left), indent=1))
print('moved', len(moved), 'left', len(left))
