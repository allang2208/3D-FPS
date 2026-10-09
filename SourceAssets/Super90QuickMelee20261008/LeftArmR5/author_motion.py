"""Keep installed palms/gun; rebuild left-arm support from the body's idle shoulder.

R4 inherited the donor's far-left shoulder and moved the elbow to its inner side.
R5 keeps the shoulder near the body's left side, limits humeral swivel, and uses the
V7 skin's converted hinge basis rather than the nearly straight native bind plane.
"""
import copy
from scipy.optimize import least_squares
from scipy.ndimage import gaussian_filter1d
from pose_io import *

WRITE.insert(0, 'clavicle_l')
RU = rest['lowerarm_l'][:3, 3] - rest['upperarm_l'][:3, 3]
RF = rest['hand_l'][:3, 3] - rest['lowerarm_l'][:3, 3]
RH = unit(np.cross(RU, RF))
CAP = np.radians(100)
cam = json.loads((OLD / 'camera_basis.json').read_text())
CL, CO = np.array(cam['linear']), np.array(cam['origin_m'])

def ease(x):
    x = np.clip(x, 0., 1.)
    return x * x * x * (10 + x * (-15 + 6 * x))

def frame(axis, normal):
    x = unit(axis); z = unit(normal - x * (normal @ x))
    return np.column_stack((x, np.cross(z, x), z))

v7 = json.loads((O / 'v7_skin_basis.json').read_text())
vrest = {n: np.array(m) for n, m in v7['rest'].items()}
vu = vrest['lowerarm_l'][:3, 3] - vrest['upperarm_l'][:3, 3]
vf = vrest['hand_l'][:3, 3] - vrest['lowerarm_l'][:3, 3]
vh = unit(np.cross(vu, vf))
binding = json.loads((O.parents[1] / 'BenelliM4Super9020261006/authoring.json').read_text())
warp = {n: np.array(m) for n, m in binding['v7_to_native_warp'].items()}
skin_upper_hinge = warp['upperarm_l'][:3, :3] @ vh
skin_forearm_hinge = warp['lowerarm_l'][:3, :3] @ vh
FU0, FF0 = frame(RU, skin_upper_hinge), frame(RF, skin_forearm_hinge)

def axis_angle(axis, angle):
    return R.from_rotvec(unit(axis) * angle).as_matrix()

def swing(a, b):
    a, b = unit(a), unit(b)
    return R.from_quat(np.r_[np.cross(a, b), 1 + np.clip(a @ b, -1, 1)]).as_matrix()

def twist(m, axis):
    q = R.from_matrix(m).as_quat()
    v = 2 * np.arctan2(q[:3] @ unit(axis), q[3])
    return (v + np.pi) % (2 * np.pi) - np.pi

def smooth_pinned(v, sigma=4):
    v = np.array(v); out = gaussian_filter1d(v, sigma, axis=0, mode='nearest')
    j = np.arange(len(v)); a = np.clip(1 - j / (3 * sigma), 0, 1) ** 2
    b = a[::-1]
    if v.ndim > 1:
        a = a[:, None]; b = b[:, None]
    return out + a * (v[0] - out[0]) + b * (v[-1] - out[-1])

