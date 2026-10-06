import sys, json
from pathlib import Path
O = Path(__file__).parent
sys.path.insert(0, str(O))
from grip_scene import *
side = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'single'
rig, data, profile, meta = load(side)
after='after' in sys.argv
if after:profile=json.loads((O/'Single/profile.json').read_text())
tree = grip_trees()[0][1]
out = {}
for hand in (('r',) if after else ('r', 'l') if side == 'single' else (side,)):
    skin = Skin(rig, hand)
    entries = []
    for kind in ('idle', 'aim', 'inspect'):
        if kind not in data['clips']: continue
        samples = data['clips'][kind]['samples']
        chosen = [samples[0]] if kind != 'inspect' else samples[::max(1,len(samples)//16)] + [samples[-1]]
        for sample in chosen:
            p = pose(rig, data, profile, kind, sample)
            r, _, _ = report(skin, p, meta, tree)
            entries.append(dict(kind=kind, t=sample['time'], contact=r, hand=packed(canonical_pose(p,meta) @ p['hand_' + hand])))
    out[hand] = entries
    print('DIAGNOSE',side,hand,'skin vertices',len(skin.coords),flush=True)
    for e in entries:
        print(e['kind'],round(e['t'],3),{k:(v['inside_half_mm'],round(v['deepest_mm'],2)) for k,v in e['contact'].items()},flush=True)
(O / ('diagnosis_' + side + ('_after' if after else '') + '.json')).write_text(json.dumps(out,indent=2))
