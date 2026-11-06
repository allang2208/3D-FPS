"""Refit the 52.00–53.60 s chamber. All spatial calculations are in camera metres."""
from pathlib import Path
import math

import numpy as np
from mathutils import Quaternion, Vector


HERE = Path(__file__).resolve().parent
Z = Vector((0, 0, 1))
# Times in the original 60 Hz take, relative to 52.00. The last clearly
# visible leading forearm is at +46. The remaining observations follow the tip.
LANDMARKS = [0, 6, 12, 18, 22, 26, 30, 34, 38, 42, 46, 50, 56, 64, 78, 88, 96]
CLOCK = np.arange(193) * .5


def curve(times, values, clock=CLOCK):
    """Shape-preserving Hermite interpolation with level endpoints."""
    x, y = np.asarray(times, dtype=float), np.asarray(values, dtype=float)
    scalar = y.ndim == 1
    y = y.reshape(len(x), -1)
    slope = np.diff(y, axis=0) / np.diff(x)[:, None]
    tangent = np.zeros_like(y)
    a, b = slope[:-1], slope[1:]
    np.divide(2 * a * b, a + b, out=tangent[1:-1], where=a * b > 0)
    i = np.searchsorted(x[1:-1], clock, side='right')
    dt = (x[i + 1] - x[i])[:, None]
    t = (clock - x[i])[:, None] / dt
    v = ((1 + 2*t)*(1-t)**2*y[i] + t*(1-t)**2*dt*tangent[i]
         + t*t*(3-2*t)*y[i+1] + t*t*(t-1)*dt*tangent[i+1])
    return v[:, 0] if scalar else v


def observed(take, bone, read, times, clock=CLOCK, step=2):
    # Use a small neighbourhood at each measured landmark. Do not interpret a
    # single noisy image solution as a new elbow or crossguard orientation.
    values = []
    for t in times:
        if t in (0, times[-1]):
            values.append(read(take[2*t][bone]))
            continue
        samples = [read(take[max(0, min(len(take)-1, 2*t+j*step))][bone]) for j in (-2,-1,0,1,2)]
        values.append(np.average(samples, axis=0, weights=[1,3,4,3,1]))
    return curve(times, values, clock)


def transport(directions):
    rotations = [Quaternion()]
    for previous, current in zip(directions, directions[1:]):
        rotations.append((previous.rotation_difference(current) @ rotations[-1]).normalized())
    return rotations


def plane(v, axis):
    return (v - axis*v.dot(axis)).normalized()


def bearing(axis, a, b):
    return math.atan2(axis.dot(a.cross(b)), a.dot(b))


def weapon_track(A, idle, take, end_spins):
    start, end = idle['WPN_root'], take[-1]['WPN_root']
    positions = observed(take, 'WPN_root', lambda m: tuple(m.translation), LANDMARKS)
    directions = observed(take, 'WPN_root', lambda m: tuple(m.to_quaternion() @ Z), LANDMARKS)
    neutral = start.to_quaternion() @ Z
    entry = [A.smooth(t / 13.) for t in CLOCK]
    shaft = [neutral.lerp(Vector(v), w).normalized() for v, w in zip(directions, entry)]
    carried = [q @ start.to_quaternion() for q in transport(shaft)]
    end_roll = A.axis_angle(end.to_quaternion() @ carried[-1].inverted(), shaft[-1])
    # Crossguard banking, independent of blade direction through vertical.
    # The partially obscured back quillon at +18..26 must not reverse the palms.
    bank = curve([0, 8, 15, 21, 31, 44, 62, 80, 96],
                 np.radians([0,-38,-72,-72,-57,-49,-53,-47,math.degrees(end_roll)]))
    weapons = [A.mat(start.translation.lerp(Vector(p), w),
                     Quaternion(axis, angle) @ base, start.to_scale())
               for p,w,axis,angle,base in zip(positions,entry,shaft,bank,carried)]
    weapons[0], weapons[-1] = start, end
    # Both palms follow the same handle turn while the blade is upright.
    # The small grip-specific adjustment settles into the actual release pose.
    wrists = [curve([0,8,16,24,40,62,96],
                    np.radians([0,19,39,40,34,math.degrees(s),math.degrees(s)]))
              for s in end_spins]
    return weapons, wrists


