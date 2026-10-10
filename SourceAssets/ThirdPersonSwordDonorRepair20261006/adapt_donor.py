"""Trim actual UAL2 full-body takes and fit Jason's held sword to the cut.

The donor supplies the body, main-hand arc and elbow planes. Only equipment
grip, blade roll, support-arm reach and transition to the existing idle are
adapted. No hand-written pelvis, footstep or attack trajectory is substituted.
"""
import json
import math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
base = json.loads((OUT.parent/'ThirdPersonSwordActions20261006/authoring-input.json').read_text())
donors = json.loads((OUT/'retargeted-poses.json').read_text())
original = json.loads((OUT/'original-poses.json').read_text())
source_ix = {n:i for i,n in enumerate(original['names'])}
source_ref = np.array(original['reference'])
names, parents = base['names'], base['parents']
ix = {n:i for i,n in enumerate(names)}
ref = np.array(base['reference'])

def unit(v):
    return np.asarray(v)/max(np.linalg.norm(v), 1e-10)

def rot(q, v):
    return R.from_quat(q).apply(v)

def mul(a, b):
    return (R.from_quat(a)*R.from_quat(b)).as_quat()

def inv(q):
    return R.from_quat(q).inv().as_quat()

def axis(v, angle):
    return R.from_rotvec(unit(v)*angle).as_quat()

def compose(a, b):
    return np.r_[a[:3]+rot(a[3:7], b[:3]), mul(a[3:7], b[3:7])]

def inverse(t):
    q = inv(t[3:7])
    return np.r_[rot(q, -t[:3]), q]

def frame_xy(x, y):
    x = unit(x)
    y = unit(y-x*np.dot(x,y))
    return R.from_matrix(np.column_stack((x, y, np.cross(x,y)))).as_quat()

def fk(f):
    w = f.copy()
    for i,p in enumerate(parents):
        if p >= 0:
            w[i,:3] = w[p,:3]+rot(w[p,3:7],f[i,:3]*w[p,7:])
            w[i,3:7] = mul(w[p,3:7],f[i,3:7])
            w[i,7:] = w[p,7:]*f[i,7:]
    return w

def slerp(a,b,t):
    # Shortest-arc interpolation, vectorized over every bone in a pose.
    b = np.where(np.sum(a*b,axis=-1,keepdims=True)<0,-b,b)
    cosine = np.clip(np.sum(a*b,axis=-1,keepdims=True),-1.,1.)
    theta = np.arccos(cosine)
    sine = np.sin(theta)
    safe = np.where(sine<1e-6,1.,sine)
    q = np.where(sine<1e-6,a*(1-t)+b*t,
                 (a*np.sin((1-t)*theta)+b*np.sin(t*theta))/safe)
    return q/np.linalg.norm(q,axis=-1,keepdims=True)

def blend(a,b,t):
    f = a*(1-t)+b*t
    f[:,3:7] = slerp(a[:,3:7],b[:,3:7],t)
    return f

def smooth(t):
    t = np.clip(t,0.,1.)
    return t*t*(3-2*t)

def sample(clip,t):
    frames = np.asarray(clip['frames'])
    p = np.clip(t/clip['duration']*(len(frames)-1),0,len(frames)-1)
    a = int(p); b = min(a+1,len(frames)-1)
    return blend(frames[a],frames[b],p-a)

bind = fk(ref)
def mount(side):
    points = []
    for skeleton in (base['equipment']['reference'],{n:bind[i] for i,n in enumerate(names)}):
        hand = np.array(skeleton['hand_'+side])
        points.append(np.array([rot(inv(hand[3:7]),np.array(skeleton[d+'_01_'+side])[:3]-hand[:3]) for d in ('index','middle','pinky')]))
    a,b = points
    q = mul(frame_xy(b[1],b[0]-b[2]), inv(frame_xy(a[1],a[0]-a[2])))
    return np.r_[b.mean(axis=0)-rot(q,a.mean(axis=0)),q]

native = base['equipment']['pose']
grips = {s:compose(inverse(np.array(native['WPN_root'])[:7]),compose(np.array(native['hand_'+s])[:7],inverse(mount(s)))) for s in ('r','l')}
hand_to_weapon = inverse(grips['r'])

def weapon(f):
    return compose(fk(f)[ix['hand_r'],:7],hand_to_weapon)

def set_world_q(f,b,q,w):
    p = parents[b]
    f[b,3:7] = mul(inv(w[p,3:7]),q) if p>=0 else q

def source_palm_mount(side):
    points = []
    for w,lookup in ((source_ref,source_ix),(bind,ix)):
        h = w[lookup['hand_'+side]]
        points.append(np.array([rot(inv(h[3:7]),w[lookup[d+'_01_'+side],:3]-h[:3]) for d in ('index','middle','pinky')]))
    a,b = points
    return mul(frame_xy(b[1],b[0]-b[2]),inv(frame_xy(a[1],a[0]-a[2])))

