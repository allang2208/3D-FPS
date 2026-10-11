"""Author the user's vertical left-arm tuck and right-hand stock thrust.

The rejected horizontal-sweep gun path is not a constraint. Both held contacts
are carried by a new rigid gun path; body-side shoulders and downward elbow
planes then support those contacts. Source timing, fingers and mechanics remain.
"""
import copy
from scipy.interpolate import PchipInterpolator, CubicHermiteSpline
from pose_io import *

spec = json.loads((O/'motion_controls.json').read_text())
cam = json.loads((OLD/'camera_basis.json').read_text())
CL, CO = np.array(cam['linear']), np.array(cam['origin_m'])
CAM = np.eye(4)
CAM[:3, :3], CAM[:3, 3] = CL, CO
CAMi = np.linalg.inv(CAM)
keys = np.array(spec['times'])
WRITE[:] = [n+'_'+side for side in ('l', 'r') for n in
    ('clavicle', 'upperarm', 'lowerarm', 'lowerarm_aux', 'lowerarm_twist_02', 'lowerarm_twist_01', 'hand')]+['WPN_root']
vrest = {n: np.array(m) for n, m in json.loads((OLD/'v7_skin_basis.json').read_text())['rest'].items()}
binding = json.loads((O.parents[1]/'BenelliM4Super9020261006/authoring.json').read_text())
warp = {n: np.array(m) for n, m in binding['v7_to_native_warp'].items()}


def ease(t):
    t = np.clip(t, 0., 1.)
    return t*t*t*(10+t*(-15+6*t))


def envelope(entry, end):
    return ease(times/entry)*(1-ease((times-end[0])/(end[1]-end[0])))


support = envelope(spec['support_entry_seconds'], spec['support_return_seconds'])
ownership = envelope(spec['ownership_entry_seconds'], spec['ownership_return_seconds'])


def curve(v):
    v = np.array(v)
    slopes = PchipInterpolator(keys, v, axis=0).derivative()(keys)
    slopes[0] = 0
    slopes[-1] = 0
    return CubicHermiteSpline(keys, v, slopes, axis=0)(times)


angles = np.radians(np.column_stack([curve(spec[n+'_degrees']) for n in ('yaw', 'pitch', 'roll')]))


def hinge_frame(axis, normal):
    x = unit(axis)
    z = unit(normal-x*(normal@x))
    return np.column_stack((x, np.cross(z, x), z))


def turn(axis, angle):
    return R.from_rotvec(unit(axis)*angle).as_matrix()


def twist(m, axis):
    q = R.from_matrix(m).as_quat()
    return (2*np.arctan2(q[:3]@unit(axis), q[3])+np.pi) % (2*np.pi)-np.pi


def blend_rotation(a, b, w):
    return Slerp([0, 1], R.from_matrix([a, b]))([float(w)]).as_matrix()[0]


skin = {}
for side in ('l', 'r'):
    upper, lower, hand = ['%s_%s' % (n, side) for n in ('upperarm', 'lowerarm', 'hand')]
    ru, rf = rest[lower][:3, 3]-rest[upper][:3, 3], rest[hand][:3, 3]-rest[lower][:3, 3]
    vh = unit(np.cross(vrest[lower][:3, 3]-vrest[upper][:3, 3], vrest[hand][:3, 3]-vrest[lower][:3, 3]))
    skin[side] = dict(upper=ru, fore=rf,
        fu=hinge_frame(ru, warp[upper][:3, :3]@vh),
        ff=hinge_frame(rf, warp[lower][:3, :3]@vh))


