"""Author Jason's uppercut and dash overhead as complete, in-place body clips.

Only equipment bind/idle anatomy is taken from the FPS rig. Neither attack
copies its FPS animation. Body proportions, elbow planes, weight transfer and
recovery are authored here. CC0 KayKit Chop supplies restrained torso accents;
UAL2 Heavy Combo is a timing/weight reference, not imported animation tracks.
"""
import json
import math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp

OUT = Path(__file__).resolve().parent
d = json.loads((OUT/'authoring-input.json').read_text())
names, parents = d['names'], d['parents']
ix = {n: i for i, n in enumerate(names)}
ref = np.array(d['reference'])
IDENTITY = np.array([0., 0., 0., 1.])

def unit(v):
    return v/max(np.linalg.norm(v), 1e-10)

def mul(a, b):
    return (R.from_quat(a)*R.from_quat(b)).as_quat()

def rot(q, v):
    return R.from_quat(q).apply(v)

def inv(q):
    return R.from_quat(q).inv().as_quat()

def axis(v, degrees):
    return R.from_rotvec(unit(np.array(v))*math.radians(degrees)).as_quat()

def between(a, b):
    a, b = unit(a), unit(b)
    return unit(np.r_[np.cross(a, b), 1+np.dot(a, b)])

def smooth(t):
    t = float(np.clip(t, 0., 1.))
    return t*t*t*(10+t*(-15+6*t))

def fk(f):
    w = f.copy()
    for i, p in enumerate(parents):
        if p < 0:
            continue
        w[i, :3] = w[p, :3]+rot(w[p, 3:7], f[i, :3]*w[p, 7:])
        w[i, 3:7] = mul(w[p, 3:7], f[i, 3:7])
        w[i, 7:] = w[p, 7:]*f[i, 7:]
    return w

def set_world_q(f, b, q):
    w = fk(f)
    p = parents[b]
    f[b, 3:7] = mul(inv(w[p, 3:7]), q) if p >= 0 else q

bind = fk(ref)

def frame_from_xy(x, y):
    x = unit(x)
    y = unit(y-x*np.dot(x, y))
    return R.from_matrix(np.column_stack((x, y, np.cross(x, y)))).as_quat()

def compose(a, b):
    return np.r_[a[:3]+rot(a[3:7], b[:3]), mul(a[3:7], b[3:7])]

def inverse(t):
    q = inv(t[3:7])
    return np.r_[rot(q, -t[:3]), q]

def palm_mount(side):
    # Same anatomical frame as FFPSBodyGripRig::Initialize. Rigid transforms
    # deliberately omit imported scale=100: positions are already centimetres.
    points = []
    source_ref = d['equipment']['reference']
    for skeleton in (source_ref, {n: bind[i] for i, n in enumerate(names)}):
        hand = np.array(skeleton['hand_'+side])
        points.append(np.array([rot(inv(hand[3:7]), np.array(skeleton[digit+'_01_'+side])[:3]-hand[:3])
                               for digit in ('index', 'middle', 'pinky')]))
    a, b = points
    q = mul(frame_from_xy(b[1], b[0]-b[2]), inv(frame_from_xy(a[1], a[0]-a[2])))
    return np.r_[b.mean(axis=0)-rot(q, a.mean(axis=0)), q]

equipment_pose = d['equipment']['pose']
weapon_bind = np.array(equipment_pose['WPN_root'])[:7]
grips = {s: compose(inverse(weapon_bind), compose(np.array(equipment_pose['hand_'+s])[:7], inverse(palm_mount(s))))
         for s in ('r', 'l')}

def solve_chain(f, chain, point, end_q, pole, seed=None):
    """Fixed-length two-bone IK; transport bend frames without wrist stretching."""
    a, b, c = [ix[n] for n in chain]
    w = fk(f)
    origin = w[a, :3]
    l1, l2 = np.linalg.norm(ref[b, :3]), np.linalg.norm(ref[c, :3])
    direction = unit(point-origin)
    length = float(np.clip(np.linalg.norm(point-origin), abs(l1-l2)+.05, (l1+l2)*.98))
    point = origin+direction*length
    along = (l1*l1-l2*l2+length*length)/(2*length)
    bend = unit(pole-direction*np.dot(pole, direction))
    joint = origin+direction*along+bend*math.sqrt(max(0., l1*l1-along*along))
    initial = bind if seed is None else seed
    # Use the reference elbow/knee plane as the second axis, not arbitrary
    # shortest-arc wrist roll. This gives the upper and lower limb one plane.
    old1, old2 = initial[b, :3]-initial[a, :3], initial[c, :3]-initial[b, :3]
    old_normal = unit(np.cross(old1, old2))
    new_normal = unit(np.cross(joint-origin, point-joint))
    for bone, old, new in ((a, old1, joint-origin), (b, old2, point-joint)):
        q = mul(frame_from_xy(new, new_normal), inv(frame_from_xy(old, old_normal)))
        set_world_q(f, bone, mul(q, initial[bone, 3:7]))
    set_world_q(f, c, end_q)

