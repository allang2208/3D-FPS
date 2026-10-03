"""Video overhand left grip: thumb/index toward right hand; repair hilt-side choice and neutral wrist support."""
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

LEFT_HAND = descendants('hand_l')
LEFT_BONES = descendants('clavicle_l') | {'ik_hand_l'}
KNUCKLES = ['index_01_l','middle_01_l','ring_01_l','pinky_01_l']

def grip_station(world):
    """Finger-row station on the hilt, independent of wrist orientation."""
    inv = world['WPN_root'].inverted()
    return sum((inv@world[n]).translation.z for n in KNUCKLES)/len(KNUCKLES)

def contact_blend(a,b,u):
    p,q,s = a.decompose()
    r,v,k = b.decompose()
    angle_a,angle_b = math.atan2(p.y,p.x),math.atan2(r.y,r.x)
    angle = angle_a+math.atan2(math.sin(angle_b-angle_a),math.cos(angle_b-angle_a))*u
    radius = math.hypot(p.x,p.y)*(1-u)+math.hypot(r.x,r.y)*u
    return mat((radius*math.cos(angle),radius*math.sin(angle),p.z*(1-u)+r.z*u),q.slerp(v,u),s.lerp(k,u))

# All turns are about the hilt's longitudinal axis. The index/pinky order is
# preserved: thumb/index stay toward the right/guard hand, pinky toward pommel.
# Negative roll places the left wrist on the left side of the hilt, matching
# the video's arm approach, instead of bending the wrist back from the right.
ROLL_KEYS = [(0.,0.),(.32,-165.),(.54,-150.),(.60,-150.),(.83,-170.),
             (.94,-180.),(1.06,-180.),(1.32,-165.),(1.70,0.)]

def envelope(t):
    return smooth(t/.32) if t<.32 else (smooth((END-t)/(END-1.32)) if t>1.32 else 1.)

def preferred_roll(t):
    for a,b in zip(ROLL_KEYS,ROLL_KEYS[1:]):
        if t<=b[0]:
            u = smooth((t-a[0])/(b[0]-a[0]))
            return math.radians(a[1]+(b[1]-a[1])*u)
    return 0.

def around_hilt(old,angle):
    wr = old['WPN_root']
    axis = (old['Blade_Tip'].translation-old['Blade_Base'].translation).normalized()
    pivot = wr@Vector((0,0,grip_station(old)))
    return Matrix.Translation(pivot)@Quaternion(axis,angle).to_matrix().to_4x4()@Matrix.Translation(-pivot)

def arm_geometry(hand,normal,weight):
    s0,e0,h0 = (normal[n].translation for n in ('upperarm_l','lowerarm_l','hand_l'))
    h = hand.translation
    first,second = (e0-s0).length,(h0-e0).length
    dq = hand.to_quaternion()@normal['hand_l'].to_quaternion().inverted()
    # This is the elbow implied by an unchanged native wrist relationship.
    # Project it onto the two-bone circle, rather than biasing the elbow to a
    # fixed low pole that forced V8/V9 to back-bend the wrist.
    ideal_axis = (dq@(h0-e0)).normalized()
    ideal_elbow = h-ideal_axis*second
    neutral_shoulder = ideal_elbow+(s0-ideal_elbow).normalized()*first
    shoulder_delta = neutral_shoulder-s0
    limit = .04*weight
    if shoulder_delta.length>limit:
        shoulder_delta = shoulder_delta.normalized()*limit
    s = s0+shoulder_delta
    reach = h-s
    maximum = (first+second)*.98
    if reach.length>maximum:s += reach.normalized()*(reach.length-maximum)
    distance = (h-s).length
    axis = (h-s).normalized()
    along = (first*first-second*second+distance*distance)/(2*distance)
    radius = math.sqrt(max(0.,first*first-along*along))
    center = s+axis*along
    pole = ideal_elbow-center
    pole -= axis*pole.dot(axis)
    e = center+pole.normalized()*radius
    fore_axis = (h-e).normalized()
    deviation = ideal_axis.angle(fore_axis)
    return s,e,fore_axis,dq,deviation

def supported_left(pose,normal,geometry):
    s,e,fore_axis,hand_delta,_ = geometry
    h = pose['hand_l'].translation
    ns,ne,nh = (normal[n].translation for n in ('upperarm_l','lowerarm_l','hand_l'))
    fore_delta = (hand_delta@(nh-ne).normalized()).rotation_difference(fore_axis)@hand_delta
    upper_delta = (fore_delta@(ne-ns).normalized()).rotation_difference((e-s).normalized())@fore_delta
    pose['lowerarm_l'] = mat(e,fore_delta@normal['lowerarm_l'].to_quaternion(),normal['lowerarm_l'].to_scale())
    pose['upperarm_l'] = mat(s,upper_delta@normal['upperarm_l'].to_quaternion(),normal['upperarm_l'].to_scale())
    for segment in ('lowerarm','upperarm'):
        parent = segment+'_l'
        carry = pose[parent]@normal[parent].inverted()
        for number in ('01','02'):
            n = segment+'_twist_'+number+'_l'
            pose[n] = carry@normal[n]
    pose['clavicle_l'] = pose['upperarm_l']@normal['upperarm_l'].inverted()@normal['clavicle_l']

