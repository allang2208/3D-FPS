"""Drop retired 201 clips from ArmHinge55 and put their packages back to the pre-ArmHinge55 bytes.

Retired (no runtime path loads them; reload/reload_empty resolve to Magazine24, the metal belt
box is retired): BeltFeed08 A_LMG201_reload(_empty) / reload_belt(_empty) and the same four in
each Accessories22 grip family.  Run only while no UE process is open."""
import json, hashlib, shutil
from pathlib import Path
HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
idx = json.loads((HERE / 'inputs.json').read_text())
rec = json.loads((HERE / 'delivery.json').read_text())
retired = [k for k in idx['201']['clips'] if ('/BeltFeed08/' in k or '/Accessories22/' in k)
           and k.rsplit('_', 1)[-1] in ('reload', 'empty', 'belt') and ('_reload' in k.split('/')[-1])]
disk = lambda k: PROJECT / 'Content' / (k.removeprefix('/Game/') + '.uasset')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
keep = HERE / 'Retired_ArmHinge55_v1'
out = {}
for k in sorted(retired):
    cur = disk(k)
    if sha(cur) != rec['saved'][k]['sha256']:
        raise RuntimeError('Changed since ArmHinge55: ' + k)
    back = HERE / 'Before' / cur.relative_to(PROJECT / 'Content')
    assert sha(back) == idx['201']['clips'][k]['sha256'], k
    dst = keep / cur.relative_to(PROJECT / 'Content')
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(cur, dst)            # the v1 result, in case it is wanted later
    shutil.copy2(back, cur)           # original bytes back in place
    out[k] = {'restored_sha256': sha(cur), 'armhinge55_v1_copy': str(dst)}
    print('RESTORED', k.split('/Weapons/')[1])
for k in retired:
    idx['201']['clips'].pop(k)
    rec['saved'].pop(k, None)
idx['excluded_retired'] = sorted(retired)
(HERE / 'inputs.json').write_text(json.dumps(idx, indent=2))
(HERE / 'delivery.json').write_text(json.dumps(rec, indent=1))
(HERE / 'retired_restore.json').write_text(json.dumps(out, indent=1))
print('EXCLUDED', len(retired), 'remaining', {g: len(v['clips']) for g, v in idx.items() if isinstance(v, dict) and 'clips' in v})