def arm(pose, idle, carried, side, w):
    a_name, e_name, h_name = ['%s_%s' % (n, side) for n in ('upperarm', 'lowerarm', 'hand')]
    a0, e0, h0 = [CL@idle[n][:3, 3]+CO for n in (a_name, e_name, h_name)]
    h = CL@pose[h_name][:3, 3]+CO
    la, lb = np.linalg.norm(e0-a0), np.linalg.norm(h0-e0)
    target = np.array(spec['left_shoulder_camera_cm' if side == 'l' else 'right_shoulder_camera_cm'])/100
    a = a0*(1-w)+target*w
    axis = unit(h-a)
    distance = np.linalg.norm(h-a)
    # Only translate an unreachable shoulder enough to preserve real lengths
    # and a small bend; no scaled or shortened forearms for camera clearance.
    if distance > .955*(la+lb):
        a += axis*(distance-.955*(la+lb))
        distance = np.linalg.norm(h-a)
    axis0 = unit(h0-a0)
    idle_pole = e0-a0-axis0*((e0-a0)@axis0)
    idle_pole = unit(idle_pole-axis*(idle_pole@axis))
    down = np.array([0., 0. if side == 'l' else .50, -1.])
    pole = unit(down-axis*(down@axis))
    if side == 'r':
        # A modest outward swivel follows the right palm while its upper arm
        # extends. The left arm deliberately has no palm-driven elbow swivel.
        hd = (rot(pose[h_name])*rot(rest[h_name]).inv()).as_matrix()
        desired = -(CL@hd@unit(skin[side]['fore']))
        desired = unit(desired-axis*(desired@axis))
        angle = np.arctan2(axis@np.cross(pole, desired), pole@desired)
        pole = turn(axis, np.clip(angle, -np.radians(45), np.radians(45)))@pole
    angle = np.arctan2(axis@np.cross(idle_pole, pole), idle_pole@pole)
    pole = turn(axis, angle*w)@idle_pole
    along = (la*la-lb*lb+distance*distance)/(2*distance)
    radius = np.sqrt(max(0., la*la-along*along))
    e = a+axis*along+pole*radius
    aa, ee = CL.T@(a-CO), CL.T@(e-CO)
    hh = pose[h_name][:3, 3]
    upper, fore = ee-aa, hh-ee
    hinge = unit(np.cross(upper, fore))
    du = hinge_frame(upper, hinge)@skin[side]['fu'].T
    low = hinge_frame(fore, hinge)@skin[side]['ff'].T
    hd = (rot(pose[h_name])*rot(rest[h_name]).inv()).as_matrix()
    tau = twist(low.T@hd, skin[side]['fore'])
    df = turn(fore, tau)@low
    for stem in ('upperarm', 'lowerarm', 'lowerarm_aux', 'lowerarm_twist_02', 'lowerarm_twist_01'):
        n = stem+'_'+side
        if stem == 'upperarm':
            driver, position = du, aa
        else:
            offset = rest[n][:3, 3]-rest[e_name][:3, 3]
            station = offset@skin[side]['fore']/(skin[side]['fore']@skin[side]['fore'])
            transverse = offset-station*skin[side]['fore']
            position = ee+station*fore+df@transverse
            fraction = {'lowerarm_aux': .5, 'lowerarm_twist_02': .88}.get(stem, 1.)
            driver = blend_rotation(du, df, fraction)
        desired = driver@rot(rest[n]).as_matrix()
        pose[n][:3, :3] = blend_rotation(rot(carried[n]).as_matrix(), desired, w)*np.linalg.norm(idle[n][:3, :3], axis=0)
        pose[n][:3, 3] = position
    clavicle = 'clavicle_'+side
    pose[clavicle] = idle[clavicle].copy()
    pose[clavicle][:3, 3] += aa-idle[a_name][:3, 3]
    return dict(shoulder_camera_cm=(a*100).tolist(), elbow_camera_cm=(e*100).tolist(),
                hand_camera_cm=(h*100).tolist(), forearm_roll_degrees=float(np.degrees(tau)))


def solve(family):
    source, local = decode(family)
    idle = source[0]
    lh0 = CL@idle['hand_l'][:3, 3]+CO
    left = curve([lh0 if v is None else np.array(v)/100 for v in spec['left_hand_camera_cm']])
    front = unit(CL@(idle['WPN_FrontSight'][:3, 3]-idle['WPN_RearSight'][:3, 3]))
    up = unit(CL@idle['WPN_root'][:3, :3]@K['WPN_root'][:3, :3]@np.array([0., -1., 0.]))
    right = unit(np.cross(up, front))
    up = unit(np.cross(front, right))
    basis = np.column_stack((front, right, up))
    changed = {n: [] for n in WRITE}
    controls = []
    gun_inverse = [np.linalg.inv(p['WPN_root']) for p in source]
    for k, (yaw, pitch, roll) in enumerate(angles):
        q = basis@(R.from_rotvec([0, 0, yaw])*R.from_rotvec([0, -pitch, 0])*R.from_rotvec([roll, 0, 0])).as_matrix()@basis.T
        camera_delta = np.eye(4)
        camera_delta[:3, :3], camera_delta[:3, 3] = q, left[k]-q@lh0
        delta = CAMi@camera_delta@CAM
        wanted_gun = delta@idle['WPN_root']
        carry = wanted_gun@gun_inverse[k]
        # The complete assembly moves rigidly. Rebuild only the two support
        # chains afterwards; gun-relative hands/fingers and mechanics stay put.
        p = {n: carry@m for n, m in source[k].items()}
        carried = {n: delta@m for n, m in idle.items()}
        # Upstream body/root motion is not part of the weapon's rigid group.
        for n in ('VM_Root', 'root', 'spine_03'):
            p[n] = source[k][n].copy()
        left_info = arm(p, idle, carried, 'l', support[k])
        right_info = arm(p, idle, carried, 'r', support[k])
        if k in (0, len(times)-1):
            p = source[k]
        packed = encode(p)
        for n in WRITE:
            changed[n].append(packed[n])
        # These are editable construction controls, not a gameplay test report.
        stock = p['WPN_root']@K['WPN_root']@np.array([.030971, 5.224671, 51.443630, 1.])
        controls.append(dict(time=float(times[k]), left=left_info, right=right_info,
            stock_camera_cm=((CL@stock[:3]+CO)*100).tolist()))
    for n in WRITE:
        updated = np.array(changed[n])
        updated[0], updated[-1] = local[n][0], local[n][-1]
        local[n] = updated
    print('R7_AUTHORED', family, len(times), 'keys', flush=True)
    return local, controls


output = copy.deepcopy(D)
output.update(revision=spec['revision'], write_bones=WRITE, runtime_tested=False,
    contact_time=spec['contact_seconds'], method=spec['intent'],
    ownership_curve=dict(name='Super90MeleeArmAuthored', times=times.tolist(), values=ownership.tolist()))
base, controls = solve('base')
report = {'base': controls}
output['base_tracks'] = [track(t['bone'], base[t['bone']]) if t['bone'] in WRITE else t for t in D['base_tracks']]
zero = np.array([0, 0, 0, 0, 0, 0, 1, 0, 0, 0])
for family in D['profiles']:
    local, controls = solve(family)
    report[family] = controls
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
print('SUPER90_VERTICAL_FOLD_R7_AUTHORED', len(report), 'grips', flush=True)
