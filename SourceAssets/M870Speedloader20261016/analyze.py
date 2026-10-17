"""Read-only analysis of the inputs: rig parity, animated bones, loader geometry."""
import json
from pathlib import Path
import numpy as np
from rig import fk, row2m, inv

O = Path(__file__).parent
D = json.loads((O / 'inputs.json').read_text())
s90, m870, props = D['super90'], D['m870'], D['props']
print('super90 bones', len(s90['names']), 'm870 bones', len(m870['names']), 'props bones', len(props['names']))
only_s = [n for n in s90['names'] if n not in m870['names']]; only_m = [n for n in m870['names'] if n not in s90['names']]
print('only super90:', only_s); print('only m870:', only_m)
diff = []
for n in s90['names']:
    if n in m870['names']:
        a, b = np.array(s90['ref_local'][n]), np.array(m870['ref_local'][n])
        dt = np.linalg.norm(a[:3] - b[:3]); dq = 1 - abs(np.dot(a[3:7], b[3:7]))
        if dt > .01 or dq > 1e-6: diff.append((n, round(float(dt), 3), round(float(dq), 6)))
print('ref local differences (bone, dt cm, 1-|dot q|):', diff[:60])
print('parents differ:', [n for n in s90['names'] if n in m870['names'] and s90['parents'][n] != m870['parents'][n]])
print('props names:', props['names'])
G = json.loads((O / 'geometry.json').read_text())
pg = G['props']; dom = pg['dominant']
from collections import Counter
print('props vertices by bone', Counter(dom))
for bone in ('WPN_Shell', 'WPN_SOCKET_Magazine'):
    v = np.array([p for p, d in zip(pg['positions'], dom) if d == bone])
    if len(v):
        ref = row2m(props['ref_world'][bone]); loc = (inv(ref) @ np.c_[v, np.ones(len(v))].T).T[:, :3]
        print(bone, 'props ref world t', np.round(props['ref_world'][bone][:3], 2), 'local bbox min', loc.min(0).round(2), 'max', loc.max(0).round(2))
# Animated bones in Super90 loader normal_7 relative to its first frame
clip = D['super90_clips']['normal_7']['rows']
names = s90['names']
moving = []
for n in names:
    arr = np.array([r[n] for r in clip])
    span = np.ptp(arr[:, :3], axis=0).max()
    rot = max(1 - abs(np.dot(arr[0, 3:7], a)) for a in arr[:, 3:7])
    if span > .05 or rot > 1e-5: moving.append(n)
print('animated in super90 normal_7:', [n for n in moving if not any(k in n for k in ('thumb', 'index', 'middle', 'ring', 'pinky'))])
for role in ('idle', 'cycle', 'reload_full'):
    clip = D['m870_clips'][role]['rows']
    mv = [n for n in m870['names'] if np.ptp(np.array([r[n][:3] for r in clip]), axis=0).max() > .05]
    print('m870', role, 'frames', len(clip), 'moving (non-finger):', [n for n in mv if not any(k in n for k in ('thumb', 'index', 'middle', 'ring', 'pinky'))][:40])
