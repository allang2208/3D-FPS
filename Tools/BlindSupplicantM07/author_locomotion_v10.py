"""Author two larger-stride human locomotion clips on the retained M07 rig.

Epic's local Quinn unarmed Walk supplies foot contact, shoulder/pelvis
opposition and elbow bend timing. Only locomotion is authored; V09 geometry,
skin, cloth, materials and the other actions are kept in the combined source.
This is production baking/export, without playback, renders or tests.
"""
import importlib.util
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OUT = ROOT/'LocomotionV10'
RIG_OUT = OUT/'rig_motion'
TOOLS = Path(__file__).parent
REFERENCE = ROOT/'RecoveryOriginalV08/rig_motion/M07_OriginalReference_Meter_V08.blend'
DISPLAY_MASTER = ROOT/'RecoveryOriginalV09/M07_Original_Skinned_Master_V09.blend'
WALK = ROOT.parent/'WitchFoundation20260920/Sources/Walk.fbx'
FPS = 30
ROLES = {
    'SlowWalk': {'intervals': 60, 'speed_cm_s': 90., 'arm_half_swing_deg': 22.,
                 'elbow_range_deg': (22., 48.)},
    'Chase': {'intervals': 44, 'speed_cm_s': 145., 'arm_half_swing_deg': 30.,
              'elbow_range_deg': (28., 60.)},
}


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def load_math():
    spec = importlib.util.spec_from_file_location('m07_stride_math_v10', TOOLS/'author_motion_v04.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.SOURCES = {'Walk': WALK}
    sys.path.insert(0, str(TOOLS))
    import author_biped_legs_v08 as legs
    legs.OUT = OUT/'leg_support'
    legs.install_motion_hooks(module)
    return module, legs


def curves(action):
    if not action.is_action_layered:
        return list(action.fcurves)
    return [c for layer in action.layers for strip in layer.strips
            for bag in strip.channelbags for c in bag.fcurves]


def source_arm(source, raw, side):
    """Express wrist direction and elbow plane in the source torso frame."""
    torso = raw['spine_03'].to_quaternion() @ source['rest']['spine_03'].to_quaternion().inverted()
    upper = raw['lowerarm_'+side].translation-raw['upperarm_'+side].translation
    lower = raw['hand_'+side].translation-raw['lowerarm_'+side].translation
    wrist = upper+lower
    direction = wrist.normalized()
    bend = upper-direction*upper.dot(direction)
    if bend.length < 1.e-7:
        bend = torso @ Vector((0., -1., 0.))
    bend = torso.inverted() @ bend.normalized()
    wrist_local = torso.inverted() @ wrist
    angle = math.atan2(-wrist_local.y, -wrist_local.z)
    elbow = math.acos(max(-1., min(1., upper.normalized().dot(lower.normalized()))))
    return angle, elbow, bend


def relaxed_hand(rig, side, u, wave, hand_angles):
    phase = .18 if side == 'l' else math.pi+.18
    for finger in ('thumb', 'index', 'middle', 'ring', 'pinky'):
        meta = rig.pose.bones[finger+'_metacarpal_'+side]
        meta.rotation_mode = 'QUATERNION'
        meta.rotation_quaternion = Quaternion()
        for segment in (1, 2, 3):
            # Preserve the source-fit flexion axes and separate CMC/MCP/IP.
            angle = hand_angles[finger][segment-1]*.85
            angle += 1.8*wave + .6*math.sin(2.*math.pi*u+phase+segment*.25)
            pose = rig.pose.bones[f'{finger}_{segment:02d}_{side}']
            pose.rotation_mode = 'QUATERNION'
            pose.rotation_quaternion = Quaternion((1., 0., 0.), math.radians(angle))
            if finger == 'thumb' and segment == 1:
                pose.rotation_quaternion @= Quaternion((0., 1., 0.), math.radians(3.))


def author():
    OUT.mkdir(parents=True, exist_ok=True)
    RIG_OUT.mkdir(parents=True, exist_ok=True)
    motion, legs = load_math()
    source = motion.read_sources()['Walk']
    arm_profiles = {}
    for side in ('l', 'r'):
        sampled = [source_arm(source, f, side) for f in source['samples'][:-1]]
        angles = [x[0] for x in sampled]
        center = (max(angles)+min(angles))*.5
        arm_profiles[side] = {'center': center, 'amplitude': max(.01, (max(angles)-min(angles))*.5),
                              'elbow_min': min(x[1] for x in sampled),
                              'elbow_max': max(x[1] for x in sampled)}

    bpy.ops.wm.open_mainfile(filepath=str(REFERENCE))
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    rig.animation_data_clear()
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    rig.data.pose_position = 'POSE'
    rig.hide_set(False)
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = FPS, 1
    maker = motion.Author(rig, {'Walk': source})
    rest = maker.rest
    hand_angles = json.loads((ROOT/'RecoveryOriginalV07/hands/hand_action_guides_v07.json').read_text(encoding='utf-8'))['recommended_curl_degrees']['Locomotion']
    manifest = {
        'revision': 'LocomotionV10', 'fps': FPS, 'clips': {},
        'source': str(OUT/'M07_Original_Locomotion_V10.blend'),
        'source_walk': str(WALK),
        'source_walk_asset': '/Game/Characters/Mannequins/Anims/Unarmed/Walk/MF_Unarmed_Walk_Fwd',
        'source_license': 'Installed Epic UE mannequin template; local UE project adaptation, no standalone source redistribution',
        'source_provenance': str(ROOT.parent/'WitchFoundation20260920/source_motion.json'),
        'reference_skeleton': '/Game/Monsters/BlindSupplicantM07/SK_M07_ReferenceOriginalV08',
        'display_mesh_retained': '/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV09',
        'reference_pose_modified': False, 'geometry_modified': False,
        'weights_modified': False, 'cloth_modified': False,
        'tested': False, 'rendered': False, 'runtime_tested': False,
        'method': 'One complete mature human foot/torso cycle retimed for longer steps; source-correlated opposite arm swing, dynamic elbow flexion, transported neutral wrists and relaxed fingers; native anatomical biped IK and unchanged target bone lengths',
    }
    actions = {}
    for role, config in ROLES.items():
        count = config['intervals']+1
        duration = config['intervals']/FPS
        stride_m = config['speed_cm_s']*.01*duration
        action = bpy.data.actions.new('A_M07_'+role+'_LocomotionV10')
        action.use_fake_user = True
        motion.activate(rig, action)
        actions[role] = action
        scene.frame_start, scene.frame_end = 1, count
        previous = {}
        contact = {s: [] for s in ('l', 'r')}
        for i in range(count):
            scene.frame_set(i+1)
            u = i/config['intervals']
            maker.reset()
            raw = motion.sample(source, u)
            common = maker.walk_travel*u
            mean = maker.walk_mean_pelvis-maker.walk_travel*.5
            sway = raw['pelvis'].translation-common-mean
            pelvis = rest['pelvis'].translation+sway*maker.leg_ratio+Vector((0., 0., -.05))
            maker.retarget(source, raw, pelvis)
            for name, degrees in (('spine_02', 1.5), ('spine_04', 2.), ('neck_01', 3.), ('head', 4.)):
                motion.rotate(rig, name, Vector((1., 0., 0.)), degrees)
            foot_goals = {}
            settling = 0.
            for side in ('l', 'r'):
                donor_ball = raw['ball_'+side].translation-common
                profile = maker.walk_ball[side]
                ball = rest['ball_'+side].translation.copy()
                ball.x += (donor_ball.x-profile['mean'].x)*maker.leg_ratio
                ball.y += (donor_ball.y-profile['mean'].y)*stride_m/max(.01, maker.walk_navigation_distance)
                ball.z += max(0., donor_ball.z-profile['low'])*maker.leg_ratio*(.90 if role == 'SlowWalk' else 1.06)
                delta = raw['foot_'+side].to_quaternion() @ source['rest']['foot_'+side].to_quaternion().inverted()
                foot_q = delta @ rest['foot_'+side].to_quaternion()
                ankle_to_ball = rest['foot_'+side].to_quaternion().inverted() @ (rest['ball_'+side].translation-rest['foot_'+side].translation)
                bounded_foot = legs._bounded_world_foot(foot_q, rest['foot_'+side].to_quaternion())
                goal = ball-bounded_foot@ankle_to_ball
                hip = motion.world(rig, 'thigh_'+side).translation
                horizontal_sq = (goal.x-hip.x)**2+(goal.y-hip.y)**2
                length = (maker.leg_data[side]['l1']+maker.leg_data[side]['l2'])*.995
                available_height = math.sqrt(max(0., length*length-horizontal_sq))
                settling = max(settling, hip.z-goal.z-available_height)
                foot_goals[side] = (ball, foot_q, ankle_to_ball)
                contact[side].append(1.-motion.smooth((donor_ball.z-profile['low']-.015)/.055))
            # A longer stance may require a few centimetres of hip settling.
            # Keep the support target on the floor instead of clipping the
            # ankle toward an unreachable hip at the end of the stride.
            if settling > 0.:
                pelvis_frame = motion.world(rig, 'pelvis')
                pelvis_frame.translation.z -= settling
                motion.put(rig, 'pelvis', pelvis_frame)
            for side in ('l', 'r'):
                ball, foot_q, ankle_to_ball = foot_goals[side]
                maker.leg(side, ball-foot_q@ankle_to_ball, foot_q, raw)
                local_rest = source['rest']['foot_'+side].to_quaternion().inverted() @ source['rest']['ball_'+side].to_quaternion()
                local_pose = raw['foot_'+side].to_quaternion().inverted() @ raw['ball_'+side].to_quaternion()
                rig.pose.bones['ball_'+side].rotation_quaternion = local_pose @ local_rest.inverted()

            out_axis, forward, up = maker.torso_axes()
            for side, sign in (('l', 1), ('r', -1)):
                source_angle, source_elbow, source_bend = source_arm(source, raw, side)
                profile = arm_profiles[side]
                wave = max(-1., min(1., (source_angle-profile['center'])/profile['amplitude']))
                theta = math.radians(2.+config['arm_half_swing_deg']*wave)
                lo, hi = [math.radians(v) for v in config['elbow_range_deg']]
                elbow_phase = motion.smooth((source_elbow-profile['elbow_min']) /
                                           max(.01, profile['elbow_max']-profile['elbow_min']))
                elbow = lo+(hi-lo)*elbow_phase
                l1, l2 = maker.arm[side]['l1'], maker.arm[side]['l2']
                reach = math.sqrt(l1*l1+l2*l2+2.*l1*l2*math.cos(elbow))
                shoulder = motion.world(rig, 'upperarm_'+side).translation.copy()
                direction = (forward*math.sin(theta)-up*math.cos(theta)+out_axis*(sign*.055)).normalized()
                bend = (out_axis*source_bend.x+forward*(-source_bend.y)+up*source_bend.z).normalized()
                goal = shoulder+direction*reach
                pole = shoulder+bend*(l1+l2)*.55
                maker.solve_chain(side, ('upperarm', 'lowerarm', 'hand'), maker.arm, goal, pole, .995)
                neutral = motion.world(rig, 'lowerarm_'+side).to_quaternion() @ rest['lowerarm_'+side].to_quaternion().inverted() @ rest['hand_'+side].to_quaternion()
                # Wrists follow their forearms; small flexible lag avoids the
                # old independently imposed palm orientation and large roll.
                lag_raw = motion.sample(source, (u-.035) % 1.)
                lag_angle = source_arm(source, lag_raw, side)[0]
                lag_wave = max(-1., min(1., (lag_angle-profile['center'])/profile['amplitude']))
                wrist = neutral @ Quaternion((1., 0., 0.), math.radians(3.*lag_wave))
                wrist @= Quaternion((0., 1., 0.), math.radians(sign*2.*wave))
                motion.orient(rig, 'hand_'+side, wrist)
                relaxed_hand(rig, side, u, lag_wave, hand_angles)
            maker.gills(u)
            for pose in maker.ordered:
                pose.rotation_mode = 'QUATERNION'
                if pose.name != 'pelvis':
                    pose.location = Vector()
                pose.scale = Vector((1., 1., 1.))
                q = pose.rotation_quaternion.copy()
                if pose.name in previous and q.dot(previous[pose.name]) < 0:
                    q.negate()
                    pose.rotation_quaternion = q
                previous[pose.name] = q
                for prop in ('location', 'rotation_quaternion', 'scale'):
                    pose.keyframe_insert(data_path=prop, frame=i+1, group=pose.name)
        # The same donor cycle defines both sides and both roles. Closing the
        # cycle and keeping the real bind pose outside it are export authoring.
        scene.frame_set(1)
        opening = {p.name: p.matrix_basis.copy() for p in maker.ordered}
        scene.frame_set(count)
        for pose in maker.ordered:
            pose.matrix_basis = opening[pose.name]
            for prop in ('location', 'rotation_quaternion', 'scale'):
                pose.keyframe_insert(data_path=prop, frame=count, group=pose.name)
        scene.frame_set(0)
        maker.reset()
        for pose in maker.ordered:
            for prop in ('location', 'rotation_quaternion', 'scale'):
                pose.keyframe_insert(data_path=prop, frame=0, group=pose.name)
        legs.apply_motion(rig, action, 'A_M07_'+role, fps=FPS, unit_scale=1.)
        manifest['clips'][role] = {
            'action': action.name, 'file': str(RIG_OUT/('A_M07_'+role+'.fbx')),
            'frames': count, 'fps': FPS, 'duration_seconds': duration,
            'speed_cm_s': config['speed_cm_s'], 'stride_cm': stride_m*100.,
            'step_cm': stride_m*50., 'loop': True, 'root_motion': False,
            'arm_sagittal_swing_deg': [2.-config['arm_half_swing_deg'], 2.+config['arm_half_swing_deg']],
            'elbow_bend_range_deg': list(config['elbow_range_deg']),
            'foot_contact': contact,
            'export_frame_start': 1, 'export_frame_end': count,
            'reference_only_frame': 0,
        }
        print('M07_V10_AUTHORED '+role+' '+str(duration)+'s', flush=True)

    rig.data.transform(Matrix.Scale(100., 4))
    rig.matrix_world = Matrix.Identity(4)
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = .01
    for action in actions.values():
        for curve in curves(action):
            if curve.data_path.endswith('.location'):
                for point in curve.keyframe_points:
                    point.co.y *= 100.
                    point.handle_left.y *= 100.
                    point.handle_right.y *= 100.
            for point in curve.keyframe_points:
                point.interpolation = 'LINEAR'
    for role, entry in manifest['clips'].items():
        motion.activate(rig, actions[role])
        scene.frame_start, scene.frame_end = 1, entry['frames']
        scene.frame_set(0)
        bpy.ops.export_scene.fbx(filepath=entry['file'], use_selection=True,
            object_types={'ARMATURE'}, add_leaf_bones=False, use_armature_deform_only=False,
            armature_nodetype='NULL', bake_anim=True, bake_anim_use_all_bones=True,
            bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
            bake_anim_force_startend_keying=True, bake_anim_step=1,
            bake_anim_simplify_factor=0, axis_forward='-Y', axis_up='Z',
            apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS')
        print('M07_V10_EXPORTED '+role, flush=True)
    rig_source = RIG_OUT/'M07_Locomotion_Rig_V10.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(rig_source))

    bpy.ops.wm.open_mainfile(filepath=str(DISPLAY_MASTER))
    display_rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.data.bones.get('gill_01_00'))
    with bpy.data.libraries.load(str(rig_source), link=False) as (available, loaded):
        loaded.actions = [name for name in available.actions if name.endswith('_LocomotionV10')]
    for action in loaded.actions:
        action.use_fake_user = True
    action_by_name = {a.name: a for a in loaded.actions}
    motion.activate(display_rig, action_by_name[manifest['clips']['SlowWalk']['action']])
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, manifest['clips']['SlowWalk']['frames']
    scene.render.fps, scene.render.fps_base = FPS, 1
    scene.frame_set(0)
    display_rig['locomotion_revision'] = 'LocomotionV10: larger biped stride and mature opposite human arm swing'
    combined = OUT/'M07_Original_Locomotion_V10.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(combined))
    manifest.update({'rig_source': str(rig_source), 'combined_source_saved': True,
                     'animation_fbx_exported': True, 'retained_display_source': str(DISPLAY_MASTER)})
    write_json(OUT/'locomotion_manifest_v10.json', manifest)
    print('M07_V10_LOCOMOTION_SOURCE_SAVED '+str(combined), flush=True)


if __name__ == '__main__':
    author()
