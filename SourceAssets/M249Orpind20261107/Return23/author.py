"""Compact left-hand release and return, scoped to M249 side-magazine tails.

Author from the current compressed clips and the current family idle contacts.
Magazine seating, right-hand charging and the existing gameplay clocks are retained.
"""
from pathlib import Path
import pickle, json, gzip
import numpy as np
from scipy.spatial.transform import Rotation as R

r = Path(__file__).resolve().parent
helpers = r.parent / 'Repair20/author.py'
s = {'__file__': str(helpers)}
exec(compile(helpers.read_text().split("outdir=r/'Motion'")[0], str(helpers), 'exec'), s)
d = pickle.load(open(r / 'current.pkl', 'rb'))
s['d'] = d
world, layer, encode, mix, ease, rot, unit = [s[k] for k in ('world', 'layer', 'encode', 'mix', 'ease', 'rot', 'unit')]
names, ix, parents = s['names'], s['ix'], s['parents']
hinge = s['hinge']
hinge.CAP = np.radians(145.)
hinge.ELBOW_CM = 3.
bind, arm_names = s['binding']('l')
arm_ids = [ix[n] for n in arm_names]
fingers = [i for i, n in enumerate(names) if n.endswith('_l') and n.startswith(('thumb', 'index', 'middle', 'ring', 'pinky'))]
left_ids = arm_ids + fingers + [ix['ik_hand_l']]
left_names = {names[i] for i in left_ids}
idle_path = next(p for p in d['clips'] if p.endswith('_idle'))
idle_raw = np.array(d['clips'][idle_path]['frames'])
cached = pickle.load(open(r / 'current_world.pkl', 'rb'))
out = r / 'Motion'
out.mkdir(exist_ok=True)
profiles = {f: [] for f in d['profiles']}
report, candidate = {}, {}


def rigid(m):
    v = m.copy()
    v[:3, :3] = rot(v)
    return v


def radial(a, e, h):
    axis = unit(h - a)
    return unit(e - a - axis * ((e - a) @ axis))


def sphere(a, b, w):
    angle = np.arccos(np.clip(a @ b, -1., 1.))
    if angle < 1.e-6:
        return a.copy()
    return R.from_rotvec(unit(np.cross(a, b)) * angle * w).apply(a)


def compact(w, times, idle, empty):
    # Release only after the seat/settle contact has finished. Empty reload
    # regains front support before the right hand pulls at source 3.18 s.
    begin, end = 2.76, (3.14 if empty else 3.50)
    start = int(np.searchsorted(times, begin))
    seat = np.linalg.inv(rigid(w[start, ix['WPN_root']])) @ w[start]
    goal = np.linalg.inv(rigid(idle[ix['WPN_root']])) @ idle
    a0, e0, p0 = [seat[ix[n], :3, 3].copy() for n in ('upperarm_l', 'lowerarm_l', 'hand_l')]
    a1, e1, p1 = [goal[ix[n], :3, 3].copy() for n in ('upperarm_l', 'lowerarm_l', 'hand_l')]
    upper, lower = np.linalg.norm(e0-a0), np.linalg.norm(p0-e0)
    bend0, bend1 = radial(a0,e0,p0), radial(a1,e1,p1)
    # The wrist leaves the outside of the magazine, descends beside the
    # receiver and approaches the grip from below. No overhead waypoint.
    control1 = p0 + np.array([7., 0., -5.])
    control2 = np.array([max(p0[0],p1[0])+4., p1[1]-4., p1[2]-2.])
    old_local = encode(w)
    open_frame = int(np.searchsorted(times, 2.95))
    idle_local = encode(idle[None])[0]
    old = w.copy()
    for k in range(start, len(w)):
        tm = times[k]
        gun = rigid(old[k, ix['WPN_root']])
        if tm >= end:
            w[k,left_ids] = gun @ goal[left_ids]
            continue
        q = float(np.clip((tm-begin)/(end-begin),0.,1.))
        u = float(ease(q))
        palm = (1-u)**3*p0 + 3*(1-u)**2*u*control1 + 3*(1-u)*u*u*control2 + u**3*p1
        for i in arm_ids:
            w[k,i] = gun @ mix(seat[i], goal[i], u)
        shoulder = w[k,ix['upperarm_l'],:3,3]
        target = (gun @ np.r_[palm,1.])[:3]
        axis = unit(target-shoulder)
        length = np.linalg.norm(target-shoulder)
        along = (upper*upper-lower*lower+length*length)/(2*length)
        radius = np.sqrt(max(0.,upper*upper-along*along))
        hint = gun[:3,:3] @ sphere(bend0,bend1,u)
        elbow = shoulder + axis*along + unit(hint-axis*(hint@axis))*radius
        ref_upper = gun @ mix(seat[ix['upperarm_l']],goal[ix['upperarm_l']],u)
        ref_elbow = (gun @ np.r_[(1-u)*e0+u*e1,1.])[:3]
        w[k,ix['upperarm_l'],:3,:3] = hinge.swing(ref_elbow-shoulder,elbow-shoulder) @ ref_upper[:3,:3]
        w[k,ix['lowerarm_l'],:3,3] = elbow
        # Turn only after the fingers start letting go, with one shortest arc.
        hand = gun @ mix(seat[ix['hand_l']],goal[ix['hand_l']],float(ease((q-.08)/.86)))
        hand[:3,3] = target
        w[k,ix['hand_l']] = hand
        for i in fingers:
            initial = s['matrix'](old_local[start,i])
            opened = s['matrix'](old_local[open_frame,i])
            final = s['matrix'](idle_local[i])
            local = mix(initial,opened,float(ease(q/.24)))
            local = mix(local,final,float(ease((q-.60)/.40)))
            w[k,i] = w[k,parents[i]] @ local
        w[k,ix['ik_hand_l']] = hand
    # Rebuild the skin-bearing upper-arm and forearm frames as one chain.
    stop = int(np.searchsorted(times,end))+1
    solved, info = hinge.solve(w[start:stop,arm_ids],bind)
    for k in range(start,stop):
        q = float(np.clip((times[k]-begin)/(end-begin),0.,1.))
        gun = rigid(old[k,ix['WPN_root']])
        for j in range(1,7):
            i = arm_ids[j]
            # Fade the solve in/out against the exact seated and idle chain.
            pose = mix(w[k,i],solved[k-start][j],float(ease(q/.14)))
            w[k,i] = mix(pose,gun @ goal[i],float(ease((q-.80)/.20)))
    def travel(a):
        points = np.array([(np.linalg.inv(rigid(fr[ix['WPN_root']])) @ fr[ix['hand_l']])[:3,3] for fr in a[start:]])
        return float(np.linalg.norm(np.diff(points,axis=0),axis=1).sum())
    return w, dict(release_source=begin,grip_source=end,wrist_path_before_cm=travel(old),wrist_path_after_cm=travel(w),forearm_roll_max_deg=float(np.max(abs(info['forearm']))))