def sample_curve(keys, t):
    # All authored keys have zero velocity at semantic accents. The release
    # gets its speed from the short interval, not an overshooting cubic spline.
    for a, b in zip(keys, keys[1:]):
        if t <= b[0]:
            u = smooth((t-a[0])/(b[0]-a[0]))
            return np.array(a[1:])*(1-u)+np.array(b[1:])*u
    return np.array(keys[-1][1:])

# Columns: t, sword guard xyz, blade pitch (0 up, 90 forward), yaw,
# pelvis xyz, pelvis yaw, torso forward lean, chest twist, stance amount.
# Actor space is +Y forward, -X right, +Z up; sword local +Z is the blade.
NEUTRAL = [0, 38, 116, 32, 0, 0, 1, 81, 0, 3, 0, 0]
UPPER = [
    [0., *NEUTRAL],
    [.32, -13, 29, 103, 74, -12, -2, -1, 78, 6, 6, 8, .3],
    [.82, -23, 25, 89, 143, -15, -3, -3, 75, 13, 10, 15, .85],
    [1., -25, 27, 87, 153, -12, -3, -2, 75, 15, 11, 16, 1],
    [1.075, -2, 44, 139, 27, 0, 0, 5, 82, -4, 0, -5, 1],
    [1.125, 4, 39, 151, -18, 0, 1, 5, 83, -7, -3, -6, 1],
    [1.27, 6, 34, 148, -16, 0, 1, 4, 82, -6, -1, -4, 1],
    [1.65, -6, 39, 125, 17, 0, 0, 2, 81, -2, 2, -2, .45],
    [2.05, *NEUTRAL],
]
# Dash source uses a compact .25 s lift rather than ordinary long preparation.
DASH = [
    [0., *NEUTRAL],
    [.16, -1, 22, 166, -48, 0, 0, -1, 82, 1, -5, 2, .45],
    [.25, 0, 24, 165, -34, 0, 0, 1, 81, 0, -2, 1, .8],
    [.34, 0, 48, 133, 62, 0, 0, 5, 78, 0, 9, 0, 1],
    [.43, -1, 48, 104, 143, 0, 0, 6, 76, 0, 15, 0, 1],
    [.56, -1, 45, 102, 150, 0, 0, 5, 76, 0, 13, 0, 1],
    [.94, -3, 43, 111, 80, 0, 0, 3, 79, 0, 6, 0, .7],
    [1.63, *NEUTRAL],
]