source_mount = {s:source_palm_mount(s) for s in ('r','l')}
body_clip = next(c for n,c in donors['clips'].items() if n.endswith('Sword_Heavy_Combo'))
source_clip = next(c for n,c in original['clips'].items() if n.endswith('Sword_Heavy_Combo'))
idle = np.array(base['clips']['idle']['frames'][0])
idle_world = fk(idle)

def two_bone(f,side,target,pole):
    """Fit fixed-length Jason arms using the donor's actual bend direction."""
    a,b,c = [ix[k+'_'+side] for k in ('upperarm','lowerarm','hand')]
    w = fk(f)
    origin = w[a,:3]
    l1,l2 = np.linalg.norm(ref[b,:3]),np.linalg.norm(ref[c,:3])
    direction = unit(target[:3]-origin)
    distance = np.clip(np.linalg.norm(target[:3]-origin),abs(l1-l2)+.01,(l1+l2)*.965)
    endpoint = origin+direction*distance
    bend = unit(pole-direction*np.dot(pole,direction))
    along = (l1*l1-l2*l2+distance*distance)/(2*distance)
    elbow = origin+direction*along+bend*math.sqrt(max(0,l1*l1-along*along))
    normal = unit(np.cross(elbow-origin,endpoint-elbow))
    old1,old2 = bind[b,:3]-bind[a,:3],bind[c,:3]-bind[b,:3]
    old_normal = unit(np.cross(old1,old2))
    for bone,old,new in ((a,old1,elbow-origin),(b,old2,endpoint-elbow)):
        desired = mul(mul(frame_xy(new,normal),inv(frame_xy(old,old_normal))),bind[bone,3:7])
        set_world_q(f,bone,desired,fk(f))
    # Let forearm pronation carry most of the grip roll. The remaining wrist
    # articulation follows the donor instead of concentrating a 90-degree
    # blade correction at the hand joint.
    w = fk(f)
    neutral = mul(w[b,3:7],ref[c,3:7])
    difference = mul(target[3:7],inv(neutral))
    if difference[3]<0:
        difference *= -1
    forearm = unit(endpoint-elbow)
    twist = 2*math.atan2(np.dot(difference[:3],forearm),difference[3])
    set_world_q(f,b,mul(axis(forearm,twist*.8),w[b,3:7]),w)
    set_world_q(f,c,target[3:7],fk(f))

def main_hand(f,source):
    """Retain the original main-arm ray, correcting A/T-pose retarget offsets."""
    w = fk(f)
    a,b,c = [source_ix[k+'_r'] for k in ('upperarm','lowerarm','hand')]
    length = sum(np.linalg.norm(ref[ix[k+'_r'],:3]) for k in ('lowerarm','hand'))
    donor_length = np.linalg.norm(source[b,:3]-source[a,:3])+np.linalg.norm(source[c,:3]-source[b,:3])
    point = w[ix['upperarm_r'],:3]+(source[c,:3]-source[a,:3])*length/donor_length
    q = mul(source[c,3:7],inv(source_mount['r']))
    return np.r_[point,q]

def coupled_fit(f,right,poles):
    wp = compose(right,hand_to_weapon)
    targets = {s:compose(wp,grips[s]) for s in ('r','l')}
    w = fk(f)
    shift = np.zeros(3)
    for _ in range(12):
        for s in ('r','l'):
            center = w[ix['upperarm_'+s],:3]
            radius = .963*sum(np.linalg.norm(ref[ix[k+'_'+s],:3]) for k in ('lowerarm','hand'))
            v = targets[s][:3]+shift-center
            if np.linalg.norm(v)>radius:
                shift -= unit(v)*(np.linalg.norm(v)-radius)
    for s in ('r','l'):
        target = targets[s].copy()
        target[:3] += shift
        two_bone(f,s,target,poles[s])
    return f

def donor_frame(time):
    f = sample(body_clip,time)
    # Retarget rotations carry torso and legs. Preserve Jason's bone lengths,
    # neck offsets and scale; only the retargeted pelvis has translation keys.
    hip = f[ix['pelvis'],:3].copy()
    f[:,:3] = ref[:,:3]
    f[:,7:] = ref[:,7:]
    f[ix['pelvis'],:3] = hip
    f[ix['root']] = ref[ix['root']]
    source = sample(source_clip,time)
    poles = {s:unit(source[source_ix['lowerarm_'+s],:3]-source[source_ix['upperarm_'+s],:3]) for s in ('r','l')}
    right = main_hand(f,source)
    return f,right,poles

