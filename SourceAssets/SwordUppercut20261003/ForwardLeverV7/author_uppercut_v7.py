"""User video: left pommel, right guard; two-hand forward rising cut."""
import bisect
import json
import math
from pathlib import Path
import bpy
from mathutils import Matrix, Quaternion, Vector

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
DATA = json.loads((P/'inputs.json').read_text('utf-8'))
SOURCE = ROOT/'SourceAssets/ModularOutfit20260925/BarePalmV7/Editable/RuneSword_BareArmsV7.blend'
FPS, END = 120, 1.70
FRAMES = round(FPS*END)
END = FRAMES/FPS
C = Matrix.Diagonal(Vector((1,-1,1)))
NAMES = list(DATA['parents'])
PARENTS = DATA['parents']

def mat(p,q,s=(1,1,1)):
    return Matrix.LocRotScale(Vector(p),q,Vector(s))

def native(row):
    return mat(row['p'],Quaternion(row['q']),row['s'])

def canonical(m):
    p,q,s = m.decompose()
    return mat(C@p*.01,(C@q.to_matrix()@C).to_quaternion(),s)

def localize(world):
    return {n:world[PARENTS[n]].inverted()@world[n] if PARENTS[n] in world else world[n] for n in NAMES}

def globalize(local):
    world = {}
    def get(n):
        if n not in world:
            parent = PARENTS[n]
            world[n] = get(parent)@local[n] if parent in local else local[n].copy()
        return world[n]
    for n in NAMES:get(n)
    return world

def blend(a,b,u):
    pa,qa,sa = a.decompose()
    pb,qb,sb = b.decompose()
    return mat(pa.lerp(pb,u),qa.slerp(qb,u),sa.lerp(sb,u))

def smooth(x):
    x = max(0.,min(1.,x))
    return x*x*x*(10+x*(-15+6*x))

def delta(track,t):
    times,values = track['times'],track['values']
    k = max(0,min(len(times)-1,bisect.bisect_right(times,t)-1))
    j = min(len(times)-1,k+1)
    u = max(0.,min(1.,(t-times[k])/(times[j]-times[k]))) if j!=k else 0.
    def key(i):
        v = values[10*i:10*i+10]
        return Vector(v[:3]),Quaternion((v[6],v[3],v[4],v[5])),Vector(v[7:])
    a,b = key(k),key(j)
    return a[0].lerp(b[0],u),a[1].slerp(b[1],u),a[2].lerp(b[2],u)

def role_profile(role):
    return next((e for e in DATA.get('long_grip_profile',{}).get('clips',[])
                 if e['base'].split('.')[-1].endswith('_'+role)),None)

def live_source(variant,role,index=0):
    """Use the same base + authored deltas currently consumed by LongGrip."""
    profile = role_profile(role) if variant=='LongGrip' else None
    use_profile = profile and not profile['retained']
    e = DATA['variants']['Standard' if use_profile else variant]
    rows = e['samples'] if role=='Thrust' else (e['slashes'][role]['samples'] if role!='Idle' else None)
    row = e['idle_world'] if role=='Idle' else rows[index]['world']
    world = {n:native(r) for n,r in row.items()}
    if use_profile:
        expected = e['idle' if role=='Idle' else 'thrust'] if role in ('Idle','Thrust') else e['slashes'][role]['asset']
        if profile['base']!=expected:
            raise RuntimeError('Donor profile base changed: '+profile['base'])
        local = localize(world)
        t = 0. if role=='Idle' else rows[index]['seconds']
        for track in profile['tracks']:
            name = track['bone']
            dp,dq,ds = delta(track,t)
            p,q,s = local[name].decompose()
            local[name] = mat(p+dp,(dq@q).normalized(),s+ds)
        world = globalize(local)
    return {n:canonical(m) for n,m in world.items()}

def descendants(name):
    result = {name}
    for n in NAMES:
        parent = PARENTS[n]
        while parent in PARENTS:
            if parent == name:
                result.add(n)
                break
            parent = PARENTS[parent]
    return result

def blade_frame(pitch):
    angle = math.radians(pitch)
    blade = Vector((0,math.cos(angle),math.sin(angle)))
    edge = Vector((0,-math.sin(angle),math.cos(angle)))
    return Matrix((edge,blade.cross(edge),blade)).transposed().to_quaternion()

def rigid_between(p,q,old):
    return mat(p,q,old.to_scale())@old.inverted()

