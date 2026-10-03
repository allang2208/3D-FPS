"""Lower the uppercut finish, keep its tip up, and rebuild supported arm rotation."""
from pathlib import Path
import numpy as np

P = Path(__file__).resolve().parent
exec(compile((P/'author_common.py').read_text('utf-8'),str(P/'author_common.py'),'exec'))

REVISION = 'SupportedFinishUppercutV13'
TIP_DIRECTION = Vector((-.14,.32,.937)).normalized()
HOLD_START, HOLD_END = 111, 128
ROOT_BONE = next(n for n in NAMES if PARENTS[n] not in PARENTS)

def frame(axis,normal):
    x = axis.normalized()
    z = (normal-x*normal.dot(x)).normalized()
    return Matrix((x,z.cross(x).normalized(),z)).transposed().to_quaternion()

def axis_angle(q,axis):
    a = 2.*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w)
    return (a+math.pi)%(2.*math.pi)-math.pi

def near_angle(a,old):
    return a+round((old-a)/(2.*math.pi))*2.*math.pi

def pose_from_rows(rows):
    return {n:canonical(m) for n,m in globalize({n:native(k) for n,k in rows.items()}).items()}

def fit_skin_stations(objects,reference,side):
    """Fit incremental rotation to the current V7 skin weights, not bone heads."""
    lo,hand = 'lowerarm_'+side,'hand_'+side
    order = [lo,'lowerarm_twist_02_'+side,'lowerarm_twist_01_'+side]
    e,h = reference[lo].translation,reference[hand].translation
    axis = (h-e).normalized()
    length = (h-e).length
    rows,targets = [],[]
    for obj in objects:
        groups = {g.index:g.name for g in obj.vertex_groups}
        for vertex in obj.data.vertices:
            weights = {groups[g.group]:g.weight for g in vertex.groups}
            if sum(weights.get(n,0.) for n in order)<.25:continue
            t = (obj.matrix_world@vertex.co-e).dot(axis)/length
            if not .035<t<.98:continue
            rows.append([weights.get(n,0.) for n in order])
            targets.append(t-weights.get(hand,0.))
    coeff = np.linalg.lstsq(np.asarray(rows),np.asarray(targets),rcond=None)[0]
    # The elbow cap carries no added pronation. Fit the forearm stations from
    # the surface, retain increasing rotation towards the fixed hand endpoint.
    coeff[0] = 0.
    coeff[1] = np.clip(coeff[1],.15,.48)
    coeff[2] = np.clip(coeff[2],max(.65,coeff[1]+.2),.95)
    return dict(zip(order,[float(v) for v in coeff]))

