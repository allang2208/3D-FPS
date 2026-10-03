"""Use the actual idle left grip and elbow bend plane; no hilt roll curve or roll search."""
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

def limb_frame(direction,normal):
    x = direction.normalized()
    z = (normal-x*normal.dot(x)).normalized()
    y = z.cross(x).normalized()
    return Matrix((x,y,z)).transposed()

def follow_idle_arm(pose,idle):
    """Keep the idle elbow side and hinge frame, without hand-driven arm roll.

    The idle bend direction is transported by the smallest shoulder-to-wrist
    swing. Hand pronation is carried progressively by the forearm helpers;
    it never rotates the entire upper arm to chase the hand's palm direction.
    """
    s0,e0,h0 = (idle[n].translation for n in ('upperarm_l','lowerarm_l','hand_l'))
    h = pose['hand_l'].translation
    upper0,fore0 = e0-s0,h0-e0
    first,second = upper0.length,fore0.length
    u0 = (h0-s0).normalized()
    old_pole = e0-s0-u0*(e0-s0).dot(u0)
    s = s0.copy()
    reach = h-s
    maximum = (first+second)*.97
    if reach.length>maximum:s += reach.normalized()*(reach.length-maximum)
    distance = (h-s).length
    axis = (h-s).normalized()
    pole = u0.rotation_difference(axis)@old_pole.normalized()
    pole = (pole-axis*pole.dot(axis)).normalized()
    along = (first*first-second*second+distance*distance)/(2*distance)
    radius = math.sqrt(max(0.,first*first-along*along))
    e = s+axis*along+pole*radius
    upper,fore = e-s,h-e
    plane0 = upper0.cross(fore0).normalized()
    plane = upper.cross(fore).normalized()
    upper_delta = (limb_frame(upper,plane)@limb_frame(upper0,plane0).transposed()).to_quaternion()
    fore_delta = (limb_frame(fore,plane)@limb_frame(fore0,plane0).transposed()).to_quaternion()
    pose['upperarm_l'] = mat(s,upper_delta@idle['upperarm_l'].to_quaternion(),idle['upperarm_l'].to_scale())
    pose['lowerarm_l'] = mat(e,fore_delta@idle['lowerarm_l'].to_quaternion(),idle['lowerarm_l'].to_scale())
    # Distal forearm roll follows the hand; the elbow keeps the idle hinge frame.
    hand_delta = pose['hand_l'].to_quaternion()@idle['hand_l'].to_quaternion().inverted()
    distal_delta = (hand_delta@fore0.normalized()).rotation_difference(fore.normalized())@hand_delta
    if fore_delta.dot(distal_delta)<0:distal_delta = -distal_delta
    for number in ('01','02'):
        name = 'lowerarm_twist_'+number+'_l'
        station = max(0.,min(1.,(idle[name].translation-e0).dot(fore0.normalized())/second))
        delta_q = fore_delta.slerp(distal_delta,station)
        pose[name] = mat(e+fore_delta@(idle[name].translation-e0),
                         delta_q@idle[name].to_quaternion(),idle[name].to_scale())
        name = 'upperarm_twist_'+number+'_l'
        pose[name] = mat(s+upper_delta@(idle[name].translation-s0),
                         upper_delta@idle[name].to_quaternion(),idle[name].to_scale())
    pose['clavicle_l'] = Matrix.Translation(s-s0)@idle['clavicle_l']

receipts = {}
for variant in DATA['variants']:
    source_keys = P/'SourceV10'/variant/'editable_keys.json'
    accepted = json.loads(source_keys.read_text('utf-8'))
    idle = live_source(variant,'Idle')
    blade0 = (idle['Blade_Tip'].translation-idle['Blade_Base'].translation).normalized()
    station = grip_station(idle)
    pivot0 = idle['WPN_root']@Vector((0,0,station))
    idle_ue = {n:mat(C@m.translation*100,(C@m.to_quaternion().to_matrix()@C).to_quaternion(),m.to_scale()) for n,m in idle.items()}
    idle_keys = {}
    for n,m in localize(idle_ue).items():
        p,q,s = m.decompose()
        idle_keys[n] = dict(p=list(p),q=list(q),s=list(s))
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
    action = bpy.data.actions.new('Sword_UppercutV11_'+variant)
    action.use_fake_user = True
    rig.animation_data.action = action
    samples,previous,blend_previous = [],{},{}
    for i,original in enumerate(accepted['samples']):
        pose = {n:canonical(m) for n,m in globalize({n:native(k) for n,k in original['bones'].items()}).items()}
        blade = (pose['Blade_Tip'].translation-pose['Blade_Base'].translation).normalized()
        # Follow only the sword's direction. Its display-face rotation is not
        # a grip rotation, and must not add any axial flip to the idle left hand.
        swing = blade0.rotation_difference(blade)
        pivot = pose['WPN_root']@Vector((0,0,station))
        carry = Matrix.Translation(pivot)@swing.to_matrix().to_4x4()@Matrix.Translation(-pivot0)
        for n in LEFT_HAND:pose[n] = carry@idle[n]
        follow_idle_arm(pose,idle)
        pose['ik_hand_l'] = carry@idle['ik_hand_l']
        if i in (0,FRAMES):
            for n in LEFT_BONES:pose[n] = idle[n].copy()
        ue = {n:mat(C@m.translation*100,(C@m.to_quaternion().to_matrix()@C).to_quaternion(),m.to_scale()) for n,m in pose.items()}
        keys = {n:dict(k) for n,k in original['bones'].items()}
        for n,m in localize(ue).items():
            if n not in LEFT_BONES:continue
            if n in LEFT_HAND and n!='hand_l':
                keys[n] = dict(idle_keys[n])
            else:
                p,q,s = m.decompose()
                if n in previous and q.dot(previous[n])<0:q = -q
                keys[n] = dict(p=list(p),q=list(q),s=list(s))
            previous[n] = Quaternion(keys[n]['q'])
        samples.append(dict(seconds=original['seconds'],source_seconds=original.get('source_seconds',original['seconds']),bones=keys))
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
    patch = dict(revision='IdleLeftUppercutV11',variant=variant,source_keys=str(source_keys),
                 idle_source=DATA['variants'][variant]['idle'],fps=FPS,intervals=FRAMES,seconds=END,samples=samples)
    (out/'editable_keys.json').write_text(json.dumps(patch,separators=(',',':')),encoding='utf-8')
    blend_path = out/'Sword_UppercutV11_Editable.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    receipts[variant] = dict(blend=str(blend_path),keys=str(out/'editable_keys.json'),seconds=END,
        idle_source=DATA['variants'][variant]['idle'])
    print('IDLE_LEFT_UPPERCUT_V11_AUTHORED '+variant,flush=True)
(P/'authoring.json').write_text(json.dumps(dict(revision='IdleLeftUppercutV11',fps=FPS,
    request='The normal idle left hand already suits this action; remove the left-arm flip',
    method='Fresh native idle grip; shortest blade-axis swing only; idle elbow-plane transport; gradual distal forearm twist',
    removed='V10 hilt roll curve and bounded roll search; hand-driven upper-arm roll',
    preservation='Non-left V10 keys copied verbatim; idle finger local transforms copied directly; same fast release timing',
    variants=receipts,paid_motion_used=False,runtime_tested=False,rendered=False),ensure_ascii=False,indent=2),encoding='utf-8')