def solve(family):
    poses, local = decode(family)
    idle = poses[0]
    A0, E0, T0 = [idle[n][:3, 3] for n in ('upperarm_l', 'lowerarm_l', 'hand_l')]
    idle_u, idle_f = E0 - A0, T0 - E0
    idle_h = unit(np.cross(idle_u, idle_f))
    UI, FI = frame(idle_u, idle_h), frame(idle_f, idle_h)
    # Native helper positions, not the unrelated M4/PKM skeleton's conventions.
    stations, offsets = {}, {}
    for n in WRITE:
        if not n.startswith('lowerarm'):
            continue
        r = rest[n][:3, 3] - rest['lowerarm_l'][:3, 3]
        stations[n] = float(r @ RF / (RF @ RF))
        offsets[n] = r - stations[n] * RF
    raw, prev = [], np.zeros(3)
    support = ease(times / .10) * (1 - ease((times - .71) / .19))
    shoulder_camera = CL @ A0 + CO

    def geometry(k, x):
        p = poses[k]
        t = p['hand_l'][:3, 3]
        la = np.linalg.norm(p['lowerarm_l'][:3, 3] - p['upperarm_l'][:3, 3])
        lb = np.linalg.norm(t - p['lowerarm_l'][:3, 3])
        dh = (rot(p['hand_l']) * rot(rest['hand_l']).inv()).as_matrix()
        neutral = dh @ unit(RF)
        # Solve from the held wrist back towards the torso. The wrist cone is
        # structural; a shoulder-root penalty cannot silently force it to 80 deg.
        r = np.linalg.norm(x[:2])
        v = x[:2] * (np.radians(35) * np.tanh(r / np.radians(35)) / max(r, 1e-12))
        rotation_vector = (dh @ FF0[:, 1]) * v[0] + (dh @ FF0[:, 2]) * v[1]
        target_f = R.from_rotvec(rotation_vector).apply(neutral)
        carried_f = (rot(p['hand_l']) * rot(idle['hand_l']).inv()).apply(unit(idle_f))
        q = R.from_matrix(swing(carried_f, target_f))
        fdir = R.from_rotvec(q.as_rotvec() * support[k]).apply(carried_f)
        e = t - lb * fdir
        # Keep the arm root near its actual idle/body anchor, not the donor's
        # far-left anchor. Elbow flexion and upper-arm swivel remain bounded.
        upper_dir = unit(e - A0)
        bend = np.arccos(np.clip(upper_dir @ fdir, -1, 1))
        bounded_bend = np.clip(bend, np.radians(35), np.radians(125))
        radial = unit(upper_dir - fdir * (upper_dir @ fdir))
        upper_dir = np.cos(bounded_bend) * fdir + np.sin(bounded_bend) * radial
        upper_dir = axis_angle(fdir, x[2] * support[k]) @ upper_dir
        a = e - la * upper_dir
        u, f = e - a, t - e
        h = unit(np.cross(u, f))
        dl = frame(f, h) @ FF0.T
        tau = twist(dl.T @ dh, RF)
        wrist = np.arccos(np.clip(unit(f) @ (dh @ unit(RF)), -1, 1))
        return a, e, t, u, f, h, dl, tau, wrist

    # The bounded wrist cone and elbow flexion are built into the chain itself.
    # Optimisation now selects a nearby torso support and modest humeral swivel,
    # not an arbitrary point on a nearly 180-degree shoulder-wrist elbow circle.
    for k in range(len(times)):
        if k in (0, len(times) - 1):
            raw.append(np.zeros(3)); prev = np.zeros(3)
            continue
        w = support[k]
        def residual(x):
            a, e, t, u, f, h, dl, tau, wrist = geometry(k, x)
            ec, tc, ac = CL @ e + CO, CL @ t + CO, CL @ a + CO
            return np.r_[(ac - shoulder_camera) / .10 * [1.4, 2.0, 1.4],
                .35 * x[2], .10 * x[:2], .15 * (x - prev),
                4 * w * max(0, abs(tau) - np.radians(95)),
                55 * w * max(0, ec[1] - ac[1] + .008),
                30 * w * max(0, ec[2] - min(tc[2] + .005, -.15)),
                30 * max(0, ac[2] - shoulder_camera[2] - .01),
                24 * max(0, .10 - ec[0]),
                25 * max(0, ac[0] - shoulder_camera[0] - .20),
                25 * max(0, shoulder_camera[0] - ac[0] - .07)]
        fit = least_squares(residual, prev, bounds=([-1.6, -1.6, -np.radians(40)],
                                                    [1.6, 1.6, np.radians(40)]),
                            max_nfev=65, ftol=1e-6, xtol=1e-6, gtol=1e-6)
        prev = fit.x; raw.append(prev.copy())
    controls = smooth_pinned(raw)
    rows = [geometry(k, x) for k, x in enumerate(controls)]
    tau = np.unwrap([r[7] for r in rows])
    fore = np.clip(tau, -CAP, CAP)
    upper = tau - fore
    changed = {n: [] for n in WRITE}

    for k, (a, e, t, u, f, h, dl, _, wrist) in enumerate(rows):
        p = {n: m.copy() for n, m in poses[k].items()}
        w = support[k]
        # The remainder is coherent on both sides of the elbow. The skin hinge
        # does not inherit the full palm pronation as it did in R3.
        fe = axis_angle(f, upper[k]) @ dl
        # Independent converted skin hinges keep the modelled upper/forearm
        # crease aligned, despite the native and V7 bind planes differing.
        du = axis_angle(u, upper[k]) @ frame(u, h) @ FU0.T
        for n in WRITE:
            if n in ('clavicle_l', 'hand_l'):
                continue
            is_upper = n == 'upperarm_l'
            station = 0. if is_upper else stations[n]
            d = du if is_upper else axis_angle(f, fore[k] * station) @ fe
            target = R.from_matrix(d) * rot(rest[n])
            carry_frame = frame(u, h) @ UI.T if is_upper else frame(f, h) @ FI.T
            carried = R.from_matrix(carry_frame) * rot(idle[n])
            q = Slerp([0, 1], R.from_quat([carried.as_quat(), target.as_quat()]))([float(w)])[0]
            p[n][:3, :3] = q.as_matrix() * np.linalg.norm(poses[k][n][:3, :3], axis=0)
            if is_upper:
                p[n][:3, 3] = a
            else:
                # Use the same gradual change for helper offsets as the rotations.
                idle_offset = idle[n][:3, 3] - E0 - station * idle_f
                offset = (1 - w) * (carry_frame @ idle_offset) + w * (d @ offsets[n])
                p[n][:3, 3] = e + station * f + offset
        p['clavicle_l'][:3, 3] += a - poses[k]['upperarm_l'][:3, 3]
        # hand_l and all fingers remain the exact installed world matrices.
        # This recomputes hand_l locally under the repaired lowerarm parent.
        if k in (0, len(times) - 1):
            p = poses[k]
        packed = encode(p)
        for n in WRITE:
            changed[n].append(packed[n])
    # Keep endpoint key values byte-for-byte from the installed input where possible.
    for n in WRITE:
        changed[n] = np.array(changed[n])
        changed[n][0] = local[n][0]; changed[n][-1] = local[n][-1]
        local[n] = changed[n]
    shoulder_offsets = np.array([CL @ (r[0] - A0) * 100 for r in rows])
    info = dict(shoulder_offset_camera_cm=shoulder_offsets.tolist(),
                shoulder_anchor_camera_cm=(shoulder_camera * 100).tolist(),
                upper_swivel_degrees=np.degrees(controls[:, 2] * support).tolist(),
                elbow_camera_cm=[((CL @ r[1] + CO) * 100).tolist() for r in rows],
                elbow_flex_degrees=[float(np.degrees(np.arccos(np.clip(unit(r[3]) @ unit(r[4]), -1, 1)))) for r in rows],
                palm_pronation_degrees=np.degrees(tau).tolist(),
                forearm_pronation_degrees=np.degrees(fore).tolist(),
                upper_remainder_degrees=np.degrees(upper).tolist(),
                wrist_bend_degrees=np.degrees([r[8] for r in rows]).tolist(),
                helper_stations=stations)
    print('AUTHORED_LEFT_ARM', family, 'shoulder support cm',
          round(float(np.max(np.linalg.norm(shoulder_offsets, axis=1))), 2), flush=True)
    return local, info