def solve_supported_arm(pose,idle,source,side,weight,state,skin):
    """Choose a continuous elbow plane, then distribute only axial palm roll.

    Upper arm and elbow cap share the transported idle hinge. Palm rotation is
    separated from wrist bending and spread using the skin's support weights.
    All hand/finger world transforms remain the authored grip transforms.
    """
    if weight<=1.e-8:return
    n = lambda stem:stem+'_'+side
    un,ln,hn = n('upperarm'),n('lowerarm'),n('hand')
    s0,e0,h0 = (idle[k].translation for k in (un,ln,hn))
    u0,l0 = e0-s0,h0-e0
    a,b = u0.length,l0.length
    neutral_plane = u0.cross(l0).normalized()
    neutral_axis = (h0-s0).normalized()
    neutral_pole = (e0-s0-neutral_axis*(e0-s0).dot(neutral_axis)).normalized()
    root_offset = pose[ROOT_BONE].translation-idle[ROOT_BONE].translation
    shoulder = source[un].translation.lerp(s0+root_offset,weight)
    hand = pose[hn].translation
    reach = hand-shoulder
    # A supported 36 degree elbow avoids the nearly straight IK singularity.
    max_reach = math.sqrt(a*a+b*b+2*a*b*math.cos(math.radians(36)))
    if reach.length>max_reach:
        shoulder += reach.normalized()*(reach.length-max_reach)
    axis = (hand-shoulder).normalized()
    d = (hand-shoulder).length
    along = (a*a-b*b+d*d)/(2*d)
    radius = math.sqrt(max(0.,a*a-along*along))
    base_pole = neutral_axis.rotation_difference(axis)@neutral_pole
    hand_delta = pose[hn].to_quaternion()@idle[hn].to_quaternion().inverted()
    wrist_axis = (hand_delta@l0).normalized()
    old_angle,old_roll = state['pole'],state['roll']

    def candidate(degrees):
        pole = Quaternion(axis,math.radians(degrees))@base_pole
        elbow = shoulder+axis*along+pole*radius
        upper,lower = elbow-shoulder,hand-elbow
        plane = upper.cross(lower).normalized()
        du = frame(upper,plane)@frame(u0,neutral_plane).inverted()
        # Move the forearm by elbow flexion without adding another axial roll.
        df = (du@l0.normalized()).rotation_difference(lower.normalized())@du
        hand_frame = (hand_delta@l0.normalized()).rotation_difference(lower.normalized())@hand_delta
        phi = near_angle(axis_angle(hand_frame@df.inverted(),lower.normalized()),old_roll)
        wrist_bend = math.degrees(lower.normalized().angle(wrist_axis))
        upper_swing = u0.normalized().rotation_difference(upper.normalized())
        upper_roll = math.degrees(axis_angle(du@upper_swing.inverted(),upper.normalized()))
        cost = (max(0.,abs(math.degrees(phi))-65.)/22.)**2
        cost += (max(0.,wrist_bend-28.)/17.)**2
        cost += (max(0.,abs(upper_roll)-60.)/25.)**2
        cost += .09*(degrees/60.)**2 + .06*((degrees-old_angle)/12.)**2
        # Keep the elbow supported below the hand and outside its own shoulder.
        cost += (max(0.,elbow.z-hand.z+.015)/.06)**2
        toward_other_arm = (elbow.x-shoulder.x)*(1 if side=='l' else -1)
        cost += .35*(max(0.,toward_other_arm-.04)/.10)**2
        return cost,elbow,du,df,phi,wrist_bend

    # Bound pole motion in author time, then refine continuously; no per-frame
    # coarse angle switching and no half-turn branch changes at the wrist.
    left,right = max(-80.,old_angle-10.),min(80.,old_angle+10.)
    chosen = min(np.linspace(left,right,11),key=lambda x:candidate(float(x))[0])
    left,right = max(left,chosen-2.),min(right,chosen+2.)
    for _ in range(18):
        x,y = left+(right-left)/3.,right-(right-left)/3.
        if candidate(x)[0]<candidate(y)[0]:right=y
        else:left=x
    angle = (left+right)*.5
    _,target_elbow,du,df,phi,bend = candidate(angle)
    # At clip seams retain the original elbow side continuously on the IK circle.
    old_vec = source[ln].translation-shoulder
    old_pole = old_vec-axis*old_vec.dot(axis)
    old_pole.normalize()
    new_pole = (target_elbow-shoulder-axis*along).normalized()
    turn = Quaternion().slerp(old_pole.rotation_difference(new_pole),weight)
    elbow = shoulder+axis*along+(turn@old_pole)*radius
    upper,lower = elbow-shoulder,hand-elbow
    plane = upper.cross(lower).normalized()
    du = frame(upper,plane)@frame(u0,neutral_plane).inverted()
    df = (du@l0.normalized()).rotation_difference(lower.normalized())@du
    hand_frame = (hand_delta@l0.normalized()).rotation_difference(lower.normalized())@hand_delta
    phi = near_angle(axis_angle(hand_frame@df.inverted(),lower.normalized()),old_roll)
    state.update(pole=angle,roll=phi)
    for bone,position,q,old_direction,new_direction in (
        (un,shoulder,du@idle[un].to_quaternion(),source[ln].translation-source[un].translation,upper),
        (ln,elbow,df@idle[ln].to_quaternion(),source[hn].translation-source[ln].translation,lower)):
        aligned = old_direction.rotation_difference(new_direction)@source[bone].to_quaternion()
        pose[bone] = mat(position,aligned.slerp(q,weight),idle[bone].to_scale())
    for num in ('01','02'):
        bone = n('upperarm_twist_'+num)
        target_q = du@idle[bone].to_quaternion()
        inherited = pose[un].to_quaternion()@source[un].to_quaternion().inverted()
        source_q = inherited@source[bone].to_quaternion()
        pose[bone] = mat(shoulder+du@(idle[bone].translation-s0),source_q.slerp(target_q,weight),idle[bone].to_scale())
        bone = n('lowerarm_twist_'+num)
        target_q = Quaternion(lower.normalized(),phi*skin[bone])@df@idle[bone].to_quaternion()
        inherited = (source[hn].translation-source[ln].translation).rotation_difference(lower)
        source_q = inherited@source[bone].to_quaternion()
        pose[bone] = mat(elbow+df@(idle[bone].translation-e0),source_q.slerp(target_q,weight),idle[bone].to_scale())
    pose[n('clavicle')] = source[n('clavicle')].copy()
    pose[n('clavicle')].translation += shoulder-source[un].translation