def elbow_path(A, idle, take, poses, side, progress, guides, clock=CLOCK,
               shoulder_keys=(0,12,24,38,50,68,96), neutral=None):
    u, l, h = [k+'_'+side for k in ('upperarm','lowerarm','hand')]
    end = take[-1]
    s0,e0,h0 = [idle[n].translation for n in (u,l,h)]
    s1,e1,h1 = [end[n].translation for n in (u,l,h)]
    upper, fore = (e0-s0).length, (h0-e0).length
    max_reach = math.sqrt(upper**2+fore**2+2*upper*fore*math.cos(math.radians(32)))
    min_reach = math.sqrt(upper**2+fore**2+2*upper*fore*math.cos(math.radians(137)))
    neutral = idle if neutral is None else neutral
    neutral_fore = (neutral[h].translation-neutral[l].translation).normalized()
    neutral_palm = ((neutral['middle_01_'+side].translation+neutral['ring_01_'+side].translation)*.5
                    - neutral[h].translation).normalized()
    fitted = observed(take, u, lambda m: tuple(m.translation), shoulder_keys, clock)
    duration = clock[-1]
    down = Vector((0,-math.sin(math.radians(41)),-math.cos(math.radians(41))))
    shoulders, axes, centres, radii = [], [], [], []
    for i,(p,t,w) in enumerate(zip(poses,clock,progress)):
        hand = p[h].translation
        shoulder = s0.lerp(s1,w).lerp(Vector(fitted[i]), .40*A.smooth(t/8)*A.smooth((duration-t)/15))
        # Keep the support shoulder under the wide camera and reachable without
        # straightening the elbow. Project onto the intersection if necessary.
        clearance = min(.113, down.dot(s0), down.dot(s1))
        if side == 'l':
            shoulder += down*max(0.,clearance-down.dot(shoulder))
        reach = hand-shoulder
        shoulder = hand-reach.normalized()*max(min_reach,min(max_reach,reach.length))
        if side=='l' and down.dot(shoulder)<clearance:
            height = clearance-down.dot(hand)
            centre = hand+height*down
            v = shoulder-centre
            tangent = v-down*v.dot(down)
            shoulder = centre+tangent.normalized()*min(tangent.length,math.sqrt(max(0.,max_reach**2-height**2)))
        if i in (0,len(poses)-1):
            shoulder = s0 if i==0 else s1
        reach = hand-shoulder
        axis = reach.normalized()
        along = (upper**2-fore**2+reach.length_squared)/(2*reach.length)
        shoulders.append(shoulder)
        axes.append(axis)
        centres.append(shoulder+axis*along)
        radii.append(math.sqrt(max(0.,upper**2-along**2)))

    radial = plane(e0-centres[0], axes[0])
    carried = [q @ radial for q in transport(axes)]
    swivel_end = bearing(axes[-1],carried[-1],plane(e1-centres[-1],axes[-1]))
    poles = [Quaternion(axis,swivel_end*w) @ pole for axis,w,pole in zip(axes,progress,carried)]

    # Fit only the visible forearm tangent. Depth and camera-edge occlusion
    # leave two plausible elbows; choose one continuous path over the take.
    degrees = np.arange(-64.,65.,2.)
    angle = np.radians(degrees)
    motion_cost = 4.*(degrees[:,None]-degrees[None,:])**2
    zero = len(angle)//2
    cost = np.full(len(angle), np.inf)
    cost[zero] = 0.
    parents = []
    def project(p):
        return p[..., [0,2]] * np.array([1.,-1.]) / np.maximum(p[...,1:2],.025)
    for i in range(1,len(poses)):
        p = poses[i]
        hand = np.array(p[h].translation)
        pole = np.asarray(poles[i])
        quarter = np.asarray(axes[i].cross(poles[i]))
        choices = np.array(centres[i])+radii[i]*(np.cos(angle)[:,None]*pole+np.sin(angle)[:,None]*quarter)
        visible = project(choices)-project(hand)
        visible /= np.maximum(np.linalg.norm(visible,axis=1)[:,None],1.e-8)
        desired = guides[i,2:4]-guides[i,:2]
        desired /= max(1.e-8,np.linalg.norm(desired))
        silhouette = np.degrees(np.arccos(np.clip(visible @ desired,-1.,1.)))
        carry = p[h].to_quaternion() @ neutral[h].to_quaternion().inverted()
        natural = carry @ neutral_fore
        forearms = hand-choices
        wrist = np.degrees(np.arccos(np.clip((forearms @ np.array(natural))/np.linalg.norm(forearms,axis=1),-1.,1.)))
        flex = np.degrees(np.arccos(np.clip((forearms @ np.array(carry @ neutral_palm))/np.linalg.norm(forearms,axis=1),-1.,1.)))
        options = cost[:,None]+motion_cost
        parents.append(options.argmin(axis=0))
        cost = (options.min(axis=0)+.14*degrees**2
                +guides[i,4]*.24*silhouette**2+1.5*np.maximum(wrist-32.,0.)**2
                +3.*np.maximum(flex-35.,0.)**2)
    index = zero
    path = [angle[index]]
    for parent in reversed(parents):
        index = parent[index]
        path.append(angle[index])
    filtered = np.convolve(path[::-1],np.array([1,2,3,4,3,2,1])/16.,mode='same')
    elbows = [c+r*(Quaternion(axis,a*A.smooth(t/7)*A.smooth((duration-t)/9)) @ pole)
              for c,r,axis,a,t,pole in zip(centres,radii,axes,filtered,clock,poles)]
    elbows[0], elbows[-1] = e0,e1
    return shoulders, elbows


