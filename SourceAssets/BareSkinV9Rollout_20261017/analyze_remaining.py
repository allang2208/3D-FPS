"""Offline: the sides still beyond 180 after the forearm unspin - per 15 fps frame: hand roll after unspin, elbow
bend, elbow distance from the shoulder-wrist line (how far a whole-arm swivel would move the elbow)."""
import sys, json, math
import numpy as np
from scipy.spatial.transform import Rotation as Rot
from rollout import R, load_snapshot
from unspin import twist, unwrap, centre, best_beta, smooth, elbow_twist

want = sys.argv[1:] or ['A_M4_Foregrip_drum_reload_empty', 'A_QBZ191_QuickCombat_Vertical', 'A_M1911_inspect', 'A_DW715_inspect', 'A_Warhammer_Uppercut', 'A_Warhammer_QuickCombat']
seen = set()
for b in ('batch1', 'batch2', 'batch3', 'batch4'):
    plan = json.loads((R / (b + '.json')).read_text()); specs = json.loads((R / 'Work' / b / 'twist_specs.json').read_text())
    for ps, vm in plan['viewmodels'].items():
        f = R / 'ClipsTrue' / (ps + '.json')
        if not f.exists(): continue
        ref = load_snapshot(vm)['bones']; cd = json.loads(f.read_text()); bi = {x: i for i, x in enumerate(cd['bones'])}
        for path, c in cd['clips'].items():
            sp = specs.get(path)
            if not sp or sp['pose_source'] != ps or 'frames' not in c or path in seen or not any(path.endswith(w) for w in want): continue
            seen.add(path)
            for s, sd in sp['sides'].items():
                U0 = Rot.from_quat(ref['upperarm_' + s]['q']); L0 = Rot.from_quat(ref['lowerarm_' + s]['q'])
                P, E, rows = [], [], []
                for fr in c['frames']:
                    q = lambda n: Rot.from_quat(fr[bi[n + '_' + s]][3:]); g = lambda n: np.asarray(fr[bi[n + '_' + s]][:3])
                    P.append(twist((q('lowerarm').inv() * q('hand') * Rot.from_quat(sd['rel_hand']).inv()).as_quat(), sd['axis_l']))
                    E.append(elbow_twist(q('upperarm'), q('lowerarm'), U0, L0, sd['axis_l']))
                    S_, E_, W_ = g('upperarm'), g('lowerarm'), g('hand'); ax = (W_ - S_) / np.linalg.norm(W_ - S_)
                    rr = np.linalg.norm((E_ - S_) - ((E_ - S_) @ ax) * ax)
                    bend = math.degrees(math.acos(np.clip((E_ - S_) @ (W_ - E_) / np.linalg.norm(E_ - S_) / np.linalg.norm(W_ - E_), -1, 1)))
                    rows.append((bend, rr))
                P = centre(unwrap(P)); E = centre(unwrap(E))
                beta = smooth([best_beta(p, e) for p, e in zip(P, E)], 15.0); P2 = [p - x for p, x in zip(P, beta)]
                if max(map(abs, P2)) < 180: continue
                print('%s %s  (fps 15, keys %d)' % (path.split('/')[-1], s, len(P2)))
                print('   ' + ' '.join('%d/%d/%.0f' % (p, r[0], r[1]) for p, r in zip(P2, rows)))