receipts = {}
for variant in ('Standard','LongGrip'):
    source_path = P/'SourceV12'/variant/'editable_keys.json'
    accepted = json.loads(source_path.read_text('utf-8'))
    idle = pose_from_rows(accepted['samples'][0]['bones'])
    peak = pose_from_rows(accepted['samples'][HOLD_START]['bones'])
    peak_axis = (peak['Blade_Tip'].translation-peak['Blade_Base'].translation).normalized()
    finish_turn = peak_axis.rotation_difference(TIP_DIRECTION)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    rig = next(o for o in scene.objects if o.type=='ARMATURE')
    rig.animation_data_clear()
    rest = {b.name:b.matrix_local.copy() for b in rig.data.bones}
    local_rest = {n:rest[PARENTS[n]].inverted()@m if PARENTS[n] in rest else m for n,m in rest.items()}
    reference = {n:canonical(native(row)) for n,row in DATA['reference'].items()}
    correction = {n:reference[n].inverted()@rest[n] for n in rest}
    objects = [o for o in scene.objects if o.type=='MESH']
    stations = {s:fit_skin_stations(objects,reference,s) for s in ('l','r')}
    states = {s:dict(pole=0.,roll=0.) for s in ('l','r')}
    rig.animation_data_create()
    action = bpy.data.actions.new('Sword_UppercutV13_'+variant)
    action.use_fake_user = True
    rig.animation_data.action = action
    samples,previous,blend_previous = [],{},{}
    for i in range(FRAMES+1):
        source_frame = i if i<=HOLD_START else (HOLD_START if i<=HOLD_END else HOLD_START+(i-HOLD_END)*(FRAMES-HOLD_START)/(FRAMES-HOLD_END))
        rows = sample_keys(accepted['samples'],source_frame/FPS)
        base = pose_from_rows(rows)
        pose = {n:m.copy() for n,m in base.items()}
        finish_weight = smooth((i-96)/(HOLD_START-96)) if i<=HOLD_START else (1. if i<=HOLD_END else 1.-smooth((i-HOLD_END)/(FRAMES-HOLD_END)))
        pivot = (base['hand_l'].translation+base['hand_r'].translation)*.5
        rotation = Quaternion().slerp(finish_turn,finish_weight)
        carry = Matrix.Translation(pivot+Vector((0.,0.,-.12*finish_weight)))@rotation.to_matrix().to_4x4()@Matrix.Translation(-pivot)
        for n in WEAPON|HANDS['l']|HANDS['r']:pose[n] = carry@base[n]
        supported = smooth(i/24)*(1.-smooth((i-160)/(FRAMES-160)))
        for side in ('l','r'):solve_supported_arm(pose,idle,base,side,supported,states[side],stations[side])
        ue = {n:mat(C@m.translation*100,(C@m.to_quaternion().to_matrix()@C).to_quaternion(),m.to_scale()) for n,m in pose.items()}
        keys = {}
        for n,m in localize(ue).items():
            p,q,s = m.decompose()
            if n in previous and q.dot(previous[n])<0:q = -q
            keys[n] = dict(p=list(p),q=list(q),s=list(s))
            if n in (HANDS['l']-{'hand_l'})|(HANDS['r']-{'hand_r'}):keys[n] = rows[n]
            previous[n] = Quaternion(keys[n]['q'])
        if i in (0,FRAMES):keys = rows
        samples.append(dict(seconds=i/FPS,source_seconds=source_frame/FPS,bones=keys))
        scene.frame_set(i)
        worlds = {n:pose[n]@correction[n] for n in rest}
        for bone in rig.pose.bones:
            parent_world = worlds[bone.parent.name] if bone.parent else Matrix.Identity(4)
            bone.matrix_basis = local_rest[bone.name].inverted()@parent_world.inverted()@worlds[bone.name]
            bone.rotation_mode = 'QUATERNION'
            q = bone.rotation_quaternion.copy()
            if bone.name in blend_previous and q.dot(blend_previous[bone.name])<0:q = -q
            bone.rotation_quaternion = q
            blend_previous[bone.name] = q.copy()
            for channel in ('location','rotation_quaternion','scale'):bone.keyframe_insert(channel,frame=i,group=bone.name)
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
    patch = dict(revision=REVISION,variant=variant,source_keys=str(source_path),fps=FPS,
        intervals=FRAMES,seconds=FRAMES/FPS,release_seconds=.8,main_stroke_seconds=.075,
        finish_drop_m=.12,finish_blade_direction=list(TIP_DIRECTION),skin_stations=stations,
        finish_hold_seconds=[HOLD_START/FPS,HOLD_END/FPS],samples=samples)
    (out/'editable_keys.json').write_text(json.dumps(patch,separators=(',',':')),encoding='utf-8')
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'Sword_UppercutV13_Editable.blend'))
    receipts[variant] = {k:v for k,v in patch.items() if k!='samples'}
    print('UPPERCUT_V13_AUTHORED '+variant,flush=True)
(P/'authoring.json').write_text(json.dumps(dict(revision=REVISION,variants=receipts,
    method='Lower grip finish; tip-up inclined stop; idle hinge transport; continuous elbow placement; palm roll distributed by V7 skin support',
    runtime_tested=False,rendered=False,paid_motion_used=False),ensure_ascii=False,indent=2),encoding='utf-8')