output = copy.deepcopy(D)
output.update(revision='Super90QuickMelee-LeftArmR5-20261008', write_bones=WRITE,
              runtime_tested=False, contact_time=1/6,
              method='Wrist-first arm solve; torso-side shoulder, bounded flexion/swivel, converted V7 skin hinge; installed palms/gun fixed')
base, info = solve('base')
report = {'base': info}
output['base_tracks'] = [track(t['bone'], base[t['bone']]) if t['bone'] in WRITE else t
                         for t in D['base_tracks']]
zero = np.array([0, 0, 0, 0, 0, 0, 1, 0, 0, 0])
for family in D['profiles']:
    local, info = solve(family); report[family] = info
    tracks = [t for t in D['profiles'][family]['clip']['tracks'] if t['bone'] not in WRITE]
    for n in WRITE:
        q = (R.from_quat(local[n][:, 3:7]) * R.from_quat(base[n][:, 3:7]).inv()).as_quat()
        q[q[:, 3] < 0] *= -1
        values_out = np.c_[local[n][:, :3] - base[n][:, :3], q, local[n][:, 7:] - base[n][:, 7:]]
        if np.max(np.abs(values_out - zero)) > 1e-7:
            tracks.append(track(n, values_out))
    output['profiles'][family]['clip']['tracks'] = tracks
(O / 'animation_patch.json').write_text(json.dumps(output, separators=(',', ':')))
(O / 'authoring_controls.json').write_text(json.dumps(report, separators=(',', ':')))
print('SUPER90_LEFT_ARM_AUTHORED', len(times), 'keys;', len(report), 'grips', flush=True)