def skin_arm(A, idle, end, poses, side, progress, shoulders, elbows):
    hand = 'hand_'+side
    hands = [p[hand].translation for p in poses]
    upper_axes = [(e-s).normalized() for e,s in zip(elbows,shoulders)]
    fore_axes = [(h-e).normalized() for h,e in zip(hands,elbows)]
    upper_frames = transport(upper_axes)
    fore_frames = transport(fore_axes)
    # Measure palm rotation about the moving forearm without an Euler angle or
    # a projected elbow normal. Twist stations share the temporary pronation.
    twist = []
    for pose,axis,base in zip(poses,fore_axes,fore_frames):
        delta = pose[hand].to_quaternion() @ idle[hand].to_quaternion().inverted()
        aligned = (delta @ fore_axes[0]).rotation_difference(axis) @ delta
        twist.append(A.near_angle(A.axis_angle(aligned @ base.inverted(),axis),twist[-1] if twist else 0.))
    upper = [('clavicle',0.),('upperarm_twist_01',.06),('upperarm_twist_02',.14),('upperarm',.20)]
    fore = [('lowerarm',.23),('lowerarm_twist_02',.48),('lowerarm_twist_01',.84)]
    for stations,origins,axes,bases in [(upper,shoulders,upper_axes,upper_frames),(fore,elbows,fore_axes,fore_frames)]:
        for stem,share in stations:
            n = stem+'_'+side
            first, last = idle[n], end[n]
            start_offset = first.translation-origins[0]
            end_offset = bases[-1].inverted() @ (last.translation-origins[-1])
            finish = bases[-1].inverted() @ last.to_quaternion()
            for i,(pose,w,origin,axis,base) in enumerate(zip(poses,progress,origins,axes,bases)):
                extra = share*(twist[i]-twist[-1]*w)
                turn = Quaternion(axis,extra) @ base
                pose[n] = A.mat(origin+turn @ start_offset.lerp(end_offset,w),
                                turn @ first.to_quaternion().slerp(finish,w),first.to_scale())


