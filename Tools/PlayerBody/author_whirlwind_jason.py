"""Author Jason whirlwind phases from CC0 full-body donors, without rendering.

Source globals are converted into actor space before retiming. Leg lengths and
all neck/arm translations stay at Jason's reference dimensions. A periodic
two-step pivot supplies heel roll, swing clearance and knee/foot alignment.
"""
import json
import math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'SourceAssets/ThirdPersonWhirlwind20261006'
d = json.loads((OUT/'authoring-input.json').read_text())
names = d['names']
parents = d['parents']
ix = {n: i for i, n in enumerate(names)}
ref = np.array(d['reference'])
root, pelvis = ix['root'], ix['pelvis']

def unit(v):
    return v/max(np.linalg.norm(v), 1e-12)

def mul(a, b):
    return np.r_[a[3]*b[:3]+b[3]*a[:3]+np.cross(a[:3], b[:3]), a[3]*b[3]-np.dot(a[:3], b[:3])]

def inv(q):
    return np.r_[-q[:3], q[3]]

def rot(q, v):
    return v+2*np.cross(q[:3], np.cross(q[:3], v)+q[3]*v)

def axis(axis, degrees):
    h = math.radians(degrees)*.5
    return np.r_[unit(np.array(axis))*math.sin(h), math.cos(h)]

def between(a, b):
    a, b = unit(a), unit(b)
    return unit(np.r_[np.cross(a, b), 1+np.dot(a, b)])

def smooth(t):
    t = float(np.clip(t, 0, 1))
    return t*t*t*(t*(6*t-15)+10)

def mix(a, b, t):
    f = a*(1-t)+b*t
    q = b[:, 3:7].copy()
    q[np.sum(a[:, 3:7]*q, axis=1)<0] *= -1
    f[:, 3:7] = a[:, 3:7]*(1-t)+q*t
    f[:, 3:7] /= np.linalg.norm(f[:, 3:7], axis=1)[:, None]
    return f

def fk(f):
    w = f.copy()
    for i, p in enumerate(parents):
        if p < 0:
            continue
        w[i, :3] = w[p, :3]+rot(w[p, 3:7], f[i, :3]*w[p, 7:])
        w[i, 3:7] = mul(w[p, 3:7], f[i, 3:7])
        w[i, 7:] = w[p, 7:]*f[i, 7:]
    return w

def world_rotation(f, w, b, q):
    p = parents[b]
    f[b, 3:7] = unit(mul(inv(w[p, 3:7]), q) if p >= 0 else q)

bind = fk(ref)

def actor_space(kind):
    data = d[kind]
    result = []
    initial = np.array(data['donor_roots'][0][3:7])
    for frame, donor in zip(data['frames'], data['donor_roots']):
        f = np.array(frame)
        # The retargeter places global heading on the pelvis, leaving root
        # identity. Remove the donor ROOT heading, never the pelvis's own coil.
        delta = mul(np.array(donor[3:7]), inv(initial))
        heading = Rotation.from_quat(delta).as_euler('xyz')[2]
        undo = axis([0, 0, 1], -math.degrees(heading))
        w = fk(f)
        hip_q, hip_t = mul(undo, w[pelvis, 3:7]), rot(undo, w[pelvis, :3])
        f[:, :3] = ref[:, :3]
        f[:, 7:] = ref[:, 7:]
        f[root] = ref[root]
        f[pelvis, :3] = hip_t
        f[pelvis, 3:7] = hip_q
        result.append(f)
    return np.array(result)

sources = {k: actor_space(k) for k in ('spin', 'loop')}

def source(kind, t):
    frames = sources[kind]
    x = np.clip(t/d[kind]['duration'], 0, 1)*(len(frames)-1)
    a = min(int(x), len(frames)-2)
    return mix(frames[a], frames[a+1], x-a)

def foot_cycle(phase, side):
    # Opposite half-cycles: one forefoot carries the turn while the other
    # travels outside the supporting leg. The 5 cm inside clearance prevents
    # the two shoes crossing at weight transfer. Heel roll permits toe swivel.
    p = (phase+.25-(.5 if side > 0 else 0)) % 1
    if p < .5:
        angle = 2*math.pi*(p-.25)
        toe = np.array([side*math.sqrt(25+144*math.cos(angle)**2), side*12*math.sin(angle), 1.22])
        roll = 9+9*math.sin(2*math.pi*p)**2
    else:
        u = (p-.5)*2
        lift = math.sin(math.pi*u)**2
        toe = np.array([side*(5+18*lift), side*12*(1-2*smooth(u)), 1.22+8*lift])
        roll = 9*(1-lift)
    yaw = -side*8
    return toe, yaw, roll

def neutral_foot(side):
    b = ix['ball_'+('l' if side > 0 else 'r')]
    return bind[b, :3].copy(), 0., 0.

def foot_blend(a, b, t):
    return tuple(x*(1-t)+y*t for x, y in zip(a, b))

