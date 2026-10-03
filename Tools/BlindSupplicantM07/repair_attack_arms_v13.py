"""Rebuild M07 attacks from a neutral body and direct anatomical arm rotations.

The V11 reference, original surfaces, UVs and skin groups are immutable input.
No old attack wrist goals, elbow poles or solved arm frames are re-used. This
script only authors two attacks, records the requested arm source diagnosis,
and exports animation FBX files; it never runs Unreal, rendering or gameplay.
"""
import copy
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OUT = ROOT/'RecoveryV13Arms'
SOURCE = ROOT/'RecoveryHandsV11/M07_Original_HandArm_Master_V11.blend'
FPS = 30
FWD = Vector((0, -1, 0))
UP = Vector((0, 0, 1))
RIGHT = Vector((1, 0, 0))
sys.path.insert(0, str(Path(__file__).parent))
import author_motion_v04 as motion


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def qangle(q):
    return math.degrees(2*math.acos(min(1., abs(q.normalized().w))))


def smooth(t):
    t = min(1., max(0., t))
    return t*t*(3.-2.*t)


def track(t, keys):
    # Zero slopes at authored extremes stop anatomical joint angles overshooting.
    if t <= keys[0][0]:
        return keys[0][1]
    for (ta, a), (tb, b) in zip(keys, keys[1:]):
        if t <= tb:
            return a+(b-a)*smooth((t-ta)/(tb-ta))
    return keys[-1][1]


def curves(action):
    if not action.is_action_layered:
        return list(action.fcurves)
    return [c for layer in action.layers for strip in layer.strips
            for bag in strip.channelbags for c in bag.fcurves]


def longitudinal_roll(delta, original_direction, direction):
    swing = original_direction.normalized().rotation_difference(direction.normalized())
    residual = swing.inverted() @ delta
    residual.normalize()
    if residual.w < 0:
        residual.negate()
    axis = original_direction.normalized()
    v = Vector((residual.x, residual.y, residual.z))
    return math.degrees(2*math.atan2(v.dot(axis), residual.w))


def diagnose_existing(rig, rest, entries):
    report = {}
    for role in ('MeleeLeft', 'MeleeRight'):
        entry = entries[role]
        motion.activate(rig, bpy.data.actions[entry['action']])
        samples = []
        previous = {}
        for frame in range(1, entry['frames']+1):
            bpy.context.scene.frame_set(frame)
            bpy.context.view_layer.update()
            torso = rig.pose.bones['spine_05'].matrix.to_quaternion() @ rest['spine_05'].to_quaternion().inverted()
            for side in ('l', 'r'):
                a, b, c = [rig.pose.bones[n+'_'+side].matrix.copy() for n in ('upperarm', 'lowerarm', 'hand')]
                upper_rest = rest['lowerarm_'+side].translation-rest['upperarm_'+side].translation
                upper_dir = b.translation-a.translation
                upper_delta = torso.inverted() @ a.to_quaternion() @ rest['upperarm_'+side].to_quaternion().inverted()
                upper_roll = longitudinal_roll(upper_delta, upper_rest, torso.inverted() @ upper_dir)
                plane = (b.translation-a.translation).cross(c.translation-b.translation).normalized()
                local_plane = torso.inverted() @ plane
                lower_delta = b.to_quaternion() @ rest['lowerarm_'+side].to_quaternion().inverted()
                wrist_delta = (lower_delta @ rest['hand_'+side].to_quaternion()).inverted() @ c.to_quaternion()
                step = math.degrees(previous[side].angle(local_plane)) if side in previous else 0.
                previous[side] = local_plane.copy()
                samples.append({'frame':frame, 'seconds':(frame-1)/FPS, 'side':side,
                                'upperarm_axial_roll_torso_deg':upper_roll,
                                'elbow_plane_step_deg':step,
                                'wrist_residual_deg':qangle(wrist_delta),
                                'elbow_bend_deg':math.degrees((b.translation-a.translation).angle(c.translation-b.translation)),
                                'shoulder_cm':list(a.translation), 'elbow_cm':list(b.translation), 'wrist_cm':list(c.translation)})
        report[role] = {'max_abs_upperarm_axial_roll_torso_deg':max(abs(x['upperarm_axial_roll_torso_deg']) for x in samples),
                        'max_elbow_plane_step_deg':max(x['elbow_plane_step_deg'] for x in samples),
                        'max_wrist_residual_deg':max(x['wrist_residual_deg'] for x in samples),
                        'samples':samples}
    return report


