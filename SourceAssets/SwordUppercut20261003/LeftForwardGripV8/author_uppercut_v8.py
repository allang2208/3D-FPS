"""Correct only the left support hand to the native forward grip; preserve accepted V7 right arm and sword keys."""
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

def solve_left(pose,old,normal,weight):
    """Rebuild only the left chain for the corrected hilt contact.

    The source V7 shoulder and lengths remain the geometric baseline. The
    native idle forward grip supplies the anatomical forearm/hand roll frame.
    Rotation support fades in with the correction, so idle and the original
    entry/exit have no added endpoint twist.
    """
    upper,lower,hand = 'upperarm_l','lowerarm_l','hand_l'
    s0,e0,h0 = (old[n].translation for n in (upper,lower,hand))
    h = pose[hand].translation
    first,second = (e0-s0).length,(h0-e0).length
    s = s0.copy()
    reach = h-s
    maximum = (first+second)*.975
    if reach.length>maximum:s += reach.normalized()*(reach.length-maximum)
    axis = (h-s).normalized()
    distance = (h-s).length
    along = (first*first-second*second+distance*distance)/(2*distance)
    center = s+axis*along
    radius = math.sqrt(max(0,first*first-along*along))
    hand_delta = pose[hand].to_quaternion()@old[hand].to_quaternion().inverted()
    carried_elbow = h-hand_delta@(h0-e0)
    outside = Vector((-.34,.17,-.35))
    pole = carried_elbow.lerp(outside,.62*weight)-center
    pole -= axis*pole.dot(axis)
    e = center+pole.normalized()*radius
    fore_axis,upper_axis = (h-e).normalized(),(e-s).normalized()
    old_fore = (h0-e0).normalized()
    old_upper = (e0-s0).normalized()
    old_fore_delta = (hand_delta@old_fore).rotation_difference(fore_axis)@hand_delta
    old_fq = old_fore_delta@old[lower].to_quaternion()
    ns,ne,nh = (normal[n].translation for n in (upper,lower,hand))
    normal_hand_delta = pose[hand].to_quaternion()@normal[hand].to_quaternion().inverted()
    normal_fore_delta = (normal_hand_delta@(nh-ne).normalized()).rotation_difference(fore_axis)@normal_hand_delta
    normal_fq = normal_fore_delta@normal[lower].to_quaternion()
    fq = old_fq.slerp(normal_fq,weight)
    full_fore_delta = fq@normal[lower].to_quaternion().inverted()
    normal_uq = (full_fore_delta@(ne-ns).normalized()).rotation_difference(upper_axis)@full_fore_delta@normal[upper].to_quaternion()
    carried_uq = old_upper.rotation_difference(upper_axis)@old[upper].to_quaternion()
    uq = carried_uq.slerp(normal_uq,weight)
    pose[lower] = mat(e,fq,old[lower].to_scale())
    pose[upper] = mat(s,uq,old[upper].to_scale())
    for segment in ('lowerarm','upperarm'):
        parent = segment+'_l'
        for number in ('01','02'):
            n = segment+'_twist_'+number+'_l'
            old_relative = old[parent].inverted()@old[n]
            normal_relative = normal[parent].inverted()@normal[n]
            pose[n] = pose[parent]@blend(old_relative,normal_relative,weight)
    pose['clavicle_l'] = pose[upper]@old[upper].inverted()@old['clavicle_l']
    pose['ik_hand_l'] = pose[hand]@old[hand].inverted()@old['ik_hand_l']

def envelope(t):
    return smooth(t/.32) if t<.32 else (smooth((END-t)/(END-1.32)) if t>1.32 else 1.)

receipts = {}
for variant,entry in DATA['variants'].items():
    source_keys = P/'AcceptedV7'/variant/'editable_keys.json'
    accepted = json.loads(source_keys.read_text('utf-8'))
    normal = live_source(variant,'Idle')
    normal_contact = normal['WPN_root'].inverted()@normal['hand_l']
    normal_station = grip_station(normal)
    normal_fingers = {n:normal['hand_l'].inverted()@normal[n] for n in LEFT_HAND}
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
    action = bpy.data.actions.new('Sword_UppercutV8_'+variant)
    action.use_fake_user = True
    rig.animation_data.action = action
    samples,previous,blend_previous = [],{},{}
    for i,original in enumerate(accepted['samples']):
        t = original['seconds']
        old = {n:canonical(m) for n,m in globalize({n:native(row) for n,row in original['bones'].items()}).items()}
        pose = {n:m.copy() for n,m in old.items()}
        weight = envelope(t)
        if weight>0.:
            wr = old['WPN_root']
            old_contact = wr.inverted()@old['hand_l']
            target_contact = normal_contact.copy()
            # Retain the accepted pommel grasp station while using the complete
            # native normal grip. Align finger rows, not the offset wrist origin.
            target_contact.translation.z += grip_station(old)-normal_station
            hw = wr@contact_blend(old_contact,target_contact,weight)
            for n in LEFT_HAND:
                if n=='hand_l':
                    pose[n] = hw
                else:
                    relative = old['hand_l'].inverted()@old[n]
                    pose[n] = hw@blend(relative,normal_fingers[n],weight)
            solve_left(pose,old,normal,weight)
        # Copy all V7 keys verbatim; replace only the left shoulder/arm/hand/IK.
        # This makes the user's accepted right arm, sword and timing immutable
        # through this revision, including helpers and weapon parent bones.
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
    patch = dict(revision='LeftForwardGripUppercutV8',variant=variant,source_idle=entry['idle'],
        accepted_source=str(source_keys),fps=FPS,intervals=FRAMES,seconds=END,samples=samples)
    (out/'editable_keys.json').write_text(json.dumps(patch,separators=(',',':')),encoding='utf-8')
    blend_path = out/'Sword_UppercutV8_Editable.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    receipts[variant] = dict(blend=str(blend_path),keys=str(out/'editable_keys.json'),seconds=END,
        forward_grip_source=entry['idle'],accepted_source=str(source_keys))
    print('LEFT_FORWARD_GRIP_UPPERCUT_V8_AUTHORED '+variant,flush=True)
(P/'authoring.json').write_text(json.dumps(dict(revision='LeftForwardGripUppercutV8',fps=FPS,
    request='Preserve accepted V7 right hand; left hand must use a normal forward grip',
    processing='Native idle left grip at original pommel finger-row station; complete left arm and twist support',
    preserved='All non-left-arm V7 keys copied verbatim, including right fingers, right arm, sword and timing',
    changed_bones=sorted(LEFT_BONES),paid_motion_used=False,
    variants=receipts,runtime_tested=False,rendered=False),ensure_ascii=False,indent=2),encoding='utf-8')

