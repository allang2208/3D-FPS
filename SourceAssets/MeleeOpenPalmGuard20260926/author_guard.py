"""Author native guard tracks and editable V7 bare-arm scenes; no rendering.

UE component poses are mapped to the visible armature through reference-pose
deformation, not by assuming its reconstructed bone axes match the native rig.
Only Guard, GuardHit and GuardBreak tracks are replaced, at their original rates.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

P = Path(__file__).parent
ROOT = P.parents[1]
CFG = json.loads((P / 'pose_config.json').read_text())
SOURCE = ROOT / 'SourceAssets/ModularOutfit20260925/BarePalmV7/Editable/RuneSword_BareArmsV7.blend'
ONE = Vector((1, 1, 1))
C = Matrix.Diagonal(Vector((1, -1, 1)))
bpy.context.preferences.filepaths.save_version = 0


def ease(t):
    t = max(0.0, min(1.0, t))
    return t*t*t*(t*(t*6.0-15.0)+10.0)


def transform(p, q):
    return Matrix.LocRotScale(p, q, ONE)


def blend(a, b, w):
    return transform(a.translation.lerp(b.translation, w), a.to_quaternion().slerp(b.to_quaternion(), w))


def frame(forward, normal):
    x = forward.normalized()
    z = (normal-x*normal.dot(x)).normalized()
    return Matrix((x, x.cross(z), z)).transposed()


for variant in ('Standard', 'LongGrip'):
    data = json.loads((P / (variant + '_active.json')).read_text())
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    scene = bpy.context.scene
    rig = bpy.data.objects['RuneSword_NativeReference']
    rig.animation_data_create()
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    parents = data['parents']
    names = data['bones']
    ref = data['reference']
    rest_local = {n: rest[parents[n]].inverted() @ rest[n] if parents[n] in rest else rest[n] for n in names}
    # Bpose = reflected native deformation * visible authoring reference frame.
    basis = {n: Quaternion(ref[n]['q']).to_matrix().transposed() @ C @ rest[n].to_3x3() for n in names}

    def from_ue(world):
        return {n: transform(C @ Vector(k['p']) * .01,
                            (C @ Quaternion(k['q']).to_matrix() @ basis[n]).to_quaternion())
                for n, k in world.items()}

    def native_keys(pose, original):
        native = {}
        for n, m in pose.items():
            native[n] = {'p': C @ m.translation * 100.0,
                         'q': (C @ m.to_3x3() @ basis[n].transposed()).to_quaternion(),
                         's': Vector(original[n]['s'])}
        result = {}
        for n, k in native.items():
            parent = parents[n]
            if parent in native:
                a = native[parent]
                iq = a['q'].inverted()
                offset = iq @ (k['p']-a['p'])
                p = Vector(tuple(offset[i]/a['s'][i] for i in range(3)))
                q = iq @ k['q']
                s = Vector(tuple(k['s'][i]/a['s'][i] for i in range(3)))
            else:
                p, q, s = k['p'], k['q'], k['s']
            result[n] = {'p': list(p), 'q': list(q), 's': list(s)}
        return result

    held = from_ue(data['clips']['Guard']['samples'][-1]['world'])
    blade_direction = (held['Blade_Tip'].translation-held['Blade_Base'].translation).normalized()
    projected = Vector((blade_direction.x, 0, blade_direction.z)).normalized()
    lean = math.radians(CFG['blade_toward_player_degrees'])
    desired_direction = projected*math.cos(lean)+Vector((0, -math.sin(lean), 0))
    tilt = blade_direction.rotation_difference(desired_direction)
    target_sword = transform(held['WPN_root'].translation, tilt @ held['WPN_root'].to_quaternion())
    sword_rotation_offset = held['WPN_root'].to_quaternion().inverted() @ target_sword.to_quaternion()

    wrist0 = rest['hand_l'].translation
    normal0 = (rest['pinky_01_l'].translation-wrist0).cross(rest['index_01_l'].translation-wrist0).normalized()
    palm0 = frame(rest['middle_01_l'].translation-wrist0, normal0)
    # The existing blade broad face, transported by the new inward tilt.
    face_normal = tilt @ Vector((0.0, .8, -.6))
    face_normal = (face_normal-desired_direction*face_normal.dot(desired_direction)).normalized()
    palm = frame(Vector(CFG['palm_forward']), face_normal)
    hand_rotation = (palm @ palm0.transposed() @ rest['hand_l'].to_3x3()).to_quaternion()
    contact = target_sword.translation+desired_direction*CFG['palm_contact_distance_m']
    target_hand = transform(contact-palm @ Vector((CFG['palm_pad_forward_m'], 0, CFG['palm_pad_depth_m'])), hand_rotation)
    palm_to_sword = target_sword.inverted() @ target_hand
    finger_names = [n for n in names if n.endswith('_l') and n.startswith(('index', 'middle', 'ring', 'pinky', 'thumb'))]

    # Anatomical curl/spread, using measured phalange directions instead of
    # arbitrary reconstructed rig axes. Flex angles are cumulative per digit.
    finger_pose = {n: m.copy() for n, m in rest.items()}
    for n in finger_names:
        parent = parents[n]
        m = finger_pose[parent] @ rest_local[n]
        parts = n.split('_')
        if len(parts) == 3 and parts[1].isdigit():
            k = int(parts[1])-1
            digit = CFG['open_fingers'][parts[0]]
            next_name = f'{parts[0]}_{k+2:02d}_l'
            direction = rest[next_name].translation-rest[n].translation if next_name in rest else rest[n].translation-rest[parent].translation
            spread = digit['spread'][k] if isinstance(digit['spread'], list) else digit['spread']
            angle = math.radians(spread)
            neutral = frame(palm0 @ Vector((math.cos(angle), math.sin(angle), 0)), normal0)
            curl = Quaternion(neutral.col[1], math.radians(digit['flex'][k]))
            goal = curl.to_matrix() @ neutral
            q = (goal @ frame(direction, normal0).transposed() @ rest[n].to_3x3()).to_quaternion()
            m = transform(m.translation, q)
        finger_pose[n] = m
    open_fingers = {n: finger_pose[parents[n]].inverted() @ finger_pose[n] for n in finger_names}

    edited = {'WPN_root'}
    for side in ('l', 'r'):
        edited.update(part+'_'+side for part in ('clavicle', 'upperarm', 'lowerarm', 'hand',
                                                'upperarm_twist_01', 'upperarm_twist_02',
                                                'lowerarm_twist_01', 'lowerarm_twist_02'))
    edited.update(finger_names)
    edited = [n for n in names if n in edited]

    def solve_arm(pose, source, side, hand, weight):
        upper, fore, wrist = (p+'_'+side for p in ('upperarm', 'lowerarm', 'hand'))
        a = source[upper].translation
        h = hand.translation
        ru = rest[fore].translation-rest[upper].translation
        rf = rest[wrist].translation-rest[fore].translation
        l1 = (source[fore].translation-a).length
        l2 = (source[wrist].translation-source[fore].translation).length
        reach = h-a
        distance = reach.length
        if distance >= l1+l2 or distance <= abs(l1-l2):
            raise RuntimeError('Authored wrist is outside the arm reach: '+side)
        axis = reach.normalized()
        guide = source[fore].translation
        if side == 'l':
            guide = guide.lerp(Vector(CFG['left_elbow_guide_m']), weight)
        pole = guide-a-axis*(guide-a).dot(axis)
        pole.normalize()
        along = (l1*l1-l2*l2+distance*distance)/(2*distance)
        elbow = a+axis*along+pole*math.sqrt(max(0.0, l1*l1-along*along))
        ud, fd = (elbow-a).normalized(), (h-elbow).normalized()
        hand_deform = hand.to_quaternion() @ rest[wrist].to_quaternion().inverted()
        fore_deform = (hand_deform @ rf.normalized()).rotation_difference(fd) @ hand_deform
        fore_goal = fore_deform @ rest[fore].to_quaternion()
        source_fd = (source[wrist].translation-source[fore].translation).normalized()
        fore_transport = source_fd.rotation_difference(fd) @ source[fore].to_quaternion()
        fore_q = fore_transport.slerp(fore_goal, weight)
        # Carry the forearm's roll back to the upper arm by shortest swing.
        # This avoids introducing a separate bend-plane frame that twists the
        # elbow seam even when the joint centers look plausible.
        coherent_deform = fore_q @ rest[fore].to_quaternion().inverted()
        upper_goal = ((coherent_deform @ ru.normalized()).rotation_difference(ud)
                      @ coherent_deform @ rest[upper].to_quaternion())
        source_ud = (source[fore].translation-a).normalized()
        upper_transport = source_ud.rotation_difference(ud) @ source[upper].to_quaternion()
        upper_q = upper_transport.slerp(upper_goal, weight)
        pose[upper] = transform(a, upper_q)
        pose[fore] = transform(elbow, fore_q)
        pose[wrist] = hand
        pose['clavicle_'+side] = pose[upper] @ source[upper].inverted() @ source['clavicle_'+side]
        for segment in ('upperarm', 'lowerarm'):
            parent = segment+'_'+side
            for station in ('01', '02'):
                name = f'{segment}_twist_{station}_{side}'
                before = source[parent].inverted() @ source[name]
                support = rest[parent].inverted() @ rest[name]
                pose[name] = pose[parent] @ blend(before, support, weight)

    actions = {}
    author_record = {'variant': variant, 'revision': CFG['revision'], 'clips': {},
                     'editable_visible_mesh': str(SOURCE), 'rendered_or_tested': False}
    out = P / variant
    out.mkdir(exist_ok=True)
    for clip in ('Guard', 'GuardHit', 'GuardBreak'):
        original = data['clips'][clip]
        frames, keyframes = [], []
        for sample in original['samples']:
            t = sample['seconds']
            if clip == 'Guard':
                weight = ease(t/original['seconds'])
                finger_weight = ease(t/.14)
            elif clip == 'GuardHit':
                weight = finger_weight = 1.0
            else:
                weight = 1.0-ease((t-.105)/(original['seconds']-.105))
                finger_weight = 1.0-ease((t-.24)/(original['seconds']-.24))
            source = from_ue(sample['world'])
            pose = {n: m.copy() for n, m in source.items()}
            if weight > 0 or finger_weight > 0:
                original_local = {n: source[parents[n]].inverted() @ source[n] if parents[n] in source else source[n] for n in names}
                sword = source['WPN_root'].copy()
                sword = transform(sword.translation, sword.to_quaternion() @ Quaternion().slerp(sword_rotation_offset, weight))
                pose['WPN_root'] = sword
                right_hand = sword @ source['WPN_root'].inverted() @ source['hand_r']
                left_hand = blend(source['hand_l'], sword @ palm_to_sword, weight)
                solve_arm(pose, source, 'r', right_hand, weight)
                solve_arm(pose, source, 'l', left_hand, weight)
                for n in names:
                    parent = parents[n]
                    if n in finger_names:
                        pose[n] = pose[parent] @ blend(original_local[n], open_fingers[n], finger_weight)
                    elif n not in edited and parent in pose:
                        pose[n] = pose[parent] @ original_local[n]
            frames.append(pose)
            keys = native_keys(pose, sample['world'])
            keyframes.append({'seconds': t, 'bones': {n: keys[n] for n in edited}})

        patch = {'revision': CFG['revision'], 'asset': original['asset'], 'source_sha256': original['source_sha256'],
                 'seconds': original['seconds'], 'intervals': original['intervals'],
                 'edited_bones': edited, 'samples': keyframes}
        (out / (clip+'_patch.json')).write_text(json.dumps(patch, separators=(',', ':')), encoding='utf-8')

        action = bpy.data.actions.new('A_RuneSword_'+clip)
        action.use_fake_user = True
        rig.animation_data.action = action
        previous = {}
        for f, pose in enumerate(frames):
            for n in names:
                b = rig.pose.bones[n]
                parent = parents[n]
                local = pose[parent].inverted() @ pose[n] if parent in pose else pose[n]
                loc, q, scale = (rest_local[n].inverted() @ local).decompose()
                if n in previous and q.dot(previous[n]) < 0:
                    q.negate()
                previous[n] = q.copy()
                b.rotation_mode = 'QUATERNION'
                b.location, b.rotation_quaternion, b.scale = loc, q, scale
                for channel in ('location', 'rotation_quaternion', 'scale'):
                    b.keyframe_insert(channel, frame=f, group=n)
        rig.animation_data.action_slot = action.slots[0]
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        for key in curve.keyframe_points:
                            key.interpolation = 'LINEAR'
        actions[clip] = action
        author_record['clips'][clip] = {'asset': original['asset'], 'seconds': original['seconds'],
                                       'frames': len(frames), 'source_sha256': original['source_sha256']}
        print('OPEN_PALM_AUTHORED '+variant+' '+clip, flush=True)

    rig.animation_data.action = actions['Guard']
    rig.animation_data.action_slot = actions['Guard'].slots[0]
    scene.render.fps = round(data['clips']['Guard']['intervals']/data['clips']['Guard']['seconds'])
    scene.render.fps_base = 1.0
    scene.frame_start = 0
    scene.frame_end = data['clips']['Guard']['intervals']
    scene.frame_set(scene.frame_end)
    # The real accepted V7 skin is kept in each source; no proxy arms or meshes.
    bpy.ops.wm.save_as_mainfile(filepath=str(out / (variant+'_OpenPalmGuard_Editable.blend')))
    (out / 'authoring.json').write_text(json.dumps(author_record, indent=2), encoding='utf-8')
print('OPEN_PALM_AUTHORING_COMPLETE', flush=True)