def support_wrist(A, neutral, poses, side, shoulders, elbows, strike=None):
    # Work in palm space: an energetic forward thrust translates the fist
    # quickly but does not require throwing the elbow across the wrist.
    u,l,h = [n+'_'+side for n in ('upperarm','lowerarm','hand')]
    palm = neutral[h].to_quaternion().inverted() @ (
        (neutral['middle_01_'+side].translation+neutral['ring_01_'+side].translation)*.5
        -neutral[h].translation).normalized()
    upper_length = (neutral[u].translation-neutral[l].translation).length
    fore_length = (neutral[h].translation-neutral[l].translation).length
    fore,upper = [],[]
    for p,s,e in zip(poses,shoulders,elbows):
        wrist_inv = p[h].to_quaternion().inverted()
        fore.append(wrist_inv @ (p[h].translation-e).normalized())
        upper.append(wrist_inv @ (e-s).normalized())
    down = Vector((0,-math.sin(math.radians(41)),-math.cos(math.radians(41))))
    clearance = min(.113,down.dot(shoulders[0]),down.dot(shoulders[-1]))
    def limit(v,axis,max_angle):
        angle = axis.angle(v)
        if angle<=max_angle:
            return v
        return math.cos(max_angle)*axis+math.sin(max_angle)*plane(v,axis)
    def filtered(values,i):
        return sum((values[max(0,min(len(values)-1,i+j))]*weight for j,weight in
                    zip(range(-6,7),(1,2,3,4,5,6,7,6,5,4,3,2,1))),Vector()).normalized()
    if strike is not None:
        take,clock = strike
        # At these source frames both grip and sleeve are identifiable. Read
        # the limb directions in *that same palm frame*, so turning the hilt
        # never pulls the wrist away from its supported forearm.
        landmarks = (0,7,10,14,18,24,62)
        def limb_keys(parent,child):
            keys = []
            for t in landmarks:
                p=take[t*2]
                keys.append(tuple(p[h].to_quaternion().inverted() @
                                  (p[child].translation-p[parent].translation).normalized()))
            return [Vector(v).normalized() for v in curve(landmarks,keys,clock)]
        source_fore,source_upper=limb_keys(l,h),limb_keys(u,l)
    fore_path,upper_path=[],[]
    for i in range(1,len(poses)-1):
        blend = A.smooth(i/10.)*A.smooth((len(poses)-1-i)/10.)
        hand = poses[i][h]
        fore_guide = filtered(fore,i)
        f = limit(fore_guide,palm,math.radians(36))
        f = hand.to_quaternion() @ fore[i].lerp(f,blend).normalized()
        base_f = hand.to_quaternion() @ fore[i].lerp(fore_guide,blend).normalized()
        upper_dir = base_f.rotation_difference(f) @ (hand.to_quaternion() @
            upper[i].lerp(filtered(upper,i),blend).normalized())
        if strike is not None:
            visibility = A.smooth(clock[i]/6.)*A.smooth((26.-clock[i])/10.)
            f=f.lerp(hand.to_quaternion() @ source_fore[i],visibility).normalized()
            upper_dir=upper_dir.lerp(hand.to_quaternion() @ source_upper[i],visibility).normalized()
        fore_path.append(hand.to_quaternion().inverted() @ f)
        upper_path.append(hand.to_quaternion().inverted() @ upper_dir)
    fore_path=[fore[0],*fore_path,fore[-1]]
    upper_path=[upper[0],*upper_path,upper[-1]]
    for i in range(1,len(poses)-1):
        hand=poses[i][h]
        weight=A.smooth(i/7.)*A.smooth((len(poses)-1-i)/7.)
        f=hand.to_quaternion() @ fore_path[i].lerp(filtered(fore_path,i),weight).normalized()
        upper_dir=hand.to_quaternion() @ upper_path[i].lerp(filtered(upper_path,i),weight).normalized()
        e=hand.translation-fore_length*f
        if side=='l':
            # Keep the cut end below the wide first-person camera without
            # moving the palm or undoing the wrist correction.
            bound = max(-1.,min(1.,(down.dot(e)-clearance)/upper_length))
            if upper_dir.dot(down)>bound:
                upper_dir = bound*down+math.sqrt(1.-bound**2)*plane(upper_dir,down)
        elbows[i],shoulders[i] = e,e-upper_length*upper_dir
    if strike is not None:
        # A nearly straight arm does not identify a reliable elbow plane.
        # Keep the elbow and hand on the observed line, and carry the shoulder
        # around it between the two adjacent, clearly flexed poses.
        axes=[(p[h].translation-e).normalized() for p,e in zip(poses,elbows)]
        upper_axes=[(e-s).normalized() for e,s in zip(elbows,shoulders)]
        bends=[a.angle(b) for a,b in zip(axes,upper_axes)]
        poles=[plane(b,a) for a,b in zip(axes,upper_axes)]
        carried=transport(axes)
        good=[0]+[i for i in range(1,len(poses)-1) if bends[i]>=math.radians(27)]+[len(poses)-1]
        for first,last in zip(good,good[1:]):
            if last-first<=1:
                continue
            base=carried[first].inverted() @ poles[first]
            target=carried[last].inverted() @ poles[last]
            roll=bearing(axes[0],base,target)
            for i in range(first+1,last):
                t=A.smooth((i-first)/(last-first))
                pole=carried[i] @ (Quaternion(axes[0],t*roll) @ base)
                bend=max(math.radians(19.),bends[i])
                upper=math.cos(bend)*axes[i]+math.sin(bend)*pole
                shoulders[i]=elbows[i]-upper_length*upper


