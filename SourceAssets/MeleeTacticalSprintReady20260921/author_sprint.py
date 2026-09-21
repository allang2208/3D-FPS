"""Author a half-second dash-ready entry and stride-synchronized blade motion.

Uses current UE source poses and the existing sword/arm calibration. Does not
render, run gameplay or replace the accepted idle/walk/overhead assets.
"""
import ast
import json
import math
from pathlib import Path
import bpy
from mathutils import Matrix, Quaternion, Vector

P = Path(__file__).parent
ROOT = P.parents[1]
CFG = json.loads((P/'motion.json').read_text())
FPS = CFG['fps']
SOURCE = ROOT/'SourceAssets/RuneSwordPickaxeOverhead20260920/ImpactV2/Standard/Sword_PickaxeOverhead_Editable.blend'
OLD = ROOT/'SourceAssets/RuneSwordElbowRepair20260920'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
local_rest = {b.name: rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name] for b in rig.data.bones}
source_action = bpy.data.actions['A_RuneSword_Overhead_Standard']
rig.animation_data.action = source_action
rig.animation_data.action_slot = source_action.slots[0]
scene.frame_set(0)
bpy.context.view_layer.update()
zero = {b.name: b.matrix.copy() for b in rig.pose.bones}
ue_zero = json.loads((OLD/'Standard_active.json').read_text())['clips']['Overhead']['samples'][0]['world']
C = Matrix.Diagonal(Vector((1,-1,1)))
K = {n: (C@Quaternion(ue_zero[n]['q']).to_matrix()@C).inverted()@m.to_quaternion().to_matrix() for n,m in zero.items()}
tree = ast.parse((OLD/'pose_conversion.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'from_ue','ue_matrix','to_ue'}],type_ignores=[]),str(OLD/'pose_conversion.py'),'exec'),globals())
STATIONS = json.loads((SOURCE.parents[1]/'authoring.json').read_text())['skin_stations']

def smooth(x):
    x = max(0.,min(1.,x))
    return x*x*x*(10.-15.*x+6.*x*x)

def blend_matrix(a,b,t):
    p,q,s = a.decompose()
    v,r,k = b.decompose()
    return Matrix.LocRotScale(p.lerp(v,t),q.slerp(r,t),s.lerp(k,t))

def unwrap(value, previous):
    return value if previous is None else previous+(value-previous+math.pi)%(2*math.pi)-math.pi

def axial_delta(a,b,axis):
    q = a@b.inverted()
    return (2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w)+math.pi)%(2*math.pi)-math.pi

def frame_rotation(axis, normal):
    return Matrix((axis,normal,axis.cross(normal))).transposed().to_quaternion()

def shoulder(side, weight):
    return idle['upperarm_'+side].translation+Vector(CFG['shoulder_offset_m'][side])*weight

def fit_held_group(wpn, weight):
    # Project the whole held group into the intersection of the two arm reaches.
    # Both grasp matrices remain invariant; no independent wrist clamping.
    fitted = wpn.copy()
    for _ in range(16):
        for side in ('l','r'):
            a,e,h = [idle[n+'_'+side].translation for n in ('upperarm','lowerarm','hand')]
            maximum = (e-a).length+(h-e).length-.016
            origin = shoulder(side,weight)
            delta = (fitted@grips[side]).translation-origin
            if delta.length>maximum:
                fitted.translation += delta.normalized()*(maximum-delta.length)
    return fitted

def clear_view_elbow(origin, target, center, direction, radius, supported, neutral_axis, weight):
    """Select an elbow hint on the exact two-bone circle during offline authoring.

    Uses separate target/pole/hinge responsibilities as in ozz IKTwoBoneJob.
    Camera clearance is our viewmodel-specific objective, not an ozz feature.
    """
    cfg = CFG['left_clearance']
    tan_h = math.tan(math.radians(cfg['horizontal_fov']*.5))
    tan_v = tan_h/cfg['aspect']
    seat = idle['lowerarm_l'].translation.lerp(Vector(CFG['left_elbow_hint_m']),weight)

    def coverage(point, thickness, crop=1.):
        h,v = tan_h*crop,tan_v*crop
        # Signed camera-plane distances with an arm-thickness allowance.
        horizontal = h*point.y-abs(point.x)+thickness*math.sqrt(1+h*h)
        vertical = v*point.y-abs(point.z)+thickness*math.sqrt(1+v*v)
        return max(0.,min(horizontal,vertical,point.y+thickness-.01))**2

    def evaluate(angle):
        radial = Quaternion(direction,angle)@supported
        elbow = center+radial*radius
        fore_axis = (target-elbow).normalized()
        wrist_bend = math.acos(max(-1.,min(1.,fore_axis.dot(neutral_axis))))
        occlusion = 0.
        for start,end,thickness in ((origin,elbow,cfg['upper_radius_m']),(elbow,target,cfg['fore_radius_m'])):
            for k in range(1,10):
                point = start.lerp(end,k/10.)
                occlusion += coverage(point,thickness)+2.*coverage(point,thickness,.65)
        cost = 80.*occlusion/18.+.003*wrist_bend*wrist_bend+1.2*(elbow-seat).length_squared
        cost += 20.*max(0.,elbow.y-.025)**2+20.*max(0.,elbow.z+.13)**2
        cost += 15.*max(0.,elbow.x-.07)**2
        return cost

    limit = math.radians(cfg['swivel_limit_degrees'])
    step = 2.*limit/32.
    candidates = [-limit+i*step for i in range(33)]
    best = min(candidates,key=evaluate)
    lo,hi = max(-limit,best-step),min(limit,best+step)
    # Continuous refinement avoids quantized elbow motion in the baked loop.
    phi = (math.sqrt(5.)-1.)*.5
    for _ in range(18):
        a,b = hi-phi*(hi-lo),lo+phi*(hi-lo)
        if evaluate(a)<evaluate(b):hi=b
        else:lo=a
    return Quaternion(direction,(lo+hi)*.5)@supported

def solve_arm(pose, side, hand, weight, state):
    upper,fore,wrist = [p+'_'+side for p in ('upperarm','lowerarm','hand')]
    a = (rest[fore].translation-rest[upper].translation).normalized()
    b = (rest[wrist].translation-rest[fore].translation).normalized()
    rest_normal = a.cross(b).normalized()
    old_s,old_e,old_w = [idle[n].translation for n in (upper,fore,wrist)]
    l1,l2 = (old_e-old_s).length,(old_w-old_e).length
    origin = shoulder(side,weight)
    target = hand.translation
    delta = target-origin
    direction,distance = delta.normalized(),delta.length
    along = (l1*l1-l2*l2+distance*distance)/(2*distance)
    center = origin+direction*along
    guide = Vector(CFG['elbow_pole'][side])
    supported = (guide-direction*guide.dot(direction)).normalized()
    # Choose the elbow on its reach circle using the palm's neutral wrist axis.
    # A fixed pole alone can place the wrist correctly but leave it kinked.
    hand_deform = hand.to_quaternion()@rest[wrist].to_quaternion().inverted()
    neutral_elbow = target-(hand_deform@b)*l2
    neutral = neutral_elbow-center
    neutral -= direction*neutral.dot(direction)
    swivel = math.atan2(direction.dot(supported.cross(neutral)),supported.dot(neutral))
    limit = math.radians(CFG['elbow_swivel_degrees'])
    swivel = max(-limit,min(limit,swivel))*CFG['wrist_alignment_weight']
    desired = Quaternion(direction,swivel)@supported
    if side=='l':
        radius = math.sqrt(max(0.,l1*l1-along*along))
        desired = clear_view_elbow(origin,target,center,direction,radius,supported,hand_deform@b,weight)
    initial = old_e-center
    initial = (initial-direction*initial.dot(direction)).normalized()
    angle = math.atan2(direction.dot(initial.cross(desired)),initial.dot(desired))
    elbow_weight = smooth(min(1.,weight/.50)) if side=='l' else weight
    elbow = center+(Quaternion(direction,angle*elbow_weight)@initial)*math.sqrt(max(0.,l1*l1-along*along))
    up_axis,fore_axis = (elbow-origin).normalized(),(target-elbow).normalized()
    normal = up_axis.cross(fore_axis).normalized()
    hinge = frame_rotation(up_axis,normal)@frame_rotation(a,rest_normal).inverted()
    source_q = (old_e-old_s).normalized().rotation_difference(up_axis)@idle[upper].to_quaternion()
    upper_q = source_q.slerp(hinge@rest[upper].to_quaternion(),weight)
    upper_deform = upper_q@rest[upper].to_quaternion().inverted()
    full_fore = (hand_deform@b).rotation_difference(fore_axis)@hand_deform
    fore_hinge = (upper_deform@b).rotation_difference(fore_axis)@upper_deform
    requested = unwrap(axial_delta(full_fore,fore_hinge,fore_axis),state.get(side+'_raw'))
    state[side+'_raw'] = requested
    roll_limit = math.radians(CFG['humerus_twist_limit_degrees'])
    humerus_roll = max(-roll_limit,min(roll_limit,requested*CFG['humerus_twist_share']))*weight
    upper_q = Quaternion(up_axis,humerus_roll)@upper_q
    upper_deform = upper_q@rest[upper].to_quaternion().inverted()
    fore_hinge = (upper_deform@b).rotation_difference(fore_axis)@upper_deform
    twist = unwrap(axial_delta(full_fore,fore_hinge,fore_axis),state.get(side+'_twist'))
    state[side+'_twist'] = twist
    pose['clavicle_'+side].translation += origin-old_s
    pose[upper] = Matrix.LocRotScale(origin,upper_q,Vector((1,1,1)))
    for i in ('01','02'):
        name = 'upperarm_twist_'+i+'_'+side
        pose[name] = pose[upper]@rest[upper].inverted()@rest[name]
    fore_matrix = Matrix.LocRotScale(elbow,full_fore@rest[fore].to_quaternion(),Vector((1,1,1)))
    for name,station in STATIONS[side].items():
        p = (fore_matrix@rest[fore].inverted()@rest[name]).translation
        q = Quaternion(fore_axis,twist*(1.-weight*(1.-station)))@fore_hinge@rest[name].to_quaternion()
        pose[name] = Matrix.LocRotScale(p,q,Vector((1,1,1)))
    pose[wrist] = hand
    # The accepted palm/fingers form one rigid held group with the weapon.
    for bone in rig.data.bones:
        if bone.name.startswith(('thumb','index','middle','ring','pinky')) and bone.name.endswith('_'+side):
            pose[bone.name] = pose[bone.parent.name]@idle[bone.parent.name].inverted()@idle[bone.name]

def pose_from_weapon(wpn,weight,state):
    if weight<=1e-8:
        return {n:m.copy() for n,m in idle.items()}
    wpn = fit_held_group(wpn,weight)
    pose = {n:m.copy() for n,m in idle.items()}
    for side in ('l','r'):
        solve_arm(pose,side,wpn@grips[side],weight,state)
    pose['WPN_root'] = wpn
    for name in ('Blade_Base','Blade_Tip'):
        if name in pose:pose[name] = wpn@idle['WPN_root'].inverted()@idle[name]
    return pose

def ready_to_carry(weight):
    final = Vector(CFG['grip_center_m'])
    retract = smooth(weight/CFG['entry_retract_finish'])
    lift = smooth((weight-CFG['entry_lift_start'])/(1.-CFG['entry_lift_start']))
    turn = smooth((weight-CFG['entry_turn_start'])/(1.-CFG['entry_turn_start']))
    center = ready_center.lerp(final,retract)
    center.x += CFG['entry_side_arc_m']*math.sin(math.pi*weight)**2
    center.z = ready_center.z+(final.z-ready_center.z)*lift
    q = ready.to_quaternion().slerp(carry_rotation,turn)
    m = Matrix.LocRotScale(Vector((0,0,0)),q,ready.decompose()[2])
    m.translation = center-m.to_3x3()@pivot
    return m

def loop_weapon(t,duration):
    phase = 2*math.pi*t/duration-CFG['loop_stride_lag_radians']
    side,step = math.cos(phase),math.cos(2.*phase)
    # Same stride/contact wave family as WeaponActionCameraComponent::Apply.
    contact = max(0.,step)**3-2./(3.*math.pi)
    pulse = step+CFG['loop_footfall_weight']*contact
    m = ready_to_carry(1.)
    roll = Quaternion(Vector((0,1,0)),math.radians(CFG['loop_roll_degrees'])*side)
    pitch = Quaternion(Vector((1,0,0)),-math.radians(CFG['loop_pitch_degrees'])*pulse)
    yaw = Quaternion(Vector((0,0,1)),-math.radians(CFG['loop_yaw_degrees'])*math.sin(phase))
    q = roll@yaw@pitch@m.to_quaternion()
    center = Vector(CFG['grip_center_m'])+Vector((CFG['loop_side_m']*side,
        -CFG['loop_forward_m']*step,-CFG['loop_down_m']*pulse))
    m = Matrix.LocRotScale(Vector((0,0,0)),q,m.decompose()[2])
    m.translation = center-m.to_3x3()@pivot
    return m

def constrained_blend(a,b,alpha):
    if alpha<=0:return {n:m.copy() for n,m in a.items()}
    if alpha>=1:return {n:m.copy() for n,m in b.items()}
    pose = {}
    for bone in rig.data.bones:
        n = bone.name
        if bone.parent:
            p = bone.parent.name
            pose[n] = pose[p]@blend_matrix(a[p].inverted()@a[n],b[p].inverted()@b[n],alpha)
        else:pose[n] = blend_matrix(a[n],b[n],alpha)
    # The weapon drives both wrists during the carry -> strike transition.
    for side in ('l','r'):
        u,f,h = [n+'_'+side for n in ('upperarm','lowerarm','hand')]
        grip = blend_matrix(a['WPN_root'].inverted()@a[h],b['WPN_root'].inverted()@b[h],alpha)
        hand = pose['WPN_root']@grip
        old = {n:m.copy() for n,m in pose.items()}
        s,e,w = [old[n].translation.copy() for n in (u,f,h)]
        l1,l2 = (e-s).length,(w-e).length
        direction = (hand.translation-s).normalized()
        distance = (hand.translation-s).length
        shift = direction*max(0.,distance-(l1+l2-.001))
        s += shift
        distance = (hand.translation-s).length
        along = (l1*l1-l2*l2+distance*distance)/(2*distance)
        pole = e-s
        pole = (pole-direction*pole.dot(direction)).normalized()
        elbow = s+direction*along+pole*math.sqrt(max(0.,l1*l1-along*along))
        for old_a,old_b,new_a,new_b,names in (
            (old[u].translation,e,s,elbow,(u,'upperarm_twist_01_'+side,'upperarm_twist_02_'+side)),
            (e,w,elbow,hand.translation,(f,'lowerarm_twist_01_'+side,'lowerarm_twist_02_'+side))):
            rotation = (old_b-old_a).rotation_difference(new_b-new_a)
            transform = Matrix.Translation(new_a)@rotation.to_matrix().to_4x4()@Matrix.Translation(-old_a)
            for n in names:pose[n] = transform@old[n]
        pose['clavicle_'+side].translation += shift
        pose[h] = hand
        for bone in rig.data.bones:
            if bone.name.startswith(('thumb','index','middle','ring','pinky')) and bone.name.endswith('_'+side):
                pose[bone.name] = pose[bone.parent.name]@old[bone.parent.name].inverted()@old[bone.name]
    return pose

manifest = {'revision':CFG['revision'],'config':CFG,'runtime_tested':False,'rendered':False,'variants':{}}
for variant in ('Standard','LongGrip'):
    data = json.loads((P/(variant+'_inputs.json')).read_text())
    out = P/variant
    out.mkdir(exist_ok=True)
    idle_world = data['clips']['Idle']['samples'][0]['world']
    idle = from_ue(idle_world)
    ready = idle['WPN_root']
    grips = {s:ready.inverted()@idle['hand_'+s] for s in ('l','r')}
    pivot = (grips['l'].translation+grips['r'].translation)*.5
    ready_center = ready@pivot
    blade_axis = (idle['Blade_Tip'].translation-idle['Blade_Base'].translation).normalized()
    carry_rotation = Quaternion(Vector((0,1,0)),math.radians(CFG['blade_roll_degrees']))@blade_axis.rotation_difference(Vector((0,1,0)))@ready.to_quaternion()
    held = pose_from_weapon(ready_to_carry(1.),1.,{})
    manifest['variants'][variant] = {'folder':data['folder'],'clips':[], 'held_grip_center_m':list((held['hand_l'].translation+held['hand_r'].translation)*.5)}
    clips = [('SprintEnter',round(CFG['entry_seconds']*FPS)),('SprintLoop',CFG['loop_frames']),('SprintExit',round(CFG['exit_seconds']*FPS))]
    actions = {}
    for clip,intervals in clips:
        action = bpy.data.actions.new('A_RuneSword_'+clip+'_'+variant)
        action.use_fake_user = True
        rig.animation_data.action = action
        actions[clip] = action
        scene.render.fps,scene.render.fps_base = FPS,1
        scene.frame_start,scene.frame_end = 0,intervals
        rows,previous,blend_previous,state = [],{},{},{}
        duration = intervals/FPS
        for i in range(intervals+1):
            t = i/FPS
            world = idle_world
            if clip=='SprintEnter':
                w = smooth(t/duration)
                pose = pose_from_weapon(ready_to_carry(w),w,state)
            elif clip=='SprintExit':
                w = 1.-smooth(t/duration)
                pose = pose_from_weapon(ready_to_carry(w),w,state)
            elif clip=='SprintLoop':
                pose = pose_from_weapon(loop_weapon(t,duration),1.,state)
            else:
                row = data['clips']['Overhead']['samples'][i]
                world = row['world']
                original = from_ue(world)
                alpha = smooth((t-CFG['attack_source_start'])/(CFG['attack_join_seconds']-CFG['attack_source_start']))
                pose = constrained_blend(held,original,alpha)
            desired = to_ue(pose,world)
            keys = {}
            for n,m in desired.items():
                parent = data['parents'][n]
                local = desired[parent].inverted()@m if parent in desired else m
                p,q,s = local.decompose()
                if n in previous and q.dot(previous[n])<0:q.negate()
                previous[n] = q.copy()
                keys[n] = {'p':list(p),'q':list(q),'s':list(s)}
            rows.append({'seconds':t,'bones':keys})
            scene.frame_set(i)
            for bone in rig.pose.bones:
                parent = pose[bone.parent.name] if bone.parent else Matrix.Identity(4)
                bone.matrix_basis = local_rest[bone.name].inverted()@parent.inverted()@pose[bone.name]
                bone.rotation_mode = 'QUATERNION'
                q = bone.rotation_quaternion.copy()
                if bone.name in blend_previous and q.dot(blend_previous[bone.name])<0:q.negate()
                bone.rotation_quaternion = q
                blend_previous[bone.name] = q.copy()
                for channel in ('location','rotation_quaternion','scale'):bone.keyframe_insert(channel,frame=i,group=bone.name)
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        for k in curve.keyframe_points:k.interpolation='LINEAR'
        target = data['folder']+'/TacticalSprint20260921/A_RuneSword_'+clip
        patch = {'revision':CFG['revision'],'asset':target,'source':data['clips']['Overhead' if clip=='SprintOverhead' else 'Idle']['asset'],
                 'mesh':data['mesh'],'fps':FPS,'seconds':duration,'intervals':intervals,'samples':rows}
        (out/(clip+'_keys.json')).write_text(json.dumps(patch,separators=(',',':')),encoding='utf-8')
        manifest['variants'][variant]['clips'].append({'clip':clip,'asset':target,'seconds':duration,'frames':intervals+1})
        print('MELEE_SPRINT_AUTHORED '+variant+'/'+clip,flush=True)
    rig.animation_data.action = actions['SprintLoop']
    rig.animation_data.action_slot = actions['SprintLoop'].slots[0]
    scene.frame_start,scene.frame_end = 0,CFG['loop_frames']
    scene.frame_set(0)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'Sword_TacticalSprint_Editable.blend'))
(P/'authoring.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
