"""R6: lower the melee support chain, preserve the gun and both held palms.

Author in the measured Super90 hip-camera basis. The runtime ownership curve
hands the left chain to this clip during the swing instead of solving it twice.
"""
import copy
from scipy.optimize import least_squares
from scipy.ndimage import gaussian_filter1d
from pose_io import *

WRITE.insert(0, 'clavicle_l')
RU = rest['lowerarm_l'][:3, 3] - rest['upperarm_l'][:3, 3]
RF = rest['hand_l'][:3, 3] - rest['lowerarm_l'][:3, 3]
cam = json.loads((OLD / 'camera_basis.json').read_text())
CL, CO = np.array(cam['linear']), np.array(cam['origin_m'])
v7 = json.loads((OLD / 'v7_skin_basis.json').read_text())
vrest = {n: np.array(m) for n, m in v7['rest'].items()}
vu = vrest['lowerarm_l'][:3, 3] - vrest['upperarm_l'][:3, 3]
vf = vrest['hand_l'][:3, 3] - vrest['lowerarm_l'][:3, 3]
vh = unit(np.cross(vu, vf))
binding = json.loads((O.parents[1] / 'BenelliM4Super9020261006/authoring.json').read_text())
warp = {n: np.array(m) for n, m in binding['v7_to_native_warp'].items()}


def ease(t):
    t = np.clip(t, 0., 1.)
    return t*t*t*(10+t*(-15+6*t))


def frame(axis, normal):
    x = unit(axis)
    z = unit(normal-x*(normal@x))
    return np.column_stack((x, np.cross(z, x), z))


def turn(axis, angle):
    return R.from_rotvec(unit(axis)*angle).as_matrix()


def swing(a, b):
    a, b = unit(a), unit(b)
    c = np.cross(a, b)
    return R.from_rotvec(unit(c)*np.arctan2(np.linalg.norm(c), a@b)).as_matrix()


def twist(m, axis):
    q = R.from_matrix(m).as_quat()
    return (2*np.arctan2(q[:3]@unit(axis), q[3])+np.pi) % (2*np.pi)-np.pi


FU0 = frame(RU, warp['upperarm_l'][:3, :3]@vh)
FF0 = frame(RF, warp['lowerarm_l'][:3, :3]@vh)
# Full control before contact; handoff finishes with the existing 0.9 s clip.
support = ease(times/.10)*(1-ease((times-.69)/.21))
stations, offsets = {}, {}
for n in WRITE:
    if n.startswith('lowerarm'):
        delta = rest[n][:3, 3]-rest['lowerarm_l'][:3, 3]
        stations[n] = float(delta@RF/(RF@RF))
        offsets[n] = delta-stations[n]*RF