receipts = {}
for variant in DATA['variants']:
    source_keys = P/'SourceV9'/variant/'editable_keys.json'
    accepted = json.loads(source_keys.read_text('utf-8'))
    def world(sample):
        return {n:canonical(m) for n,m in globalize({n:native(row) for n,row in sample['bones'].items()}).items()}
    normal = world(accepted['samples'][0])
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    rig = next(o for o in scene.objects if o.type=='ARMATURE')
    rig.animation_data_clear()
    rest = {b.name:b.matrix_local.copy() for b in rig.data.bones}
    local_rest = {n:rest[PARENTS[n]].inverted()@m if PARENTS[n] in rest else m for n,m in rest.items()}
    reference = {n:canonical(native(row)) for n,row in DATA['reference'].items()}
    correction = {n:reference[n].to_quaternion().inverted()@rest[n].to_quaternion() for n in rest}
    rig.animation_data_create()
    action = bpy.data.actions.new('Sword_UppercutV10_'+variant)
    action.use_fake_user = True
    rig.animation_data.action = action
    samples,previous,blend_previous,controls = [],{},{},[]
    previous_roll = 0.
    for i,original in enumerate(accepted['samples']):
        t = original['seconds']
        phase = original.get('source_seconds',t)
        weight = envelope(phase)
        old = world(original)
        pose = {n:m.copy() for n,m in old.items()}
        angle = 0.
        if weight>0.:
            preferred = preferred_roll(phase)
            allowance = math.radians(24.)*weight
            def evaluate(angle):
                hand = around_hilt(old,angle)@old['hand_l']
                geometry = arm_geometry(hand,normal,weight)
                elbow = geometry[1]
                # Bound the fit to the authored overhand side and penalize
                # crossed-center support. No full-circle or multi-turn search.
                cross = max(0.,elbow.x-(hand.translation.x-.055))
                cost = geometry[4]**2+.08*(angle-preferred)**2+.025*(angle-previous_roll)**2+20*cross*cross
                return cost,geometry
            choices = [preferred-allowance+2*allowance*j/48 for j in range(49)]
            costs = [evaluate(a)[0] for a in choices]
            k = min(range(len(choices)),key=lambda j:costs[j])
            angle = choices[k]
            if 0<k<len(choices)-1:
                denominator = costs[k-1]-2*costs[k]+costs[k+1]
                if denominator>1.e-10:
                    offset = max(-.5,min(.5,.5*(costs[k-1]-costs[k+1])/denominator))
                    angle += offset*(choices[k+1]-choices[k])
            carry = around_hilt(old,angle)
            for n in LEFT_HAND:pose[n] = carry@old[n]
            geometry = arm_geometry(pose['hand_l'],normal,weight)
            supported_left(pose,normal,geometry)
            pose['ik_hand_l'] = carry@old['ik_hand_l']
        previous_roll = angle
        controls.append(dict(seconds=t,source_seconds=phase,hilt_roll_degrees=math.degrees(angle)))
        # V9 right arm, weapon, blade and retimed parent keys remain exact.
        keys = {n:dict(row) for n,row in original['bones'].items()}
        if weight>0.:
            ue = {n:mat(C@m.translation*100,(C@m.to_quaternion().to_matrix()@C).to_quaternion(),m.to_scale())
                  for n,m in pose.items()}
            for n,m in localize(ue).items():
                if n not in LEFT_BONES:continue
                p,q,s = m.decompose()
                if n in previous and q.dot(previous[n])<0:q = -q
                keys[n] = dict(p=list(p),q=list(q),s=list(s))
        for n in LEFT_BONES:previous[n] = Quaternion(keys[n]['q'])
        samples.append(dict(seconds=t,source_seconds=phase,bones=keys))
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
    patch = dict(revision='LeftOverhandUppercutV10',variant=variant,source_keys=str(source_keys),
                 fps=FPS,intervals=FRAMES,seconds=END,samples=samples)
    (out/'editable_keys.json').write_text(json.dumps(patch,separators=(',',':')),encoding='utf-8')
    (out/'grip_controls.json').write_text(json.dumps(controls,indent=2),encoding='utf-8')
    blend_path = out/'Sword_UppercutV10_Editable.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    receipts[variant] = dict(blend=str(blend_path),keys=str(out/'editable_keys.json'),seconds=END,
                            source_keys=str(source_keys))
    print('LEFT_OVERHAND_UPPERCUT_V10_AUTHORED '+variant,flush=True)
(P/'authoring.json').write_text(json.dumps(dict(revision='LeftOverhandUppercutV10',fps=FPS,
    reference='User local video re-read at 2.10, 6.20 and 8.30 seconds; hand order explicitly clarified by user',
    grip='Left thumb/index toward the right hand; pinky toward black-banded pommel; no axial hand inversion',
    correction='Move complete closed left hand around hilt to left-side approach; elbow solves for neutral wrist, not fixed low elbow pole',
    preservation='All non-left-arm V9 keys copied verbatim; right arm, sword path and fast release timing retained',
    changed_bones=sorted(LEFT_BONES),variants=receipts,paid_motion_used=False,
    runtime_tested=False,rendered=False),ensure_ascii=False,indent=2),encoding='utf-8')

