"""Offline: clips (and sides) the arm axial fix would change, from ClipsTrue (15 fps), plus every clip whose twist
branch was rewritten. -> Work/armfix_jobs.json {path: {vm, pose_source, sides: {s: spec side}}}"""
import json
import numpy as np
from scipy.spatial.transform import Rotation as Rot
from rollout import R, load_snapshot
import armfix

specs = {}
for b in ('batch1', 'batch2', 'batch3', 'batch4'):
    for k, v in json.loads((R / 'Work' / b / 'twist_specs.json').read_text()).items(): specs.setdefault(k, v)
branch = {json.loads(f.read_text())['path'] for f in (R / 'InstalledBranch').glob('*.json') if not f.stem.endswith('.failed') and json.loads(f.read_text()).get('rewritten')}
jobs = {}; seen = set()
for b in ('batch1', 'batch2', 'batch3', 'batch4'):
    plan = json.loads((R / (b + '.json')).read_text())
    for ps, vm in plan['viewmodels'].items():
        f = R / 'ClipsTrue' / (ps + '.json')
        if not f.exists(): continue
        ref = load_snapshot(vm)['bones']; cd = json.loads(f.read_text()); bi = {x: i for i, x in enumerate(cd['bones'])}
        for path, c in cd['clips'].items():
            if 'frames' not in c or path in seen: continue
            seen.add(path)
            for s in 'lr':
                if 'hand_' + s not in bi: continue
                sp = specs.get(path) if specs.get(path, {}).get('sides', {}).get(s) else next((v for v in specs.values() if v['pose_source'] == ps and s in v['sides']), None)
                if not sp: continue
                sd = sp['sides'][s]
                keys = [dict(S=np.array(fr[bi['upperarm_' + s]][:3]), E=np.array(fr[bi['lowerarm_' + s]][:3]), W=np.array(fr[bi['hand_' + s]][:3]),
                             U=Rot.from_quat(fr[bi['upperarm_' + s]][3:]), L=Rot.from_quat(fr[bi['lowerarm_' + s]][3:]), H=Rot.from_quat(fr[bi['hand_' + s]][3:]))
                        for fr in c['frames']]
                pl = armfix.plan(keys, ref, s, sd, 15.0)
                if pl['changed'] or path in branch:
                    j = jobs.setdefault(path, dict(vm=vm, pose_source=ps, sides={}))
                    j['sides'][s] = sd
(R / 'Work/armfix_jobs.json').write_text(json.dumps(jobs))
print('clips', len(jobs), 'sides', sum(len(j['sides']) for j in jobs.values()))