for path, clip in d['clips'].items():
    if path == idle_path:
        continue
    raw = np.array(clip['frames'])
    times = np.arange(len(raw))/clip['fps']
    empty = path.split('.')[0].endswith('_empty')
    key = 'side_reload_empty' if empty else 'side_reload'
    base = None
    for family in profiles:
        w = cached[(path,family)]['world'].copy()
        idle = world(layer(idle_raw,idle_path,family,np.array([0.])))[0]
        w, stats = compact(w,times,idle,empty)
        rows = encode(w)
        # Keep all other local tracks and the authored pre-release samples.
        if family == 'base':
            base = raw.copy()
            for i in left_ids:
                base[times>2.76,i] = rows[times>2.76,i]
            with gzip.open(out/(key+'.json.gz'),'wt') as f:
                json.dump(dict(asset=path.split('.')[0],fps=clip['fps'],duration=clip['duration'],tracks={names[i]:base[:,i].tolist() for i in left_ids}),f,separators=(',',':'))
        original = next(c for c in d['profiles'][family]['clips'] if c['base']==path)
        old_tracks = {t['bone']:t for t in original['tracks']}
        delta = [q for q in original['tracks'] if q['bone'] not in left_names]
        for i in left_ids:
            n = names[i]
            v = np.zeros((len(times),10))
            v[:,:3] = rows[:,i,:3]-base[:,i,:3]
            v[:,3:7] = (R.from_quat(rows[:,i,3:7])*R.from_quat(base[:,i,3:7]).inv()).as_quat()
            v[:,7:] = rows[:,i,7:]-base[:,i,7:]
            old_track = old_tracks.get(n)
            prefix_t = np.array(old_track['times']) if old_track else np.array([0.])
            prefix_v = np.array(old_track['values']).reshape(-1,10) if old_track else np.array([[0,0,0,0,0,0,1,0,0,0.]])
            prefix = prefix_t <= 2.76
            tail = times > 2.76
            ts = np.r_[prefix_t[prefix],times[tail]]
            vs = np.concatenate((prefix_v[prefix],v[tail]))
            for k in range(1,len(vs)):
                if vs[k-1,3:7] @ vs[k,3:7] < 0:
                    vs[k,3:7] *= -1
            delta.append(dict(bone=n,times=ts.tolist(),values=vs.ravel().tolist()))
        profiles[family].append(dict(base=path.split('.')[0],duration=clip['duration'],tracks=delta))
        report[key+'_'+family] = stats
        candidate[(path,family)] = dict(times=times,world=w)
        print('M249_RETURN23_AUTHORED',key,family,json.dumps(stats),flush=True)
for family, clips in profiles.items():
    with gzip.open(r/(family+'.json.gz'),'wt') as f:
        json.dump(dict(family=family,clips=clips),f,separators=(',',':'))
(r/'authoring.json').write_text(json.dumps(report,indent=2))
with (r/'candidate_world.pkl').open('wb') as f:
    pickle.dump(candidate,f)