def solve(family):
    poses, local = decode(family)
    idle = poses[0]
    a0 = idle['upperarm_l'][:3, 3]
    shoulder_camera = CL@a0+CO
    # Lower the root as the gun swings across the chest. A lower elbow alone
    # would merely fold the upper arm against an unchanged high shoulder.
    shoulder_target = shoulder_camera+np.array([-.015, -.020, -.085])

    def geometry(k, controls):
        p = poses[k]
        original_a, original_e, h = [p[n][:3, 3] for n in
                                    ('upperarm_l', 'lowerarm_l', 'hand_l')]
        la, lb = np.linalg.norm(original_e-original_a), np.linalg.norm(h-original_e)
        dh = (rot(p['hand_l'])*rot(rest['hand_l']).inv()).as_matrix()
        radius = np.linalg.norm(controls[:2])
        cone = np.radians(40)
        angles = controls[:2]*(cone*np.tanh(radius/cone)/max(radius, 1e-12))
        target_f = R.from_rotvec(dh@FF0[:, 1]*angles[0]+dh@FF0[:, 2]*angles[1]).apply(dh@unit(RF))
        original_f = unit(h-original_e)
        change = R.from_matrix(swing(original_f, target_f))
        fdir = R.from_rotvec(change.as_rotvec()*support[k]).apply(original_f)
        e = h-lb*fdir
        preferred_a = (1-support[k])*original_a+support[k]*(CL.T@(shoulder_target-CO))
        udir = unit(e-preferred_a)
        bend = np.clip(np.arccos(np.clip(udir@fdir, -1, 1)), np.radians(30), np.radians(115))
        radial = unit(udir-fdir*(udir@fdir))
        udir = np.cos(bend)*fdir+np.sin(bend)*radial
        udir = turn(fdir, controls[2]*support[k])@udir
        a = e-la*udir
        upper, fore = e-a, h-e
        hinge = unit(np.cross(upper, fore))
        low = frame(fore, hinge)@FF0.T
        roll = twist(low.T@dh, RF)
        return a, e, h, upper, fore, hinge, low, roll

    raw, previous = [], np.zeros(3)
    for k in range(len(times)):
        if k in (0, len(times)-1):
            raw.append(np.zeros(3))
            continue
        w = support[k]
        target = shoulder_camera*(1-w)+shoulder_target*w

        def residual(x):
            a, e, h, upper, fore, hinge, low, roll = geometry(k, x)
            ac, ec, hc = [CL@v+CO for v in (a, e, h)]
            return np.r_[(ac-target)/.10*np.array([1.6, 1.4, 2.0]),
                .12*x[:2], .25*x[2], .24*(x-previous),
                # Keep a visible forearm rise to the palm, instead of the old
                # elbow hump beside the receiver. Limits are authoring values.
                80*w*max(0, ec[2]-min(hc[2]-.070, target[2]+.015)),
                50*w*max(0, ec[1]-ac[1]+.006),
                35*w*max(0, ac[2]-target[2]-.020),
                25*w*max(0, ac[0]-shoulder_camera[0]-.075),
                20*w*max(0, shoulder_camera[0]-ac[0]-.070),
                3*w*max(0, abs(roll)-np.radians(95))]

        fit = least_squares(residual, previous,
            bounds=([-1.6, -1.6, -np.radians(30)], [1.6, 1.6, np.radians(30)]),
            max_nfev=65, ftol=1e-6, xtol=1e-6, gtol=1e-6)
        previous = fit.x
        raw.append(previous.copy())
    controls = gaussian_filter1d(np.array(raw), 3, axis=0, mode='nearest')
    rows = [geometry(k, x) for k, x in enumerate(controls)]
    rolls = np.unwrap([r[7] for r in rows])
    changed = {n: [] for n in WRITE}
    for k, (a, e, h, upper, fore, hinge, low, _) in enumerate(rows):
        p = {n: m.copy() for n, m in poses[k].items()}
        # Separate the skin hinge from palm pronation. Do not carry the full
        # palm roll into the upper arm, or leave 1/3 of it at the wrist helper.
        du = frame(upper, hinge)@FU0.T
        df = turn(fore, rolls[k])@low
        for n in WRITE:
            if n in ('clavicle_l', 'hand_l'):
                continue
            if n == 'upperarm_l':
                driver, position = du, a
            else:
                fraction = {'lowerarm_aux_l': .5, 'lowerarm_twist_02_l': .88}.get(n, 1.)
                driver = Slerp([0, 1], R.from_matrix([du, df]))([fraction]).as_matrix()[0]
                position = e+stations[n]*fore+df@offsets[n]
            target_rotation = R.from_matrix(driver)*rot(rest[n])
            q = Slerp([0, 1], R.from_quat([rot(poses[k][n]).as_quat(), target_rotation.as_quat()]))([float(support[k])])[0]
            p[n][:3, :3] = q.as_matrix()*np.linalg.norm(poses[k][n][:3, :3], axis=0)
            p[n][:3, 3] = position
        p['clavicle_l'][:3, 3] += a-poses[k]['upperarm_l'][:3, 3]
        if k in (0, len(times)-1):
            p = poses[k]
        packed = encode(p)
        for n in WRITE:
            changed[n].append(packed[n])
    for n in WRITE:
        updated = np.array(changed[n])
        updated[0], updated[-1] = local[n][0], local[n][-1]
        local[n] = updated
    info = dict(controls=controls.tolist(), support_weight=support.tolist(),
        shoulder_camera_cm=[((CL@r[0]+CO)*100).tolist() for r in rows],
        elbow_camera_cm=[((CL@r[1]+CO)*100).tolist() for r in rows],
        forearm_roll_degrees=np.degrees(rolls).tolist())
    print('R6_AUTHORED', family, len(times), 'keys', flush=True)
    return local, info


output = copy.deepcopy(D)
output.update(revision='Super90QuickMelee-LeftArmR6-20261010', write_bones=WRITE,
    runtime_tested=False, contact_time=1/6,
    ownership_curve=dict(name='Super90MeleeArmAuthored', times=times.tolist(), values=support.tolist()),
    method='Lower torso support; independent upper hinge and distal wrist roll; curve-owned melee arm')
base, info = solve('base')
report = {'base': info}
output['base_tracks'] = [track(t['bone'], base[t['bone']]) if t['bone'] in WRITE else t for t in D['base_tracks']]
zero = np.array([0, 0, 0, 0, 0, 0, 1, 0, 0, 0])
for family in D['profiles']:
    local, info = solve(family)
    report[family] = info
    tracks = [t for t in D['profiles'][family]['clip']['tracks'] if t['bone'] not in WRITE]
    for n in WRITE:
        q = (R.from_quat(local[n][:, 3:7])*R.from_quat(base[n][:, 3:7]).inv()).as_quat()
        q[q[:, 3] < 0] *= -1
        delta = np.c_[local[n][:, :3]-base[n][:, :3], q, local[n][:, 7:]-base[n][:, 7:]]
        if np.max(np.abs(delta-zero)) > 1e-7:
            tracks.append(track(n, delta))
    output['profiles'][family]['clip']['tracks'] = tracks
(O/'animation_patch.json').write_text(json.dumps(output, separators=(',', ':')))
(O/'authoring_controls.json').write_text(json.dumps(report, separators=(',', ':')))
print('SUPER90_MELEE_R6_AUTHORED', len(report), 'grips', flush=True)