def solve_leg(f, side, target):
    s = 'l' if side > 0 else 'r'
    h, k, a, toe_b = (ix[n+'_'+s] for n in ('thigh', 'calf', 'foot', 'ball'))
    toe, yaw, roll = target
    yaw_q = axis([0, 0, 1], yaw)
    foot_q = mul(mul(yaw_q, axis([1, 0, 0], -roll)), bind[a, 3:7])
    ankle = toe-rot(foot_q, ref[toe_b, :3])
    w = fk(f)
    hip = w[h, :3]
    l1 = np.linalg.norm(ref[k, :3])
    l2 = np.linalg.norm(ref[a, :3])
    direction = unit(ankle-hip)
    reach = float(np.clip(np.linalg.norm(ankle-hip), abs(l1-l2)+.001, (l1+l2)*.985))
    ankle = hip+reach*direction
    along = (l1*l1-l2*l2+reach*reach)/(2*reach)
    pole = rot(yaw_q, np.array([side*.10, 1., 0.]))
    pole = unit(pole-direction*np.dot(pole, direction))
    knee = hip+direction*along+pole*math.sqrt(max(0, l1*l1-along*along))
    thigh_q = mul(between(rot(yaw_q, bind[k, :3]-bind[h, :3]), knee-hip), mul(yaw_q, bind[h, 3:7]))
    calf_q = mul(between(rot(yaw_q, bind[a, :3]-bind[k, :3]), ankle-knee), mul(yaw_q, bind[k, 3:7]))
    world_rotation(f, w, h, thigh_q)
    w[h, 3:7] = thigh_q
    world_rotation(f, w, k, calf_q)
    w[k, 3:7] = calf_q
    world_rotation(f, w, a, foot_q)
    w[a, 3:7] = foot_q
    # Ball/toe stays level through the support roll instead of stabbing the
    # ground with the whole shoe when the heel rises.
    world_rotation(f, w, toe_b, mul(yaw_q, bind[toe_b, 3:7]))

def legs(f, targets):
    # Helper/corrective bones retain the target rig's rest offsets and inherit
    # the authored thigh/calf rotations; no source-rig stretch is carried over.
    for side in (-1, 1):
        solve_leg(f, side, targets[side])
    return f

def loop_pose(p):
    f = source('loop', p*d['loop']['duration'])
    f[pelvis, :3] = [-2.8*math.cos(2*math.pi*p), 1., 79.2+.65*math.sin(4*math.pi*p)**2]
    return legs(f, {s: foot_cycle(p, s) for s in (-1, 1)})

loop_entry = loop_pose(0.)

def start_pose(p):
    f = source('spin', .60*smooth(p))
    # Counter-load against the gameplay's negative-yaw sweep, then release
    # into the exact loop pose. Whole pelvis rotates with complete torso.
    coil = 28*math.sin(math.pi*p)**2
    f[pelvis, 3:7] = mul(axis([0, 0, 1], coil), f[pelvis, 3:7])
    f = mix(f, loop_entry, smooth((p-.62)/.38))
    f[pelvis, :3] = np.array([0., 1., 81.])*(1-smooth(p))+loop_entry[pelvis, :3]*smooth(p)
    feet = {s: foot_blend(neutral_foot(s), foot_cycle(0., s), smooth((p-.25)/.75)) for s in (-1, 1)}
    return legs(f, feet)

def end_pose(p):
    f = source('spin', 1.4+smooth(p))
    f = mix(loop_entry, f, smooth(p/.38))
    settle = smooth(p)
    f[pelvis, :3] = loop_entry[pelvis, :3]*(1-settle)+np.array([0., 1., 81.])*settle
    f[pelvis, 2] -= 1.1*math.sin(math.pi*p)**2
    feet = {s: foot_blend(foot_cycle(0., s), neutral_foot(s), smooth(p/(.55 if s > 0 else .85))) for s in (-1, 1)}
    return legs(f, feet)

clips = {}
RATE = 30
# Match the project's native animation/compression rate. Clip lengths are
# normalized phase domains: recovery's 16 intervals are retimed to the skill's
# exact .52 seconds. Runtime retimes one loop by integrated angular phase.
for label, duration, fn in [('Start', .5, start_pose), ('Loop', 1., loop_pose), ('End', .52, end_pose)]:
    frame_count = round(duration*RATE)
    frames = [fn(i/frame_count) for i in range(frame_count+1)]
    if label == 'Start':
        frames[-1] = loop_entry.copy()
    elif label == 'Loop':
        frames[-1] = frames[0].copy()
    else:
        frames[0] = loop_entry.copy()
    # Continuous quaternion signs improve compression and preserve the short
    # interpolation arc at the loop seam.
    frames = np.array(frames)
    for i in range(1, len(frames)):
        flip = np.sum(frames[i-1, :, 3:7]*frames[i, :, 3:7], axis=1)<0
        frames[i, flip, 3:7] *= -1
    clips[label] = dict(rate=RATE, frames=frames.tolist())

out = dict(mesh=d['mesh'], skeleton=d['skeleton'], names=names, clips=clips,
           provenance='KayKit Character Animations 1.1 CC0; Jason retarget with authored lower body and phase transitions',
           source_url='https://kaylousberg.itch.io/kaykit-character-animations')
(OUT/'authored-phases.json').write_text(json.dumps(out, separators=(',', ':')), encoding='utf-8')
print('WHIRLWIND_AUTHORED '+', '.join(k+': '+str(len(v['frames']))+' keys' for k, v in clips.items()))