def author_pose(keys, t, label):
    params = sample_curve(keys, t)
    location, pitch, yaw = params[:3], params[3], params[4]
    hip, hip_yaw, lean, twist, stance = params[5:8], *params[8:]
    f = ref.copy()
    f[ix['pelvis'], :3] = hip
    f[ix['pelvis'], 3:7] = mul(axis([0, 0, 1], hip_yaw), ref[ix['pelvis'], 3:7])
    # Spread effort over the torso, keep every neck/head local offset intact.
    # Subtle KayKit chest variation adds donor follow-through without copying
    # its very large backwards pelvis translation or separated hand tracks.
    chop = d['clips']['chop']
    donor_index = min(len(chop['frames'])-1, round((.2+.9*min(t/keys[-1][0], 1))/chop['duration']*(len(chop['frames'])-1)))
    donor = np.array(chop['frames'][donor_index])
    accent = .10*math.sin(math.pi*t/keys[-1][0])**2 if label == 'DashOverhead' else 0.
    for bone, share in [('spine_01', .25), ('spine_02', .30), ('spine_03', .45)]:
        b = ix[bone]
        q = mul(axis([0, 0, 1], twist*share), axis([1, 0, 0], -lean*share))
        base = Slerp([0, 1], R.from_quat([ref[b, 3:7], donor[b, 3:7]]))([accent]).as_quat()[0]
        f[b, 3:7] = base
        set_world_q(f, b, mul(q, fk(f)[b, 3:7]))
    # Counter-rotate the neck modestly while keeping the gaze forward. No
    # translated head targets or scale keys are used to reach the weapon.
    for bone, share in [('neck_01', .55), ('head', .45)]:
        b = ix[bone]
        q = mul(axis([0, 0, 1], -(hip_yaw+twist)*.65*share), axis([1, 0, 0], lean*.45*share))
        set_world_q(f, b, mul(q, fk(f)[b, 3:7]))

    for side, sign in [('r', -1), ('l', 1)]:
        # Lower body is used at low ground speed. At speed the existing
        # locomotion owns feet, so an in-place planted pose cannot skate.
        toe = bind[ix['ball_'+side], :3].copy()
        toe[0] += sign*3*stance
        toe[1] += (-9 if side == 'r' else 17)*stance
        foot_yaw = axis([0, 0, 1], -sign*8*stance)
        heel = (7 if side == 'r' else 0)*stance
        foot_q = mul(mul(foot_yaw, axis([1, 0, 0], -heel)), bind[ix['foot_'+side], 3:7])
        ankle = toe-rot(foot_q, ref[ix['ball_'+side], :3])
        solve_chain(f, ['thigh_'+side, 'calf_'+side, 'foot_'+side], ankle, foot_q,
                    rot(foot_yaw, np.array([sign*.12, 1., 0.])))
        set_world_q(f, ix['ball_'+side], mul(foot_yaw, bind[ix['ball_'+side], 3:7]))

    weapon_q = mul(axis([0, 0, 1], yaw), axis([1, 0, 0], -pitch))
    weapon = np.r_[location, weapon_q]
    targets = {s: compose(weapon, grips[s]) for s in ('r', 'l')}
    # Clamp the pair's common translation to both reach spheres. Never clamp
    # two wrists independently: that would change the sword's grip spacing.
    w = fk(f)
    correction = np.zeros(3)
    for _ in range(10):
        for s in ('r', 'l'):
            shoulder = w[ix['upperarm_'+s], :3]
            reach = .96*sum(np.linalg.norm(ref[ix[b+'_'+s], :3]) for b in ('lowerarm', 'hand'))
            delta = targets[s][:3]+correction-shoulder
            distance = np.linalg.norm(delta)
            if distance > reach:
                correction -= unit(delta)*(distance-reach)
    for s, sign in [('r', -1), ('l', 1)]:
        # The elbow travels out/down with the arm as the blade rises. This
        # pole never flips from one side of the arm to the other at the top.
        elevation = float(np.clip((location[2]-118)/48, 0., 1.))
        pole = np.array([sign*.85, -.15-.45*elevation, -.65+.4*elevation])
        solve_chain(f, ['upperarm_'+s, 'lowerarm_'+s, 'hand_'+s],
                    targets[s][:3]+correction, targets[s][3:7], pole)
    return f

clips = {}
for label, keys, contact, release in [('Uppercut', UPPER, 1., 1.125), ('DashOverhead', DASH, .25, .43)]:
    intervals = round(keys[-1][0]*30)
    contact_frame, release_frame = round(contact*30), round(release*30)
    # Put phase markers on authored frames. Runtime then maps these exact
    # poses to each weapon's contact/release clocks without frame quantization.
    def source_time(frame):
        return float(np.interp(frame, [0, contact_frame, release_frame, intervals], [0., contact, release, keys[-1][0]]))
    frames = np.array([author_pose(keys, source_time(i), label) for i in range(intervals+1)])
    for i in range(1, len(frames)):
        flip = np.sum(frames[i-1, :, 3:7]*frames[i, :, 3:7], axis=1)<0
        frames[i, flip, 3:7] *= -1
    clips[label] = dict(rate=30, contact=contact_frame/intervals, release=release_frame/intervals, frames=frames.tolist())
result = dict(mesh=d['mesh'], skeleton=d['skeleton'], names=names, clips=clips,
    provenance='Authored third-person Jason actions; KayKit Character Animations 1.1 CC0 torso accents; native idle grip calibration only',
    source_url='https://kaylousberg.itch.io/kaykit-character-animations',
    reference_url='https://quaternius.itch.io/universal-animation-library-2')
(OUT/'authored-actions.json').write_text(json.dumps(result, separators=(',', ':')), encoding='utf-8')
print('SWORD_ACTIONS_AUTHORED '+', '.join(k+': '+str(len(v['frames']))+' keys' for k, v in clips.items()))