def support_arm(pose,donor,side,weight):
    """Two bone position solve, then transport complete forearm/upper segments.

    Closed hands/fingers come from the shared hilt. Forearm twist follows the
    hand; a shortest swing aligns its axis. The upper arm adopts that same
    twist frame before its own swing. Both twist helpers and the clavicle
    follow full segment transforms, without isolated wrist/roll overrides.
    """
    upper,lower,hand = ('upperarm_'+side,'lowerarm_'+side,'hand_'+side)
    s0,e0,h0 = (donor[n].translation for n in (upper,lower,hand))
    h = pose[hand].translation
    hand_delta = pose[hand].to_quaternion()@donor[hand].to_quaternion().inverted()
    first,second = (e0-s0).length,(h0-e0).length
    s = s0.copy()
    # Shoulder girdle follows only where needed for the fixed-length chains.
    reach = h-s
    maximum = (first+second)*.975
    if reach.length > maximum:
        s += reach.normalized()*(reach.length-maximum)
    axis = (h-s).normalized()
    distance = (h-s).length
    along = (first*first-second*second+distance*distance)/(2*distance)
    radius = math.sqrt(max(0,first*first-along*along))
    center = s+axis*along
    carried_elbow = h-hand_delta@(h0-e0)
    # A continuous outside/downward pole keeps the elbow on its own side.
    outside = Vector((-.34 if side=='l' else .39,.17,-.35))
    pole = carried_elbow.lerp(outside,.42*weight)-center
    pole -= axis*pole.dot(axis)
    pole.normalize()
    e = center+pole*radius
    old_fore,old_upper = (h0-e0).normalized(),(e0-s0).normalized()
    new_fore,new_upper = (h-e).normalized(),(e-s).normalized()
    fore_delta = (hand_delta@old_fore).rotation_difference(new_fore)@hand_delta
    upper_delta = (fore_delta@old_upper).rotation_difference(new_upper)@fore_delta
    fq = fore_delta@donor[lower].to_quaternion()
    uq = upper_delta@donor[upper].to_quaternion()
    # Blend twist support only; positions always retain both bone lengths.
    native_upper = old_upper.rotation_difference(new_upper)@donor[upper].to_quaternion()
    uq = native_upper.slerp(uq,weight)
    new_lower = mat(e,fq,donor[lower].to_scale())
    new_upper = mat(s,uq,donor[upper].to_scale())
    fd = new_lower@donor[lower].inverted()
    ud = new_upper@donor[upper].inverted()
    for n in (lower,'lowerarm_twist_01_'+side,'lowerarm_twist_02_'+side):
        pose[n] = fd@donor[n]
    for n in (upper,'upperarm_twist_01_'+side,'upperarm_twist_02_'+side,'clavicle_'+side):
        pose[n] = ud@donor[n]

# Camera-author space: +X right, +Y forward, +Z up, metres.
# The left wrist locates the pommel grip. Pitch changes lift the right/guard
# hand further, while both hand-to-hilt matrices remain fixed through the cut.
PATH = [
    (.32, (.055,.27,-.16), -28.),
    (.54, (.120,.235,-.315), -48.),
    (.60, (.120,.235,-.315), -48.),
    (.83, (.085,.285,-.125), 40.),
    (.94, (.070,.300,-.035), 61.),
    (1.06,(.065,.295,-.045), 59.),
    (1.32,(.050,.275,-.160), 28.),
]

def path_sample(t):
    if t <= PATH[0][0]:
        return Vector(PATH[0][1]),PATH[0][2]
    def value(i,c):
        return PATH[i][1][c] if c<3 else PATH[i][2]
    def tangent(i,c):
        if i in (0,len(PATH)-1):return 0.
        before = (value(i,c)-value(i-1,c))/(PATH[i][0]-PATH[i-1][0])
        after = (value(i+1,c)-value(i,c))/(PATH[i+1][0]-PATH[i][0])
        return 2*before*after/(before+after) if before*after>0 else 0.
    for i,(a,b) in enumerate(zip(PATH,PATH[1:])):
        if t <= b[0]:
            dt = b[0]-a[0]
            u = (t-a[0])/dt
            # Shared nonzero velocity carries the fast cut into follow-through.
            result = [(2*u**3-3*u*u+1)*value(i,c)+(u**3-2*u*u+u)*dt*tangent(i,c)
                      +(-2*u**3+3*u*u)*value(i+1,c)+(u**3-u*u)*dt*tangent(i+1,c)
                      for c in range(4)]
            return Vector(result[:3]),result[3]
    return Vector(PATH[-1][1]),PATH[-1][2]

