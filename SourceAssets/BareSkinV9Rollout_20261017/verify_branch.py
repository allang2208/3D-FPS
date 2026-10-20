"""Read-only commandlet: every clip with a forearm twist write, every key (data model): twist_01 / twist_02 against
100 % / 50 % of the hand's centred-branch roll. Output Work/verify_branch.json."""
import json, sys, math
from pathlib import Path
sys.path.insert(0, 'D:/FPS3D/FPSGAME/SourceAssets/BareSkinV9Rollout_20261017')
import unreal as u

R = Path('D:/FPS3D/FPSGAME/SourceAssets/BareSkinV9Rollout_20261017')
src = (R / 'anim_twist_branch.py').read_text(encoding='utf-8')
ns = {}
exec(src[src.index('def qt('):src.index('rec_by_path = {}')], {'math': math, 'FOLD': 210.0}, ns)   # helpers only
qt, qmul, qinv, twist, wrap, branch = (ns[k] for k in ('qt', 'qmul', 'qinv', 'twist', 'wrap', 'branch'))
specs = {}
for b in ('batch1', 'batch2', 'batch3', 'batch4'):
    sf = R / 'Work' / b / 'twist_specs.json'
    if sf.exists():
        for path, s in json.loads(sf.read_text()).items(): specs.setdefault(path, s)
recs = [json.loads(f.read_text()) for f in (R / 'InstalledRaw').glob('*.json') if not f.stem.endswith('.failed')]
out = []; meshes = {}
for rr in sorted(recs, key=lambda d: d['path']):
    if not rr.get('twist'): continue
    path = rr['path']; spec = specs[path]; vm = spec['mesh']
    seq = u.load_asset(path + '.' + path.split('/')[-1]); meshes.setdefault(vm, u.load_asset(vm + '.' + vm.split('/')[-1]))
    n = seq.get_editor_property('data_model_interface').get_number_of_keys()
    sides = [s for s in spec['sides'] if 'lowerarm_twist_02_' + s in rr['twist']]
    names = [x for s in sides for x in ('hand_' + s, 'lowerarm_twist_01_' + s, 'lowerarm_twist_02_' + s)]
    locs = [dict(zip(names, u.AnimationLibrary.get_bone_poses_for_frame(seq, names, k, False, meshes[vm]))) for k in range(n)]
    row = dict(path=path, keys=n, sides={})
    for s in sides:
        sd = spec['sides'][s]; axis = sd['axis_l']
        r = branch([twist(qmul(qt(l['hand_' + s].rotation), qinv(tuple(sd['rel_hand']))), axis) for l in locs])
        r1 = [twist(qmul(qt(l['lowerarm_twist_01_' + s].rotation), qinv(tuple(sd['rel_t1']))), axis) for l in locs]
        r2 = [twist(qmul(qt(l['lowerarm_twist_02_' + s].rotation), qinv(tuple(sd['rel_t2']))), axis) for l in locs]
        row['sides'][s] = dict(err1=round(max(abs(wrap(a - b)) for a, b in zip(r1, r)), 2), err2=round(max(abs(wrap(a - .5 * b)) for a, b in zip(r2, r)), 2),
                               max_twist02=round(max(abs(x) for x in r2), 1))
    out.append(row)
(R / 'Work/verify_branch.json').write_text(json.dumps(out, indent=1))
bad = [r for r in out if any(v['err1'] > 3 or v['err2'] > 3 for v in r['sides'].values())]
print('V9R_VERIFY_BRANCH', len(out), 'bad', len(bad), flush=True)