def grip_poses(A, idle, weapons, spins):
    poses = []
    for i,weapon in enumerate(weapons):
        pose = dict(idle)
        move = weapon @ idle['WPN_root'].inverted()
        for n in A.descendants('WPN_root') | {'ik_hand_gun'}:
            pose[n] = move @ idle[n]
        for s,side in enumerate(('r','l')):
            turn = Quaternion(Z,spins[s][i]).to_matrix().to_4x4()
            grip = weapon @ turn @ idle['WPN_root'].inverted()
            for n in A.HANDS[side] | {'ik_hand_'+side}:
                pose[n] = grip @ idle[n]
        poses.append(pose)
    return poses


def build_charge(A, idle, take, end_spins):
    weapons, spins = weapon_track(A,idle,take,end_spins)
    poses = grip_poses(A,idle,weapons,spins)
    progress = curve([0,12,23,40,56,78,96],[0,.09,.24,.63,.82,.94,1.])
    source = np.loadtxt(HERE/'Review/forearms.txt')
    keys = (source[:,0]>=3120) & (source[:,0]<=3208)
    times = list(source[keys,0]-3120)+[96]
    for s,side in enumerate(('r','l')):
        columns = [1+s*4,2+s*4,3+s*4,4+s*4,9+s]
        data = source[keys][:,columns]
        guides = curve(times, np.vstack((data,data[-1])))
        shoulders, elbows = elbow_path(A,idle,take,poses,side,progress,guides)
        support_wrist(A,idle,poses,side,shoulders,elbows)
        skin_arm(A,idle,take[-1],poses,side,progress,shoulders,elbows)
    poses[0], poses[-1] = idle, take[-1]
    return poses