receipts = {}
for variant,entry in DATA['variants'].items():
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    rig = next(o for o in scene.objects if o.type=='ARMATURE')
    rig.animation_data_clear()
    rest = {b.name:b.matrix_local.copy() for b in rig.data.bones}
    local_rest = {n:rest[PARENTS[n]].inverted()@m if PARENTS[n] in rest else m for n,m in rest.items()}
    reference = {n:canonical(native(row)) for n,row in DATA['reference'].items()}
    correction = {n:reference[n].to_quaternion().inverted()@rest[n].to_quaternion() for n in rest}
    idle = live_source(variant,'Idle')
    clip = entry['slashes']['Slash2']
    donor_keys = [localize(live_source(variant,'Slash2',i)) for i in range(len(clip['samples']))]
    def sample(t):
        f = max(0.,min(len(donor_keys)-1,t/clip['seconds']*(len(donor_keys)-1)))
        a,b = int(f),min(len(donor_keys)-1,int(f)+1)
        return globalize({n:blend(donor_keys[a][n],donor_keys[b][n],f-a) for n in NAMES})

    grasp = sample(1.44)
    root = grasp['WPN_root']
    z = (grasp['Blade_Tip'].translation-grasp['Blade_Base'].translation).normalized()
    fore = (grasp['hand_r'].translation-grasp['lowerarm_r'].translation).normalized()
    x = (fore-z*fore.dot(z)).normalized()
    source_frame = Matrix((x,z.cross(x),z)).transposed()
    low_blade = blade_frame(-48.)@Vector((0,0,1))
    low_fore = Vector((-.82,.35,.45)).normalized()
    low_perp = (low_fore-low_blade*low_fore.dot(low_blade)).normalized()
    dest_frame = Matrix((low_perp,low_blade.cross(low_perp),low_blade)).transposed()
    low_grip = (dest_frame@source_frame.transposed()).to_quaternion()@root.to_quaternion()
    grip_offset = blade_frame(-48.).inverted()@low_grip
    hand_groups = {s:descendants('hand_'+s) for s in ('l','r')}
    weapon_group = descendants('WPN_root')

    def cut_pose(t):
        left,pitch = path_sample(t)
        blade_q = blade_frame(pitch)
        grip_q = blade_q@grip_offset
        grip = mat((0,0,0),grip_q,root.to_scale())
        carry = grip@root.inverted()
        carry.translation += left-(carry@grasp['hand_l']).translation
        pose = {n:m.copy() for n,m in grasp.items()}
        # Hand pairs share one rigid hilt; finger local transforms are intact.
        for group in hand_groups.values():
            for n in group:
                pose[n] = carry@grasp[n]
        weapon_root = mat((carry@root).translation,blade_q,root.to_scale())
        sword_carry = weapon_root@root.inverted()
        for n in weapon_group:
            pose[n] = sword_carry@grasp[n]
        for side in ('l','r'):
            support_arm(pose,grasp,side,1.)
        for name,target in [('ik_hand_l','hand_l'),('ik_hand_r','hand_r')]:
            pose[name] = pose[target]@grasp[target].inverted()@grasp[name]
        pose['ik_hand_gun'] = sword_carry@grasp['ik_hand_gun']
        return pose

    ready = cut_pose(.32)
    returning = cut_pose(1.32)

    def contact_blend(a,b,u):
        """Turn around the cylindrical handle, never interpolate through it."""
        p,q,s = a.decompose()
        r,v,k = b.decompose()
        angle_a,angle_b = math.atan2(p.y,p.x),math.atan2(r.y,r.x)
        angle = angle_a+math.atan2(math.sin(angle_b-angle_a),math.cos(angle_b-angle_a))*u
        radius = math.hypot(p.x,p.y)*(1-u)+math.hypot(r.x,r.y)*u
        return mat((radius*math.cos(angle),radius*math.sin(angle),p.z*(1-u)+r.z*u),q.slerp(v,u),s.lerp(k,u))

    def turnover(donor,endpoint,u,entering):
        a,b = (donor,endpoint) if entering else (endpoint,donor)
        wr = blend(a['WPN_root'],b['WPN_root'],u)
        pose = {n:m.copy() for n,m in donor.items()}
        for side,group in hand_groups.items():
            hand = 'hand_'+side
            first = a['WPN_root'].inverted()@a[hand]
            last = b['WPN_root'].inverted()@b[hand]
            hw = wr@contact_blend(first,last,u)
            carry = hw@donor[hand].inverted()
            for n in group:pose[n] = carry@donor[n]
            support_arm(pose,donor,side,u if entering else 1-u)
            ik = 'ik_hand_'+side
            pose[ik] = carry@donor[ik]
        sword_carry = wr@donor['WPN_root'].inverted()
        for n in weapon_group:pose[n] = sword_carry@donor[n]
        pose['ik_hand_gun'] = sword_carry@donor['ik_hand_gun']
        return pose

    def at(t):
        if t <= .32:
            u = smooth(t/.32)
            native_pose = sample(clip['seconds']+(1.44-clip['seconds'])*u)
            return turnover(native_pose,ready,u,True)
        if t >= 1.32:
            u = smooth((t-1.32)/(END-1.32))
            native_pose = sample(1.44+(clip['seconds']-1.44)*u)
            return turnover(native_pose,returning,u,False)
        return cut_pose(t)

    rig.animation_data_create()
    action = bpy.data.actions.new('Sword_UppercutV7_'+variant)
    action.use_fake_user = True
    rig.animation_data.action = action
    samples,previous,blend_previous = [],{},{}
    for i in range(FRAMES+1):
        t = i/FPS
        pose = at(t)
        if i in (0,FRAMES):
            pose = {n:m.copy() for n,m in idle.items()}
        ue = {n:mat(C@m.translation*100,(C@m.to_quaternion().to_matrix()@C).to_quaternion(),m.to_scale())
              for n,m in pose.items()}
        keys = {}
        for n,local in localize(ue).items():
            p,q,s = local.decompose()
            if n in previous and q.dot(previous[n])<0:q = -q
            previous[n] = q.copy()
            keys[n] = dict(p=list(p),q=list(q),s=list(s))
        samples.append(dict(seconds=t,bones=keys))
        scene.frame_set(i)
        worlds = {n:mat(pose[n].translation,pose[n].to_quaternion()@correction[n],pose[n].to_scale()) for n in rest}
        for bone in rig.pose.bones:
            parent_world = worlds[bone.parent.name] if bone.parent else Matrix.Identity(4)
            bone.matrix_basis = local_rest[bone.name].inverted()@parent_world.inverted()@worlds[bone.name]
            bone.rotation_mode = 'QUATERNION'
            q = bone.rotation_quaternion.copy()
            if bone.name in blend_previous and q.dot(blend_previous[bone.name])<0:q = -q
            bone.rotation_quaternion = q
            blend_previous[bone.name] = q.copy()
            for channel in ('location','rotation_quaternion','scale'):
                bone.keyframe_insert(channel,frame=i,group=bone.name)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation = 'LINEAR'
    scene.render.fps,scene.render.fps_base = FPS,1
    scene.frame_start,scene.frame_end = 0,FRAMES
    scene.frame_set(0)
    out = P/variant
    out.mkdir(exist_ok=True)
    patch = dict(revision='ForwardLeverUppercutV7',variant=variant,source_idle=entry['idle'],
        source_grip=clip['asset'],fps=FPS,intervals=FRAMES,seconds=END,samples=samples)
    (out/'editable_keys.json').write_text(json.dumps(patch,separators=(',',':')),encoding='utf-8')
    blend_path = out/'Sword_UppercutV7_Editable.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    receipts[variant] = dict(blend=str(blend_path),keys=str(out/'editable_keys.json'),seconds=END,
        source_grip=clip['asset'],long_grip_source='Current playback profile' if variant=='LongGrip' else None)
    print('FORWARD_LEVER_UPPERCUT_V7_AUTHORED '+variant,flush=True)
(P/'authoring.json').write_text(json.dumps(dict(revision='ForwardLeverUppercutV7',fps=FPS,
    reference='User local c99036b756c357f62d66e37de1f093e8.mp4: second demonstration 6.2-9.4 sec',
    interpretation='Black-banded upper-left end is pommel; left hand rear, right hand guard; blade cuts forward/up',
    grip='Thumb-side blade; fixed double-hand hilt contacts during cut; no ice-pick grip',
    source_use='Native closed-hand articulation only; newly authored sagittal weapon path and full arm solves',
    paid_motion_used=False,phases=dict(turnover=[0,.32],lower=[.32,.54],hold=[.54,.60],
        cut=[.60,.83],follow=[.83,.94],settle=[.94,1.06],recover=[1.06,END]),
    path=PATH,variants=receipts,runtime_tested=False,rendered=False),ensure_ascii=False,indent=2),encoding='utf-8')