def author(label,schedule,contact,release,recovery):
    count = round(schedule[-1][0]*30)+1
    times = np.arange(count)/30
    contact_frame,release_frame = round(contact*30),round(release*30)
    raw = []
    for t in times:
        source_time = np.interp(t,[p[0] for p in schedule],[p[1] for p in schedule])
        f,right,poles = donor_frame(source_time)
        # Enter and leave through the already-used two-hand idle. The actual
        # cut, weight shift and source recovery remain unblended donor motion.
        weight = smooth(t/.20)*(1-smooth((t-recovery)/(times[-1]-recovery)))
        f = blend(idle,f,weight)
        right = np.r_[idle_world[ix['hand_r'],:3]*(1-weight)+right[:3]*weight,
                      slerp(idle_world[ix['hand_r'],3:7],right[3:7],weight)]
        for s in ('r','l'):
            idle_pole = unit(idle_world[ix['lowerarm_'+s],:3]-idle_world[ix['upperarm_'+s],:3])
            poles[s] = unit(idle_pole*(1-weight)+poles[s]*weight)
        raw.append((f,right,poles))

    weapons = [compose(right,hand_to_weapon) for _,right,_ in raw]
    tips = np.array([p[:3]+rot(p[3:7],[0,0,80]) for p in weapons])
    velocity = np.gradient(tips,1/30,axis=0)
    active = range(contact_frame,release_frame+1)
    rolls = []
    for i in active:
        v = rot(inv(weapons[i][3:7]),velocity[i])
        # +Z follows the length, +/-X are the two edges, Y is thickness.
        # -X is the single cutting edge on the TangDao blade family as well.
        rolls.append(math.atan2(-v[1],-v[0]))
    rolls = np.unwrap(rolls)
    rolls -= round(rolls[0]/(2*math.pi))*2*math.pi
    frames = []
    for i,(f,right,poles) in enumerate(raw):
        if i<contact_frame:
            roll = rolls[0]*smooth(times[i]/contact)
        elif i>release_frame:
            roll = rolls[-1]*(1-smooth((times[i]-release)/(times[-1]-release)))
        else:
            roll = rolls[i-contact_frame]
        wp = weapons[i].copy()
        wp[3:7] = mul(wp[3:7],axis([0,0,1],roll))
        corrected = compose(wp,grips['r'])
        # Axial blade alignment may alter a rigid wrist offset. Keep the
        # source wrist trajectory and let the entire weapon follow that wrist.
        corrected[:3] = right[:3]
        frames.append(coupled_fit(f,corrected,poles))
    frames = np.array(frames)
    for i in range(1,len(frames)):
        flip = np.sum(frames[i-1,:,3:7]*frames[i,:,3:7],axis=1)<0
        frames[i,flip,3:7] *= -1
    return dict(rate=30,contact=contact_frame/(count-1),release=release_frame/(count-1),
                source_take=source_clip['asset'],source_schedule=schedule,
                blade_roll_degrees=np.degrees(rolls).tolist(),frames=frames.tolist())

def main():
    clips = {
        # Heavy Combo's genuine rising cut: the blade trails the lifting wrist
        # then travels up in front at 1.10-1.15; do not mistake wrist lift for
        # the actual edge/contact interval or reverse a downward attack.
        'Uppercut':author('Uppercut',[(0,.96),(.25,.99),(1.,1.10),(1.1333333,1.15),(1.30,1.17),(2.0333333,1.17)],1.,1.1333333,1.30),
        'Overhead':author('Overhead',[(0,2.23),(.7,2.50),(.9,2.58),(1.10,2.67),(1.25,2.83),(1.65,3.55),(2.0333333,4.30)],.9,1.10,1.65),
        'DashOverhead':author('DashOverhead',[(0,2.40),(.20,2.53),(.2666667,2.58),(.4666667,2.67),(.60,2.83),(1.20,3.55),(1.6333333,4.30)],.2666667,.4666667,1.20),
    }
    result = dict(mesh=base['mesh'],skeleton=base['skeleton'],names=names,clips=clips,
        provenance='Quaternius UAL2 Standard CC0 Sword_Heavy_Combo actual body tracks; Jason arm/palm retarget, two-hand support and cutting-edge alignment',
        source_url='https://quaternius.itch.io/universal-animation-library-2',
        reference_url='https://quaternius.com/packs/universalanimationlibrary2.html')
    (OUT/'adapted-actions.json').write_text(json.dumps(result,separators=(',',':')),encoding='utf-8')
    print('UAL2_SWORD_ADAPTED '+json.dumps({n:dict(keys=len(c['frames']),source=c['source_take']) for n,c in clips.items()}))

if __name__ == '__main__':
    main()
