"""Native V7 forge motion, matching ForgeInteraction's anatomical hammer hinge."""
import math
import bpy
from mathutils import Matrix, Vector, Quaternion


def frame(x, z, position):
    x = Vector(x).normalized()
    z = Vector(z)
    z = (z - x * x.dot(z)).normalized()
    result = Matrix((x, z.cross(x).normalized(), z)).transposed().to_4x4()
    result.translation = Vector(position)
    return result


def bake_motion(scene, rig, hammer, tongs, reference, data, quench=False):
    mirror = Matrix.Diagonal((1, -1, 1, 1))
    parents = {n: rig.data.bones[n].parent.name if rig.data.bones[n].parent else None for n in reference}
    order = [bone.name for bone in rig.data.bones if bone.name in reference]
    local = {n: reference[parents[n]].inverted() @ reference[n] if parents[n] else reference[n] for n in order}
    layout = data['station_layout']
    body = Matrix.Translation(Vector(layout['body_origin_cm']) * .01) @ Matrix.Rotation(math.pi, 4, 'Z')
    camera = Vector((.29, -.43, 1.48))
    half_fov = math.radians(33.5)
    forward = (Vector((.29, .22, .92)) - camera).normalized()
    grasp = {s: Matrix.LocRotScale(Vector(v['p']) * .01, Quaternion((v['q'][3], *v['q'][:3])), Vector((1, 1, 1))) for s, v in data['hands'].items()}

    def solve(pose, side, hand):
        upper, lower, wrist, clavicle = [n + '_' + side for n in ('upperarm', 'lowerarm', 'hand', 'clavicle')]
        shoulder = pose[upper].translation.copy()
        target = hand.translation
        ref_upper = reference[lower].translation - reference[upper].translation
        ref_lower = reference[wrist].translation - reference[lower].translation
        hand_deform = hand.to_quaternion() @ reference[wrist].to_quaternion().inverted()
        outward = Vector((0, 0, 1)).cross(forward).normalized() * (1 if side == 'r' else -1)
        clearance = (outward - forward * math.tan(half_fov)).normalized()
        pronation = math.pi * .5
        if side == 'r':
            native_lower = ref_lower.normalized()
            native_hinge = ref_upper.cross(ref_lower).normalized()
            bend_axis = hand_deform @ (Quaternion(native_lower, math.radians(15)) @ native_hinge)
            wrist_aligned = Quaternion(bend_axis, math.radians(30)) @ hand_deform
            lower_direction = wrist_aligned @ native_lower
            lower_deform = Quaternion(lower_direction, pronation) @ wrist_aligned
            hinge = lower_deform @ native_hinge
            elbow = target - lower_direction * ref_lower.length
            wanted_upper = (elbow - shoulder).normalized()
            tangent = lower_direction.cross(hinge)
            wanted_flex = math.atan2(wanted_upper.dot(tangent), wanted_upper.dot(lower_direction))
            required_reach = max(0, .105 - (target - camera).dot(clearance)) + .01
            reach_flex = math.acos(max(-1, min(1, (required_reach**2 - ref_upper.length_squared - ref_lower.length_squared) / (2 * ref_upper.length * ref_lower.length))))
            max_flex = min(math.radians(110), reach_flex)
            flex = max(min(math.radians(45), max_flex), min(max_flex, wanted_flex))
            native_flex = ref_upper.angle(ref_lower)
            upper_deform = Quaternion(hinge, native_flex - flex) @ lower_deform
            supported = elbow - upper_deform @ ref_upper
            # Swing the complete hinge chain for camera clearance; never move
            # its shoulder independently and reconstruct an unconstrained elbow.
            support = supported - target
            support_direction = support.normalized()
            side_limit = max(-1, min(1, (.105 - (target - camera).dot(clearance)) / support.length))
            if support_direction.dot(clearance) < side_limit:
                tangent = (support_direction - clearance * support_direction.dot(clearance)).normalized()
                safe_direction = clearance * side_limit + tangent * math.sqrt(max(0, 1 - side_limit * side_limit))
                chain_swing = support_direction.rotation_difference(safe_direction)
                supported = target + chain_swing @ support
                elbow = target + chain_swing @ (elbow - target)
                lower_direction = chain_swing @ lower_direction
                lower_deform = chain_swing @ lower_deform
                upper_deform = chain_swing @ upper_deform
        else:
            # Keep the tong arm on its existing solve.
            neutral = hand_deform @ ref_lower.normalized()
            reach = (target - shoulder).normalized()
            bend = math.acos(max(-1, min(1, neutral.dot(reach))))
            fraction = min(1, math.radians(12) / bend) if bend > .0001 else 0
            lower_direction = Quaternion().slerp(neutral.rotation_difference(reach), fraction) @ neutral
            reach_limit = max(-1, min(1, ((target - camera).dot(clearance) + ref_upper.length - .105 - .01) / ref_lower.length))
            if lower_direction.dot(clearance) > reach_limit:
                tangent = (lower_direction - clearance * lower_direction.dot(clearance)).normalized()
                lower_direction = clearance * reach_limit + tangent * math.sqrt(max(0, 1 - reach_limit * reach_limit))
            elbow = target - lower_direction * ref_lower.length
            support = (shoulder - elbow).normalized()
            side_limit = max(-1, min(1, (.105 - (elbow - camera).dot(clearance)) / ref_upper.length))
            if support.dot(clearance) < side_limit:
                tangent = (support - clearance * support.dot(clearance)).normalized()
                support = clearance * side_limit + tangent * math.sqrt(max(0, 1 - side_limit * side_limit))
            supported = elbow + support * ref_upper.length
            upper_direction = (elbow - supported).normalized()
            lower_deform = neutral.rotation_difference(lower_direction) @ hand_deform
            upper_deform = (lower_deform @ ref_upper.normalized()).rotation_difference(upper_direction) @ lower_deform
        clavicle_offset = reference[clavicle].translation - reference[upper].translation
        pose[clavicle] = Matrix.LocRotScale(supported + upper_deform @ clavicle_offset,
                                           upper_deform @ reference[clavicle].to_quaternion(), Vector((1, 1, 1)))
        pose[upper] = Matrix.LocRotScale(supported, upper_deform @ reference[upper].to_quaternion(), Vector((1, 1, 1)))
        pose[lower] = Matrix.LocRotScale(elbow, lower_deform @ reference[lower].to_quaternion(), Vector((1, 1, 1)))
        pose[wrist] = hand
        for name in order:
            if not name.endswith('_' + side) or name in (upper, lower, wrist, clavicle):
                continue
            parent = parents[name]
            if not parent:
                continue
            if side == 'r' and parent == lower and name.startswith('lowerarm_twist_'):
                # Pure axial pronation only, not a fraction of the wrist's full
                # bend. Both helpers are siblings; author in component space.
                offset = reference[name].translation - reference[lower].translation
                along = max(0, min(1, offset.dot(ref_lower) / ref_lower.length_squared))
                deform = Quaternion(lower_direction, -pronation * along) @ lower_deform
                pose[name] = Matrix.LocRotScale(elbow + deform @ offset,
                                               deform @ reference[name].to_quaternion(), Vector((1, 1, 1)))
                continue
            transform = local[name].copy()
            if name in data['finger_rotations']:
                q = data['finger_rotations'][name]
                transform = Matrix.LocRotScale(transform.translation, Quaternion((q[3], *q[:3])), Vector((1, 1, 1)))
            pose[name] = pose[parent] @ transform

    impact = frame((0, 0, -1), layout['hammer_axis'], (0, 0, 0))
    contact = Vector(data['hammer_contact_cm']) * .01
    hit = Vector((.29, .22, .9195))
    tong = frame((0, 0, -1), layout['tong_axis'], (0, 0, 0))
    tong.translation = Vector((.53, .22, .91475)) - tong.to_3x3() @ Vector((0, 0, .254))
    for obj in (rig, hammer, tongs):
        obj.animation_data_clear()
    scene.render.fps = 100
    scene.frame_start = 0
    scene.frame_end = round((5.8 if quench else data['stroke_seconds']) * scene.render.fps)
    def ease(t):
        t=max(0,min(1,t));return t*t*(3-2*t)
    blank=bpy.data.objects.get('SM_ForgeBlank2') if quench else None
    view=None
    if quench:
        cam_data=bpy.data.cameras.new('QuenchCamera');view=bpy.data.objects.new('QuenchCamera',cam_data)
        scene.collection.objects.link(view);scene.camera=view
        if blank:blank.animation_data_clear();blank.hide_set(False)
    for index in range(scene.frame_end + 1):
        scene.frame_set(index)
        age=index / scene.render.fps
        time = 0 if quench else age
        key = data['stroke'][-1]
        for previous, following in zip(data['stroke'], data['stroke'][1:]):
            if time <= following['t']:
                alpha = max(0, min(1, (time - previous['t']) / (following['t'] - previous['t'])))
                alpha = alpha * alpha * (3 - 2 * alpha)
                key = {'angle': previous['angle'] * (1-alpha) + following['angle'] * alpha,
                       'offset': Vector(previous['offset']).lerp(Vector(following['offset']), alpha)}
                break
        tool = impact @ Matrix.Rotation(math.radians(key['angle']), 4, 'Y')
        tool.translation = hit - impact.to_3x3() @ contact + Vector(key['offset']) * .01
        work=None
        if quench:
            lift=ease(age/.55);transfer=ease((age-.5)/1.);dip=ease((age-1.5)/.65);raise_up=ease((age-3.95)/.7)
            surface=Vector((.42,-.30,.46))
            work=Matrix.Rotation(math.radians(-76*transfer),4,'Y')@Matrix.Rotation(math.radians(layout['work_yaw']),4,'Z')
            work.translation=(Vector((.29,.22,.91))+Vector((0,0,.14))*lift).lerp(surface+Vector((.073,0,.42)),transfer)+Vector((0,0,-.30*dip+.27*raise_up))
            tilt=work.to_3x3()@Matrix.Rotation(math.radians(-layout['work_yaw']),3,'Z')
            tq=frame((0,0,-1),layout['tong_axis'],(0,0,0))
            tong=(tilt@tq.to_3x3()).to_4x4()
            tong.translation=work@Vector((-.24,0,.00475))-tong.to_3x3()@Vector((0,0,.254))
            tool.translation+=Vector((-.12,-.06,-.12))*lift
            look=ease((age-.35)/1.25)
            camera=Vector((.29,-.43,1.48)).lerp(surface+Vector((-.08,-.42,.70)),look)
            target=Vector((.29,.22,.92)).lerp(surface+Vector((.04,.05,.12)),look)
            forward=(target-camera).normalized();half_fov=math.radians((67-4*look)*.5)
            view.location=Vector((camera.x,-camera.y,camera.z))
            view.rotation_euler=Vector((forward.x,-forward.y,forward.z)).to_track_quat('-Z','Y').to_euler()
            view.data.angle=half_fov*2
            view.keyframe_insert(data_path='location',frame=index);view.keyframe_insert(data_path='rotation_euler',frame=index)
            view.data.keyframe_insert(data_path='lens',frame=index)
        pose = {n: body @ reference[n] for n in order}
        solve(pose, 'r', tool @ grasp['r'])
        solve(pose, 'l', tong @ grasp['l'])
        for name in order:
            bone = rig.pose.bones[name]
            bone.rotation_mode = 'QUATERNION'
            desired = mirror @ pose[name] @ mirror
            parent_pose = mirror @ pose[parents[name]] @ mirror if parents[name] else Matrix.Identity(4)
            bone.matrix_basis = (mirror @ local[name] @ mirror).inverted() @ parent_pose.inverted() @ desired
            for channel in ('location', 'rotation_quaternion', 'scale'):
                bone.keyframe_insert(data_path=channel, frame=index)
        animated=[(hammer,tool),(tongs,tong)]
        if blank and work is not None:animated.append((blank,work))
        for obj, transform in animated:
            obj.rotation_mode = 'QUATERNION'
            obj.matrix_world = mirror @ transform @ mirror
            for channel in ('location', 'rotation_quaternion'):
                obj.keyframe_insert(data_path=channel, frame=index)
    if rig.animation_data and rig.animation_data.action:
        rig.animation_data.action.name = 'Forge_Quench_Camera_Contact_Steam_580' if quench else 'Forge_RightElbow_FastDownstroke_Contact_Rebound_%03d' % round(data['stroke_seconds']*scene.render.fps)
    scene.timeline_markers.clear()
    strike_markers=data.get('stroke_markers_seconds',{'Windup':.16,'CONTACT score + sound + sparks':data['contact_seconds'],
                                                    'Rebound':data['contact_seconds']+.11,'Ready':data['stroke_seconds']})
    markers=(('Lift',55),('Above tub',150),('Immersed steam',215),('Withdraw',395),('Cooled',465),('Return',580)) if quench else tuple(
        (label,round(seconds*scene.render.fps)) for label,seconds in strike_markers.items())
    for label, index in markers:
        scene.timeline_markers.new(label, frame=index)
    scene.frame_set(215 if quench else round(data['contact_seconds'] * scene.render.fps))