def neutral_body_cache(rig, frames, idle):
    motion.activate(rig, idle)
    result = []
    for frame in range(1, frames+1):
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        result.append({p.name:p.matrix_basis.copy() for p in rig.pose.bones})
    return result


def build_attack(rig, rest, ordered, idle_cache, role, contact, frames):
    attacking = 'l' if role == 'MeleeLeft' else 'r'
    sign_attack = 1 if attacking == 'l' else -1
    duration = (frames-1)/FPS
    anticipation = contact-.28
    follow = contact+.16
    settle = min(duration-.19, contact+.52)
    # A downward/front diagonal swipe. Neither arm crosses behind the torso or
    # enters the shoulder gill root. Upper arms remain at least 8deg abducted.
    # All motion comes from joint rotations: no wrist or elbow translation.
    profile = {
        'shoulder_flex_deg':[(0,7),(anticipation,45),(contact,62),(follow,25),(settle,8),(duration,7)],
        'shoulder_abduction_deg':[(0,9),(anticipation,23),(contact,12),(follow,10),(settle,9),(duration,9)],
        'elbow_flex_deg':[(0,19),(anticipation,73),(contact,32),(follow,24),(settle,19),(duration,19)],
        'shoulder_roll_deg':[(0,0),(anticipation,9),(contact,5),(follow,0),(settle,0),(duration,0)],
        'wrist_flex_deg':[(0,2),(anticipation,6),(contact,9),(follow,4),(settle,2),(duration,2)],
        'finger_curl':[(0,.45),(anticipation,.9),(contact,.74),(follow,.8),(settle,.45),(duration,.45)],
        'body_yaw_deg':[(0,0),(anticipation,sign_attack*7),(contact,-sign_attack*9),(follow,-sign_attack*7),(settle,0),(duration,0)],
        'body_lean_deg':[(0,0),(anticipation,1),(contact,5),(follow,3),(settle,0),(duration,0)]}
    action = bpy.data.actions.new('A_M07_'+role+'_AnatomicalV13')
    action.use_fake_user = True
    motion.activate(rig, action)
    measurements = []
    previous_q = {}
    previous_plane = {}
    for i in range(frames):
        frame, t = i+1, i/FPS
        bpy.context.scene.frame_set(frame)
        local = {n:m.copy() for n,m in idle_cache[i].items()}
        # Clean rest poses for arms, shoulder girdle and hand chains. Idle's
        # solved arm frames are not part of this new choreography.
        for name in local:
            if name.startswith(('clavicle_', 'upperarm_', 'lowerarm_', 'hand_',
                                'thumb_', 'index_', 'middle_', 'ring_', 'pinky_')):
                local[name] = Matrix.Identity(4)
        target = {}
        yaw = track(t, profile['body_yaw_deg'])
        lean = track(t, profile['body_lean_deg'])
        for p in ordered:
            name, parent = p.name, p.parent.name if p.parent else None
            if parent:
                target[name] = p.bone.convert_local_to_pose(local[name], rest[name],
                    parent_matrix=target[parent], parent_matrix_local=rest[parent])
            else:
                target[name] = p.bone.convert_local_to_pose(local[name], rest[name])
            if name in ('spine_02', 'spine_03', 'spine_04', 'spine_05'):
                q = Quaternion(UP, math.radians(yaw*.25)) @ Quaternion(RIGHT, math.radians(lean*.25)) @ target[name].to_quaternion()
                target[name] = Matrix.LocRotScale(target[name].translation, q, Vector((1,1,1)))
            if name.startswith('upperarm_'):
                side = name[-1]
                sign = 1 if side == 'l' else -1
                if side == attacking:
                    flex = track(t, profile['shoulder_flex_deg'])
                    abd = track(t, profile['shoulder_abduction_deg'])
                    roll = track(t, profile['shoulder_roll_deg'])
                else:
                    flex = 7+6*math.sin(math.pi*min(t/duration,1))**2
                    abd, roll = 12., 0.
                flex, abd = math.radians(flex), math.radians(abd)
                torso = target['spine_05'].to_quaternion() @ rest['spine_05'].to_quaternion().inverted()
                desired = Vector((sign*math.sin(abd), -math.sin(flex)*math.cos(abd), -math.cos(flex)*math.cos(abd)))
                original = rest['lowerarm_'+side].translation-rest[name].translation
                swing = original.normalized().rotation_difference(desired)
                delta = Quaternion(desired, math.radians(sign*roll)) @ swing
                q = torso @ delta @ rest[name].to_quaternion()
                target[name] = Matrix.LocRotScale(target[name].translation, q, Vector((1,1,1)))
            elif name.startswith('lowerarm_'):
                side = name[-1]
                flex = track(t, profile['elbow_flex_deg']) if side == attacking else 26.+5*math.sin(math.pi*min(t/duration,1))**2
                upper = 'upperarm_'+side
                upper_delta = target[upper].to_quaternion() @ rest[upper].to_quaternion().inverted()
                torso = target['spine_05'].to_quaternion() @ rest['spine_05'].to_quaternion().inverted()
                u = (upper_delta @ (rest[name].translation-rest[upper].translation)).normalized()
                # The anatomical flexion hinge is lateral in the thorax frame.
                # Projection avoids axial forearm rotation when the upper arm
                # is abducted; no nearly straight cross-product pole is used.
                hinge = torso @ Vector((-1,0,0))
                hinge = (hinge-u*hinge.dot(u)).normalized()
                delta = Quaternion(hinge, math.radians(flex)) @ upper_delta
                target[name] = Matrix.LocRotScale(target[name].translation,
                    delta @ rest[name].to_quaternion(), Vector((1,1,1)))
            elif name.startswith('hand_'):
                side = name[-1]
                lower = 'lowerarm_'+side
                lower_delta = target[lower].to_quaternion() @ rest[lower].to_quaternion().inverted()
                wrist = track(t, profile['wrist_flex_deg']) if side == attacking else 2.
                local_axis = Vector((1,0,0))
                delta = Quaternion(target[lower].to_quaternion() @ local_axis,
                                   math.radians(wrist)) @ lower_delta
                target[name] = Matrix.LocRotScale(target[name].translation,
                    delta @ rest[name].to_quaternion(), Vector((1,1,1)))
            elif name.startswith(('thumb_', 'index_', 'middle_', 'ring_', 'pinky_')) and '_metacarpal_' not in name:
                side = name[-1]
                amount = track(t, profile['finger_curl']) if side == attacking else .42
                hand = target['hand_'+side]
                hand_delta = hand.to_quaternion() @ rest['hand_'+side].to_quaternion().inverted()
                along = (rest['middle_01_'+side].translation-rest['hand_'+side].translation).normalized()
                across = (rest['index_01_'+side].translation-rest['pinky_01_'+side].translation).normalized()
                palm = hand_delta @ along.cross(across).normalized()
                direction = target[name].to_3x3() @ Vector((0,1,0))
                axis = direction.cross(palm)
                if axis.length > .0001:
                    axis.normalize()
                    segment = int(name.split('_')[1])
                    degrees = (7,12,9)[segment-1]*amount
                    q = Quaternion(axis, math.radians(degrees)) @ target[name].to_quaternion()
                    target[name] = Matrix.LocRotScale(target[name].translation, q, Vector((1,1,1)))
            if parent:
                p.matrix_basis = p.bone.convert_local_to_pose(target[name], rest[name],
                    parent_matrix=target[parent], parent_matrix_local=rest[parent], invert=True)
            else:
                p.matrix_basis = p.bone.convert_local_to_pose(target[name], rest[name], invert=True)
            p.rotation_mode = 'QUATERNION'
            q = p.rotation_quaternion.copy()
            if name in previous_q and q.dot(previous_q[name]) < 0:
                q.negate()
            p.rotation_quaternion = q
            previous_q[name] = q.copy()
            p.scale = Vector((1,1,1))
            if name != 'pelvis':
                p.location = Vector()
            for channel in ('location','rotation_quaternion','scale'):
                p.keyframe_insert(data_path=channel, frame=frame)
        bpy.context.view_layer.update()
        for side in ('l', 'r'):
            a,b,c=[rig.pose.bones[n+'_'+side].matrix.copy() for n in ('upperarm','lowerarm','hand')]
            torso = rig.pose.bones['spine_05'].matrix.to_quaternion() @ rest['spine_05'].to_quaternion().inverted()
            original = rest['lowerarm_'+side].translation-rest['upperarm_'+side].translation
            upper_delta = torso.inverted() @ a.to_quaternion() @ rest['upperarm_'+side].to_quaternion().inverted()
            roll = longitudinal_roll(upper_delta, original, torso.inverted() @ (b.translation-a.translation))
            plane = torso.inverted() @ (b.translation-a.translation).cross(c.translation-b.translation).normalized()
            step = math.degrees(previous_plane[side].angle(plane)) if side in previous_plane else 0.
            previous_plane[side] = plane.copy()
            lower_delta = b.to_quaternion() @ rest['lowerarm_'+side].to_quaternion().inverted()
            wrist = (lower_delta @ rest['hand_'+side].to_quaternion()).inverted() @ c.to_quaternion()
            measurements.append({'frame':frame, 'seconds':t, 'side':side,
                'upperarm_axial_roll_torso_deg':roll, 'elbow_plane_step_deg':step,
                'elbow_bend_deg':math.degrees((b.translation-a.translation).angle(c.translation-b.translation)),
                'wrist_residual_deg':qangle(wrist),
                'shoulder_cm':list(a.translation),'elbow_cm':list(b.translation),'wrist_cm':list(c.translation),
                'upper_length_cm':(b.translation-a.translation).length,'lower_length_cm':(c.translation-b.translation).length})
        for sample in measurements[-2:]:
            sample['max_child_location_cm'] = max(p.location.length for p in rig.pose.bones if p.name != 'pelvis')
            sample['max_scale_error'] = max((p.scale-Vector((1,1,1))).length for p in rig.pose.bones)
    for curve in curves(action):
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'
    return action, profile, measurements


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    rest = {b.name:b.matrix_local.copy() for b in rig.data.bones}
    ordered = sorted(rig.pose.bones, key=lambda p:len(p.bone.parent_recursive))
    original_manifest = json.loads((ROOT/'RecoveryHandsV11/rig_motion/motion_manifest_v11.json').read_text(encoding='utf-8'))
    original_report = diagnose_existing(rig, rest, original_manifest['clips'])
    write(OUT/'requested_old_attack_arm_diagnosis_v13.json', {
        'scope':'The two source attacks actually used alongside V12 locomotion',
        'source':str(SOURCE), 'clips':original_report,
        'runtime_tested':False,'rendered':False})
    print('M07_V13_OLD_ATTACK_ARM_DIAGNOSIS '+json.dumps({n:{k:v for k,v in value.items() if k!='samples'} for n,value in original_report.items()}), flush=True)
    idle = bpy.data.actions[original_manifest['clips']['Idle']['action']]
    idle_cache = neutral_body_cache(rig, 51, idle)
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = .01
    rig.data.pose_position = 'POSE'
    entries, actions, results = {}, {}, {}
    for role in ('MeleeLeft', 'MeleeRight'):
        entry = copy.deepcopy(original_manifest['clips'][role])
        action, profile, measurements = build_attack(rig, rest, ordered, idle_cache,
            role, entry['impact_seconds'], entry['frames'])
        destination = OUT/f'A_M07_{role}.fbx'
        entry.update({'file':str(destination), 'asset':'/Game/Monsters/BlindSupplicantM07/AnimationsRecoveryV13/A_M07_'+role,
                      'action':action.name,'source':'Fresh direct shoulder/hinge/wrist choreography; neutral Epic-derived V11 idle body only',
                      'source_intent':'Original M07 anatomical diagonal swipe, no old attack goal/pole/roll or mocap acceptance claim',
                      'contact_window_seconds':.16})
        entries[role], actions[role] = entry, action
        results[role] = {'profile':profile,
            'max_abs_upperarm_axial_roll_torso_deg':max(abs(x['upperarm_axial_roll_torso_deg']) for x in measurements),
            'max_elbow_plane_step_deg':max(x['elbow_plane_step_deg'] for x in measurements),
            'max_wrist_residual_deg':max(x['wrist_residual_deg'] for x in measurements),
            'max_child_location_cm':max(x['max_child_location_cm'] for x in measurements),
            'max_scale_error':max(x['max_scale_error'] for x in measurements),
            'limb_lengths_cm':{side:{key:max(x[key] for x in measurements if x['side']==side)
                for key in ('upper_length_cm','lower_length_cm')} for side in ('l','r')},
            'samples':measurements}
        motion.activate(rig, action)
        scene.frame_start, scene.frame_end = 1, entry['frames']
        scene.frame_set(0)
        bpy.ops.object.select_all(action='DESELECT')
        rig.hide_set(False)
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        bpy.ops.export_scene.fbx(filepath=str(destination), use_selection=True,
            object_types={'ARMATURE'}, add_leaf_bones=False, use_armature_deform_only=False,
            armature_nodetype='NULL', bake_anim=True, bake_anim_use_all_bones=True,
            bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
            bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0,
            axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS')
        print('M07_V13_ATTACK_EXPORTED '+role,flush=True)
    motion.activate(rig, actions['MeleeLeft'])
    scene.frame_start, scene.frame_end = 1, entries['MeleeLeft']['frames']
    scene.frame_set(0)
    blend = OUT/'M07_Original_AttackArms_V13.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)
    write(OUT/'attack_arm_manifest_v13.json', {
        'revision':'RecoveryV13Attacks','source':str(blend),'source_master':str(SOURCE),
        'clips':entries,'fps':FPS,'ue_skeleton':original_manifest['ue_skeleton'],
        'reference_bones':{n:motion.rows(m) for n,m in rest.items()},
        'bone_names':[b.name for b in rig.data.bones],'bone_parents':{b.name:b.parent.name if b.parent else None for b in rig.data.bones},
        'mesh_geometry_uv_and_skin_preserved':True, 'bone_reference_and_lengths_preserved':True,
        'child_location_policy':'Zero on every bone except source pelvis; scale 1',
        'fresh_attack_choreography':True,'old_attack_arm_goals_reused':False,
        'reference_units':'centimeter coordinates, scene .01, identity Armature object; reference frame0 excluded',
        'method':'Shoulder minimum swing plus <=9deg axial expression; lateral projected elbow hinge without forearm axial roll; <=9deg wrist flex; neutral clavicle and modest claw curls',
        'body_baseline':'Only neutral V11 idle non-arm body tracks; split yaw/lean through spine, no failed attack body/arm solve',
        'production_measurements':results,'old_source_diagnosis':str(OUT/'requested_old_attack_arm_diagnosis_v13.json'),
        'runtime_tested':False,'rendered':False,'ue_imported':False})
    print('M07_V13_ANATOMICAL_ATTACKS_SAVED',flush=True)


if __name__ == '__main__':
    main()
