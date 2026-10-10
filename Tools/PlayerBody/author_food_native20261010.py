"""Fit food to the accepted drinking arm, using the FPS food rhythm.

Only the approach relative to the bite and the prop tilt come from FPS.
The anatomical shoulder, elbow hinge, wrist and bone lengths stay on Jason.
"""
import json
from pathlib import Path
import numpy as np
from scipy.interpolate import CubicHermiteSpline
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as R

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/ThirdPersonFoodNative20261010'
OUT.mkdir(parents=True, exist_ok=True)
accepted = json.loads((ROOT / 'SourceAssets/ThirdPersonWizardDrink20261010/authored.json').read_text())
rig = json.loads((ROOT / 'SourceAssets/ThirdPersonWizardDrink20261010/inputs.json').read_text())['target']
names, parents = rig['names'], rig['parents']
ref = np.asarray(rig['reference'])
source = np.asarray(accepted['clips']['Consume.Drink']['frames'])
motion = json.loads((ROOT / 'Content/ColdSteelData/potion_use_motion.json').read_text(encoding='utf-8-sig'))
geometry = json.loads((ROOT / 'SourceAssets/Consume20261006/food-geometry.json').read_text())
anatomy = json.loads((ROOT / 'SourceAssets/Consume20261006/contact-anatomy.json').read_text())
cfg = json.loads((ROOT / 'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
u, e, h, head = [names.index(n) for n in ('upperarm_l', 'lowerarm_l', 'hand_l', 'head')]
mouth_local = np.asarray(accepted['mouth_in_head'])

def unit(v):
    return v / max(np.linalg.norm(v), 1.e-10)

def ease(t):
    t = np.clip(t, 0., 1.)
    return t*t*(3.-2.*t)

def world(f):
    w = f.copy()
    for i, p in enumerate(parents):
        if p >= 0:
            q = R.from_quat(w[p, 3:7])
            w[i, :3] = w[p, :3] + q.apply(f[i, :3]*w[p, 7:])
            w[i, 3:7] = (q*R.from_quat(f[i, 3:7])).as_quat()
            w[i, 7:] = w[p, 7:]*f[i, 7:]
    return w

def sample(progress):
    at = np.clip(progress, 0., 1.)*(len(source)-1)
    i = min(int(at), len(source)-2)
    fraction = at-i
    f = source[i]*(1.-fraction)+source[i+1]*fraction
    a, b = R.from_quat(source[i, :, 3:7]), R.from_quat(source[i+1, :, 3:7])
    f[:, 3:7] = (R.from_rotvec((b*a.inv()).as_rotvec()*fraction)*a).as_quat()
    return f

def under(i, ancestor):
    while i >= 0:
        if i == ancestor:
            return True
        i = parents[i]
    return False

# under() includes the ancestor itself. Never reset any of the three driven
# arm joints while rebuilding the weighted helper descendants.
helpers = [i for i in range(len(names)) if under(i, u) and i not in (u, e, h) and not under(i, h)]
axis = unit(ref[h, :3])
lower_ref = R.from_quat(ref[e, 3:7])
rest_direction = lower_ref.apply(axis)
hinge = unit(np.cross(unit(ref[e, :3]), rest_direction))
rest_flex = np.arccos(np.clip(np.dot(unit(ref[e, :3]), rest_direction), -1., 1.))
basis = R.from_euler('z', 90., degrees=True)

# The accepted drink contains the exact runtime V7/Jason mounting convention.
# Replace only the prop's palm offset and its geometry-dependent grip height.
drink_mount = np.asarray(accepted['grip_mount'])
mount_q = R.from_quat(drink_mount[3:7])
prop_q = R.from_euler('x', 90., degrees=True)
palm_to_body_hand = mount_q*prop_q.inv()
old_palm_offset = np.asarray(motion['hp_potion']['grip_in_palm'])
old_height = anatomy['tiers'][0]['grip_height']

def food_track(profile):
    keys = profile['keys']
    times = np.asarray([k['time'] for k in keys])
    points = np.asarray([k['grip'] for k in keys])
    tangents = np.zeros_like(points)
    for i in range(1, len(keys)-1):
        if np.all(np.abs(points[i]-points[i-1]) <= .01) or np.all(np.abs(points[i]-points[i+1]) <= .01):
            continue
        tangents[i] = (points[i+1]-points[i-1])/(times[i+1]-times[i-1])
    curve = CubicHermiteSpline(times, points, tangents)
    rotations = []
    for k in keys:
        pitch, yaw, roll = k['rotation']
        rotations.append(R.from_euler('z', yaw, degrees=True)*R.from_euler('y', -pitch, degrees=True)*R.from_euler('x', -roll, degrees=True))

    def at(t):
        i = min(max(0, np.searchsorted(times, t)-1), len(keys)-2)
        blend = ease((t-times[i])/(times[i+1]-times[i]))
        q = R.from_rotvec((rotations[i+1]*rotations[i].inv()).as_rotvec()*blend)*rotations[i]
        return curve(np.clip(t, times[0], times[-1])), q
    return at

def author(key, label):
    profile = motion[key]
    times = profile['times']
    length = times['duration']
    height = profile['grip_height']
    geo = geometry[key]
    contact = np.asarray(geo['origin']) + [0., 0., geo['extent'][2]]
    held_position = drink_mount[:3] + palm_to_body_hand.apply(np.asarray(profile['grip_in_palm'])-old_palm_offset) - mount_q.apply([0., 0., height-old_height])
    tip_local = held_position + mount_q.apply(contact)
    track = food_track(profile)
    bite_point, bite_q = track(times['contact'])
    bite_tip = bite_point + bite_q.apply(contact-[0., 0., height])
    frames = []
    previous = None
    production = []
    for seconds in np.linspace(0., length, round(length*60)+1):
        phase = np.interp(seconds, [0., times['grab'], times['drink_start'], times['contact'], times['drink_end'], times['release'], length],
                         [0., 0., .4, .64, .75, 1., 1.])
        f = sample(phase)
        # Eating does not need the source's drinking head tilt.
        for i, name in enumerate(names):
            if name.startswith(('neck_', 'head', 'spine_')):
                a = R.from_quat(source[0, i, 3:7])
                gain = .4 if name.startswith(('neck_', 'head')) else .65
                f[i, 3:7] = (R.from_rotvec((R.from_quat(f[i, 3:7])*a.inv()).as_rotvec()*gain)*a).as_quat()
        w = world(f)
        shoulder = w[u, :3]
        mouth = w[head, :3]+R.from_quat(w[head, 3:7]).apply(mouth_local)
        point, q = track(seconds)
        desired = basis*q
        # Relative food-tip motion carries the accepted lift/approach/recovery
        # rhythm. It is anchored to Jason's lips, not the first-person camera.
        goal = mouth+basis.apply(point+q.apply(contact-[0., 0., height])-bite_tip)
        base_upper = R.from_quat(w[u, 3:7])
        wrist = R.from_quat(f[h, 3:7])
        wanted_axis = desired.apply([0., 0., 1.])
        lower = R.from_quat(f[e, 3:7])
        initial_flex = np.arccos(np.clip(lower.apply(axis)[0], -1., 1.))
        initial_unrolled = R.from_rotvec(hinge*(initial_flex-rest_flex))*lower_ref
        initial_roll = np.dot((initial_unrolled.inv()*lower).as_rotvec(), axis)
        initial = np.r_[np.zeros(3), initial_flex, initial_roll] if previous is None else previous.copy()

        def pose(x):
            upper_q = R.from_rotvec(x[:3])*base_upper
            local_lower = R.from_rotvec(hinge*(x[3]-rest_flex))*lower_ref*R.from_rotvec(axis*x[4])
            lower_q = upper_q*local_lower
            elbow = shoulder+upper_q.apply(ref[e, :3])
            wrist_point = elbow+lower_q.apply(ref[h, :3])
            wrist_q = lower_q*wrist
            tip = wrist_point+wrist_q.apply(tip_local)
            return upper_q, local_lower, elbow, tip, wrist_q*mount_q

        def residual(x):
            _, _, elbow, tip, prop = pose(x)
            orientation = (desired.inv()*prop).as_rotvec()
            regularize = np.r_[x[:3]*.15, (x[3]-initial_flex)*.2, (x[4]-initial_roll)*.2]
            clearance = np.array([max(0., shoulder[0]*.55-elbow[0]),
                                  max(0., shoulder[1]+1.-elbow[1]),
                                  max(0., elbow[2]-shoulder[2]+3.)])/1.5
            smooth = (x-previous)*.2 if previous is not None else np.zeros(5)
            return np.r_[(tip-goal)/.35, (prop.apply([0., 0., 1.])-wanted_axis)/.12,
                         orientation/.5, regularize, clearance, smooth]

        bounds = (np.r_[[-1.8]*3, np.deg2rad(15.), np.deg2rad(-85.)],
                  np.r_[[1.8]*3, np.deg2rad(140.), np.deg2rad(85.)])
        solved = least_squares(residual, np.clip(initial, bounds[0]+1.e-6, bounds[1]-1.e-6),
                               bounds=bounds, max_nfev=100, ftol=1.e-7, xtol=1.e-7, gtol=1.e-7)
        previous = solved.x
        upper_q, local_lower, elbow, tip, prop = pose(solved.x)
        f[u, 3:7] = (R.from_quat(w[parents[u], 3:7]).inv()*upper_q).as_quat()
        f[e, 3:7] = local_lower.as_quat()
        # Keep the good drinking wrist local pose. Spread the new forearm roll
        # through its weighted helper bones instead of concentrating it at the cuff.
        for j in helpers:
            f[j] = ref[j]
            if parents[j] == e:
                station = np.clip(np.dot(ref[j, :3], axis)/np.linalg.norm(ref[h, :3]), 0., 1.)
                f[j, 3:7] = (R.from_rotvec(axis*(-solved.x[4]*(1.-station)))*R.from_quat(ref[j, 3:7])).as_quat()
        frames.append(f)
        # Report the actual outgoing pose after helper writes, not the solver's
        # temporary result which can hide an overwritten primary joint.
        final = world(f)
        final_tip = final[h, :3]+R.from_quat(final[h, 3:7]).apply(tip_local)
        production.append(dict(time=float(seconds), contact_fit_cm=float(np.linalg.norm(final_tip-goal)),
                               elbow_flex_deg=float(np.rad2deg(solved.x[3])), forearm_roll_deg=float(np.rad2deg(solved.x[4])),
                               shoulder=final[u, :3].tolist(), elbow=final[e, :3].tolist(), wrist=final[h, :3].tolist(),
                               food_contact=final_tip.tolist(), mouth=mouth.tolist()))
    frames = np.asarray(frames)
    for i in range(1, len(frames)):
        flip = np.sum(frames[i-1, :, 3:7]*frames[i, :, 3:7], axis=1)<0.
        frames[i, flip, 3:7] *= -1.
    return dict(rate=60, contact=times['contact']/length, release=times['drink_end']/length,
                frames=frames.tolist(), source=accepted['clips']['Consume.Drink']['source'],
                food=key, food_grip_mount=np.r_[held_position, mount_q.as_quat()].tolist(),
                contact_point=contact.tolist(), times=times), production

clips, fit = {}, {}
for key, label in [('bread', 'EatBread'), ('baguette_bread', 'EatBaguette')]:
    clips['Consume.'+label], fit[key] = author(key, label)
result = dict(mesh=rig['mesh'], names=names, clips=clips,
              previous_clips={k:cfg['clips'][k] for k in clips}, source_url=accepted['source_url'],
              drink_clip_unchanged=cfg['clips']['Consume.Drink'],
              scope='Third-person food only; accepted drinking wrist and native elbow hinge; FPS food rhythm.',
              gameplay_tested=False, rendered=False)
(OUT/'authored.json').write_text(json.dumps(result, separators=(',', ':')), encoding='utf-8')
(OUT/'author-fit.json').write_text(json.dumps(fit, separators=(',', ':')), encoding='utf-8')
print('FOOD_NATIVE_AUTHORED', ', '.join(clips))
