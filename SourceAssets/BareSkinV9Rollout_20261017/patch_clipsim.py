"""Offline stand-in for the UE re-read of the R3d rewrite: apply the written arm rows (Work/ArmPlan4: local rotations
of upperarm, lowerarm, hand, lowerarm_twist_01/02 per key) to the 15 fps component frames in ClipsSim2. Joint
positions do not move (every change is a turn about the bone's own axis). The later UE re-read overwrites these
frames with the asset's own data."""
import json, glob
import numpy as np
from scipy.spatial.transform import Rotation as Rot
from rollout import R

plans = [json.loads(open(f).read()) for f in glob.glob(str(R / 'Work/ArmPlan4/*.json'))]
by_path = {p['path']: p for p in plans}
n_files = n_clips = 0
for f in sorted((R / 'ClipsSim2').glob('*.json')):
    d = json.loads(f.read_text()); bi = {b: i for i, b in enumerate(d['bones'])}; touched = False
    for path, c in d['clips'].items():
        pl = by_path.get(path)
        if not pl or 'frames' not in c: continue
        for s, rows in pl['sides'].items():
            need = ['clavicle_' + s, 'upperarm_' + s, 'lowerarm_' + s, 'hand_' + s, 'lowerarm_twist_01_' + s, 'lowerarm_twist_02_' + s]
            if any(b not in bi for b in need): continue
            nk = len(rows['upperarm_' + s])
            for i, fr in enumerate(c['frames']):
                k = min(nk - 1, int(round(i / c['fps'] * c['rate'])))
                Cq = Rot.from_quat(fr[bi['clavicle_' + s]][3:])
                U = Cq * Rot.from_quat(rows['upperarm_' + s][k]); L = U * Rot.from_quat(rows['lowerarm_' + s][k])
                for b, q in (('upperarm', U), ('lowerarm', L), ('hand', L * Rot.from_quat(rows['hand_' + s][k])),
                             ('lowerarm_twist_01', L * Rot.from_quat(rows['lowerarm_twist_01_' + s][k])),
                             ('lowerarm_twist_02', L * Rot.from_quat(rows['lowerarm_twist_02_' + s][k]))):
                    fr[bi[b + '_' + s]][3:] = [float(x) for x in q.as_quat()]
        touched = True; n_clips += 1
    if touched: f.write_text(json.dumps(d, separators=(',', ':'))); n_files += 1
print('patched clips', n_clips, 'in files', n_files)
