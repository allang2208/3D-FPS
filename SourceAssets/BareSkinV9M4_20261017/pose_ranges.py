"""Joint-angle ranges of the M4 clips (from Snapshot/m4_read.json), relative to the reference pose.

Elbow: flexion beyond rest about the elbow hinge. Wrist: hand vs lowerarm relative rotation split into
flexion (about the radio-ulnar axis), deviation (about the palm normal) and twist (about the forearm),
plus how much of the hand twist the two lowerarm twist bones carry. Writes Work/pose_ranges.json.
"""
import json
import numpy as np
from scipy.spatial.transform import Rotation as Rot
from m4data import R

d = json.loads((R / 'Snapshot/m4_read.json').read_text()); names = d['bones']; ix = {n: i for i, n in enumerate(names)}
ref = d['ref_component']


def pose_arrays(frame):
    t = np.array([b['t'] for b in frame]); q = Rot.from_quat([b['q'] for b in frame]); return t, q


ref_t = np.array([ref[n]['t'] for n in names]); ref_q = Rot.from_quat([ref[n]['q'] for n in names])


def joint_frame(t, q, side):
    up = t[ix['lowerarm_' + side]] - t[ix['upperarm_' + side]]; fd = t[ix['hand_' + side]] - t[ix['lowerarm_' + side]]
    return up / np.linalg.norm(up), fd / np.linalg.norm(fd)


def angles(t, q, side):
    up, fd = joint_frame(t, q, side)
    elbow = np.degrees(np.arccos(np.clip(up @ fd, -1, 1)))
    rel = q[ix['lowerarm_' + side]].inv() * q[ix['hand_' + side]]
    rel0 = ref_q[ix['lowerarm_' + side]].inv() * ref_q[ix['hand_' + side]]
    delta = rel * rel0.inv()                              # in lowerarm-local space
    # local axes of the forearm, radial and palm in lowerarm space (from the reference pose)
    la = ref_q[ix['lowerarm_' + side]]
    fwd = la.inv().apply(ref_t[ix['hand_' + side]] - ref_t[ix['lowerarm_' + side]]); fwd /= np.linalg.norm(fwd)
    rad = la.inv().apply(ref_t[ix['index_metacarpal_' + side]] - ref_t[ix['pinky_metacarpal_' + side]]); rad -= (rad @ fwd) * fwd; rad /= np.linalg.norm(rad)
    palm = np.cross(fwd, rad)
    rv = delta.as_rotvec()
    twist_h = np.degrees(rv @ fwd); flex = np.degrees(rv @ rad); dev = np.degrees(rv @ palm)
    out = dict(elbow=elbow, wrist_flex=flex, wrist_dev=dev, hand_twist=twist_h)
    for b in ('lowerarm_twist_01_', 'lowerarm_twist_02_'):
        r = (q[ix['lowerarm_' + side]].inv() * q[ix[b + side]]) * (ref_q[ix['lowerarm_' + side]].inv() * ref_q[ix[b + side]]).inv()
        out[b + 'twist'] = np.degrees(r.as_rotvec() @ fwd)
    return out


ref_angles = {s: angles(ref_t, ref_q, s) for s in ('l', 'r')}
rows = {}
for clip, c in d['clips'].items():
    if c.get('missing'): continue
    per = {s: [] for s in ('l', 'r')}
    for frame in c['frames']:
        t, q = pose_arrays(frame)
        for s in ('l', 'r'): per[s].append(angles(t, q, s))
    rows[clip.split('/')[-1]] = {s: {k: [round(float(min(f[k] for f in v)), 1), round(float(max(f[k] for f in v)), 1)] for k in v[0]} for s, v in per.items()}
summary = {}
for s in ('l', 'r'):
    summary[s] = {k: [min(r[s][k][0] for r in rows.values()), max(r[s][k][1] for r in rows.values())] for k in next(iter(rows.values()))[s]}
out = dict(reference=ref_angles, clips=rows, summary=summary)
(R / 'Work/pose_ranges.json').write_text(json.dumps(out, indent=1, default=float))
print(json.dumps(dict(reference=ref_angles, summary=summary), indent=1, default=float))
for k, v in rows.items(): print(k, 'L', v['l'], '\n   R', v['r'])