def build_release(A, idle, take, start_spins):
    clock = np.arange(len(take))*.5
    start, finish = take[0]['WPN_root'], idle['WPN_root']
    landmarks = [0,2,4,6,8,10,12,16,21,26,34,41,48,55,62]
    position = observed(take,'WPN_root',lambda m:tuple(m.translation),landmarks,clock,1)
    directions = observed(take,'WPN_root',lambda m:tuple(m.to_quaternion() @ Z),landmarks,clock,1)
    shaft = [Vector(v).normalized() for v in directions]
    carried = [q @ start.to_quaternion() for q in transport(shaft)]
    final_bank = A.axis_angle(finish.to_quaternion() @ carried[-1].inverted(),shaft[-1])
    # Both hands remain on the same face of the handle during the lunge.
    # Follow the visible quillons in the strike. Once they leave the bottom
    # of the image, unwind directly to idle rather than fitting their back face.
    bank = curve([0,4,8,14,23,40,62],np.radians([0,24,53,60,63,65,math.degrees(final_bank)]),clock)
    weapons = [A.mat(p,Quaternion(axis,a) @ frame,start.to_scale())
               for p,axis,a,frame in zip(position,shaft,bank,carried)]
    weapons[0],weapons[-1] = start,finish
    spins = []
    for side,s in zip(('r','l'),start_spins):
        h='hand_'+side
        neutral=idle['WPN_root'].to_quaternion().inverted() @ idle[h].to_quaternion()
        def grasp(t):
            p=take[t*2]
            rel=p['WPN_root'].to_quaternion().inverted() @ p[h].to_quaternion()
            return A.axis_angle(rel @ neutral.inverted(),Z)
        spins.append(curve([0,8,12,18,34,50,62],[s,grasp(8),grasp(12),grasp(18),s*.27,s*.06,0.],clock))
    poses = grip_poses(A,idle,weapons,spins)
    progress = curve([0,8,18,36,53,62],[0,.12,.25,.61,.94,1.],clock)
    source = np.loadtxt(HERE/'Review/forearms.txt')
    source = source[source[:,0]>=3218]
    times = np.r_[0,source[:,0]-3216]
    for s,side in enumerate(('r','l')):
        data = source[:,[1+s*4,2+s*4,3+s*4,4+s*4,9+s]]
        guides = curve(times,np.vstack((data[0],data)),clock)
        shoulders,elbows = elbow_path(A,take[0],take,poses,side,progress,guides,clock,
                                      (0,4,8,14,22,35,48,62),idle)
        support_wrist(A,idle,poses,side,shoulders,elbows,(take,clock))
        skin_arm(A,take[0],idle,poses,side,progress,shoulders,elbows)
    poses[0],poses[-1] = take[0],idle
    return poses


def build_short_entry(A, idle, charged, end_spins):
    # A direct attack has 40 keys before the shared release. Use one draw to
    # chamber instead of accelerating the entire 1.6 s charge into that window.
    amount = [A.smooth(i/40.) for i in range(41)]
    start, end = idle['WPN_root'], charged['WPN_root']
    weapons = [A.mat(start.translation.lerp(end.translation,t),
                     start.to_quaternion().slerp(end.to_quaternion(),t),start.to_scale()) for t in amount]
    poses = grip_poses(A,idle,weapons,[[s*t for t in amount] for s in end_spins])
    for side in ('r','l'):
        u,l,h = [n+'_'+side for n in ('upperarm','lowerarm','hand')]
        neutral = [idle[n].translation for n in (u,l,h)]
        upper,fore = (neutral[1]-neutral[0]).length,(neutral[2]-neutral[1]).length
        reach_limit = math.sqrt(upper**2+fore**2+2*upper*fore*math.cos(math.radians(30)))
        shoulders,axes,centres,radii = [],[],[],[]
        for t,p in zip(amount,poses):
            shoulder = neutral[0].lerp(charged[u].translation,t)
            hand = p[h].translation
            delta = hand-shoulder
            axis = delta.normalized()
            reach = min(delta.length,reach_limit)
            shoulder = hand-axis*reach
            along = (upper**2-fore**2+reach**2)/(2*reach)
            shoulders.append(shoulder);axes.append(axis)
            centres.append(shoulder+axis*along);radii.append(math.sqrt(max(0.,upper**2-along**2)))
        base = plane(neutral[1]-centres[0],axes[0])
        poles = [q @ base for q in transport(axes)]
        turn = bearing(axes[-1],poles[-1],plane(charged[l].translation-centres[-1],axes[-1]))
        elbows = [c+r*(Quaternion(axis,turn*t) @ v) for c,r,axis,t,v in zip(centres,radii,axes,amount,poles)]
        support_wrist(A,idle,poses,side,shoulders,elbows)
        skin_arm(A,idle,charged,poses,side,amount,shoulders,elbows)
    poses[0],poses[-1] = idle,charged
    return poses
