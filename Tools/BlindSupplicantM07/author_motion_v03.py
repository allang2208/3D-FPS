"""Author M07 V03 on the immutable 81-bone M07 reference skeleton.

Full Epic Quinn gait is adapted before the M07 hanging-arm choreography.
The Witch Arm06 anatomical frame method replaces successive shortest-arc
rotations. This is production baking/export only; no render, cloth or test.
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OUT = ROOT / 'MotionV03'
MASTER = ROOT / 'Authoring/FragmentRepairV02/M07_Separated_Master_V02.blend'
FOUNDATION = ROOT.parent / 'WitchFoundation20260920'
FPS = 30
SOURCES = {
    'Walk': FOUNDATION / 'Sources/Walk.fbx',
    'Idle': FOUNDATION / 'Sources/Idle.fbx',
    'Dizzy': ROOT.parent / 'HumanoidStun20260926/fitted/A_Nurse_Dizzy.fbx',
    'Fall': ROOT.parent / 'HumanoidKnockdown20260926/fitted/A_Nurse_Hit_Knockback.fbx',
    'GetUp': ROOT.parent / 'HumanoidKnockdown20260926/fitted/A_Nurse_LayToIdle.fbx',
    'ProneGetUp': ROOT.parent / 'HumanoidKnockdown20260926/fitted/A_Nurse_ProneToIdle.fbx',
}
ROLES = (
    ('Idle', 4.0, True, None),
    ('SlowWalk', 50 / FPS, True, None),
    ('Chase', 36 / FPS, True, None),
    ('MeleeLeft', 1.5, False, .68),
    ('MeleeRight', 1.65, False, .78),
    ('Hit', .9, False, None),
    ('Death', 2.4, False, None),
    ('WallListen', 3.2, False, None),
    ('Dizzy', 2.4, True, None),
    ('Fall', 25 / FPS, False, None),
    ('GetUp', 1.5, False, None),
    ('ProneGetUp', 2.3, False, None),
)
IDENTITY = Quaternion()
UP = Vector((0, 0, 1))
FORWARD = Vector((0, -1, 0))


def rows(m):
    return [[float(v) for v in row] for row in m]


def smooth(v):
    v = max(0., min(1., v))
    return v * v * (3 - 2 * v)


def ramp(t, a, b):
    return smooth((t - a) / (b - a))


def update():
    bpy.context.view_layer.update()


def activate(rig, action):
    rig.animation_data_create()
    rig.animation_data.action = action
    if action and action.slots:
        rig.animation_data.action_slot = action.slots[0]
    for track in rig.animation_data.nla_tracks:
        track.mute = True


def world(rig, name):
    return rig.matrix_world @ rig.pose.bones[name].matrix


def put(rig, name, matrix):
    rig.pose.bones[name].matrix = rig.matrix_world.inverted() @ matrix
    update()


def orient(rig, name, quaternion):
    m = world(rig, name)
    put(rig, name, Matrix.LocRotScale(m.translation, quaternion, m.to_scale()))


def rotate(rig, name, axis, degrees):
    orient(rig, name, Quaternion(axis, math.radians(degrees)) @ world(rig, name).to_quaternion())


def sample(src, u):
    pos = max(0., min(1., u)) * (len(src['samples']) - 1)
    first = int(pos)
    last = min(len(src['samples']) - 1, first + 1)
    alpha = pos - first
    return {n: Matrix.LocRotScale(
        src['samples'][first][n].translation.lerp(src['samples'][last][n].translation, alpha),
        src['samples'][first][n].to_quaternion().slerp(src['samples'][last][n].to_quaternion(), alpha),
        Vector((1, 1, 1))) for n in src['rest']}


def read_sources():
    result = {}
    foundation_contract = json.loads((FOUNDATION/'source_motion.json').read_text(encoding='utf-8'))
    for role, path in SOURCES.items():
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(path), use_anim=True)
        rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
        action = rig.animation_data.action
        activate(rig, action)
        rate = bpy.context.scene.render.fps / bpy.context.scene.render.fps_base
        start, end = action.frame_range
        count = round((end - start) / rate * FPS) + 1
        if role in ('Walk', 'Idle'):
            # Match the exact source span used by Witch Foundation. The FBX
            # importer adds one padding sample outside that exported span.
            start = 1
            count = int(foundation_contract[role]['frames']) + 1
        frames = []
        for i in range(count):
            frame = start + i / FPS * rate
            bpy.context.scene.frame_set(math.floor(frame), subframe=frame % 1)
            frames.append({p.name: rig.matrix_world @ p.matrix for p in rig.pose.bones})
        rest = {b.name: rig.matrix_world @ b.matrix_local for b in rig.data.bones}
        result[role] = {'samples': frames, 'rest': rest, 'source': str(path),
                        'action': action.name, 'source_fps': rate,
                        'source_duration': (count - 1) / FPS,
                        'object_matrix_world': rows(rig.matrix_world)}
        print('M07_V03_DONOR ' + role + ' ' + str(count) + ' frames', flush=True)
    return result


def anatomical_frame(direction, plane):
    along = direction.normalized()
    normal = plane - along * plane.dot(along)
    if normal.length < .00001:
        fallback = FORWARD if abs(along.dot(FORWARD)) < .85 else UP
        normal = fallback - along * fallback.dot(along)
    normal.normalize()
    across = normal.cross(along).normalized()
    return Matrix((along, across, normal)).transposed()


def arc(t, keys):
    """Continuous Hermite wrist trajectory; impact point is an explicit key."""
    if t <= keys[0][0]:
        return Vector(keys[0][1])
    for j, ((ta, a), (tb, b)) in enumerate(zip(keys, keys[1:])):
        if ta <= t <= tb:
            v = (t - ta) / (tb - ta)
            a, b = Vector(a), Vector(b)
            ma = Vector() if j == 0 else (b - Vector(keys[j - 1][1])) / (tb - keys[j - 1][0])
            mb = Vector() if j + 2 == len(keys) else (Vector(keys[j + 2][1]) - a) / (keys[j + 2][0] - ta)
            return a * (2*v**3 - 3*v*v + 1) + ma*(tb-ta)*(v**3 - 2*v*v + v) + b*(-2*v**3 + 3*v*v) + mb*(tb-ta)*(v**3 - v*v)
    return Vector(keys[-1][1])


class Author:
    def __init__(self, rig, sources):
        self.rig = rig
        self.sources = sources
        self.ordered = sorted(rig.pose.bones, key=lambda p: len(p.bone.parent_recursive))
        self.rest = {b.name: rig.matrix_world @ b.matrix_local for b in rig.data.bones}
        self.local = {b.name: b.parent.matrix_local.inverted() @ b.matrix_local if b.parent else b.matrix_local.copy() for b in rig.data.bones}
        self.leg_ratio = self.chain_ratio('thigh', 'calf', 'foot', sources['Walk'])
        self.arm = {}
        self.leg_data = {}
        for side, sign in (('l', 1), ('r', -1)):
            for store, names in ((self.arm, ('upperarm', 'lowerarm', 'hand')), (self.leg_data, ('thigh', 'calf', 'foot'))):
                a, b, c = [self.rest[n + '_' + side].translation for n in names]
                u, l = (b-a).normalized(), (c-b).normalized()
                normal = u.cross(l)
                if normal.length < .02:
                    normal = Vector((0, -sign, 0))
                normal.normalize()
                store[side] = {'l1': (b-a).length, 'l2': (c-b).length,
                    'upper_reference': anatomical_frame(u, normal),
                    'lower_reference': anatomical_frame(l, normal)}
            wrist = self.rest['hand_' + side].translation
            along = (self.rest['middle_01_' + side].translation - wrist).normalized()
            across = (self.rest['index_01_' + side].translation - self.rest['pinky_01_' + side].translation).normalized()
            self.arm[side]['hand_reference'] = anatomical_frame(along, across)
        walk = sources['Walk']
        self.walk_mean_pelvis = sum((f['pelvis'].translation for f in walk['samples']), Vector()) / len(walk['samples'])
        self.walk_travel = walk['samples'][-1]['pelvis'].translation - walk['samples'][0]['pelvis'].translation
        self.walk_navigation_distance = math.hypot(self.walk_travel.x, self.walk_travel.y)
        # One common locomotion translation is removed from every joint. No
        # independent endpoint drift lines and no attenuation of torso tracks.
        values = {side: [] for side in ('l', 'r')}
        for i, frame in enumerate(walk['samples']):
            common = self.walk_travel * (i / (len(walk['samples']) - 1))
            for side in values:
                values[side].append(frame['ball_' + side].translation - common)
        self.walk_ball = {side: {
            'mean': sum(v, Vector()) / len(v),
            'low': min(p.z for p in v),
            'range_y': max(p.y for p in v) - min(p.y for p in v)} for side, v in values.items()}
        self.walk_range = sum(v['range_y'] for v in self.walk_ball.values()) / 2

    def chain_ratio(self, a, b, c, source):
        def total(rest):
            return sum((rest[b+'_'+s].translation-rest[a+'_'+s].translation).length +
                (rest[c+'_'+s].translation-rest[b+'_'+s].translation).length for s in ('l', 'r'))
        return total(self.rest) / total(source['rest'])

    def reset(self):
        for p in self.ordered:
            p.matrix_basis = Matrix.Identity(4)
        update()

    def retarget(self, source, raw, pelvis_position):
        """Complete global rotation deltas with target local bone lengths.

        Parent-driven translations keep the complete target anatomy coherent.
        Source object scale is already represented by its sampled world frame;
        it is not reapplied to target translations or silently replaced.
        """
        target = {}
        for p in self.ordered:
            n = p.name
            parent = p.parent.name if p.parent else None
            if parent:
                position = target[parent] @ self.local[n].translation
            else:
                position = self.rest[n].translation.copy()
            if n == 'pelvis':
                position = pelvis_position
            if n in raw and not n.startswith(('gill_', 'thumb_', 'index_', 'middle_', 'ring_', 'pinky_')):
                delta = raw[n].to_quaternion() @ source['rest'][n].to_quaternion().inverted()
                quaternion = delta @ self.rest[n].to_quaternion()
            elif parent:
                quaternion = (target[parent].to_quaternion() @ self.rest[parent].to_quaternion().inverted()) @ self.rest[n].to_quaternion()
            else:
                quaternion = self.rest[n].to_quaternion()
            m = Matrix.LocRotScale(position, quaternion, self.rest[n].to_scale())
            target[n] = m
            p.matrix = self.rig.matrix_world.inverted() @ m
        update()

    def solve_chain(self, side, names, store, endpoint, pole, reach=.988):
        a = world(self.rig, names[0]+'_'+side).translation.copy()
        data = store[side]
        l1, l2 = data['l1'], data['l2']
        vector = endpoint - a
        if vector.length < .00001:
            vector = Vector((0, 0, -1))
        direction = vector.normalized()
        distance = max(abs(l1-l2)+.015, min(vector.length, (l1+l2)*reach))
        end = a + direction * distance
        bend = pole - a
        bend -= direction * bend.dot(direction)
        if bend.length < .00001:
            bend = FORWARD - direction*FORWARD.dot(direction)
        bend.normalize()
        along = (l1*l1-l2*l2+distance*distance)/(2*distance)
        elbow = a+direction*along+bend*math.sqrt(max(0., l1*l1-along*along))
        upper_dir, lower_dir = (elbow-a).normalized(), (end-elbow).normalized()
        hinge = upper_dir.cross(lower_dir).normalized()
        upper_rotation = anatomical_frame(upper_dir, hinge) @ data['upper_reference'].transposed()
        lower_rotation = anatomical_frame(lower_dir, hinge) @ data['lower_reference'].transposed()
        orient(self.rig, names[0]+'_'+side, upper_rotation.to_quaternion() @ self.rest[names[0]+'_'+side].to_quaternion())
        orient(self.rig, names[1]+'_'+side, lower_rotation.to_quaternion() @ self.rest[names[1]+'_'+side].to_quaternion())
        return lower_dir

    def leg(self, side, endpoint, foot_q, raw=None):
        hip = world(self.rig, 'thigh_'+side).translation
        if raw:
            source_bend = raw['calf_'+side].translation - raw['thigh_'+side].translation
            source_bend.normalize()
            pole = hip + source_bend * .6 + FORWARD * .18
        else:
            sign = 1 if side == 'l' else -1
            pole = hip + FORWARD*.6 + Vector((sign*.04, 0, -.15))
        self.solve_chain(side, ('thigh', 'calf', 'foot'), self.leg_data, endpoint, pole)
        orient(self.rig, 'foot_'+side, foot_q)

    def torso_axes(self):
        q = world(self.rig, 'spine_03').to_quaternion() @ self.rest['spine_03'].to_quaternion().inverted()
        return q @ Vector((1, 0, 0)), q @ FORWARD, q @ UP

    def arm_pose(self, side, goal, pole, forward, up, wrist_bend=0.):
        sign = 1 if side == 'l' else -1
        lower = self.solve_chain(side, ('upperarm', 'lowerarm', 'hand'), self.arm, goal, pole, .975)
        wrist_direction = (lower*.94-up*.06+forward*wrist_bend).normalized()
        desired = anatomical_frame(wrist_direction, forward*sign) @ self.arm[side]['hand_reference'].transposed()
        wanted = desired.to_quaternion() @ self.rest['hand_'+side].to_quaternion()
        neutral = world(self.rig, 'lowerarm_'+side).to_quaternion() @ self.rest['lowerarm_'+side].to_quaternion().inverted() @ self.rest['hand_'+side].to_quaternion()
        delta = wanted @ neutral.inverted()
        vector = Vector((delta.x, delta.y, delta.z))
        projection = lower * vector.dot(lower)
        roll = Quaternion((delta.w, projection.x, projection.y, projection.z)).normalized()
        if roll.w < 0:
            roll.negate()
        axis, angle = roll.to_axis_angle()
        if angle > math.radians(70):
            roll = Quaternion(axis, math.radians(70))
        # This rig has no helper twist bones. Share roll with the entire forearm
        # and leave the remaining rotation at the articulated wrist.
        orient(self.rig, 'lowerarm_'+side, IDENTITY.slerp(roll, .42) @ world(self.rig, 'lowerarm_'+side).to_quaternion())
        orient(self.rig, 'hand_'+side, wanted)

    def fingers(self, side, amount, wave):
        for finger in ('thumb', 'index', 'middle', 'ring', 'pinky'):
            for segment in (1, 2, 3):
                name = f'{finger}_{segment:02d}_{side}'
                self.rig.pose.bones[name].matrix_basis = Matrix.Identity(4)
        update()
        hand = world(self.rig, 'hand_'+side)
        along = (world(self.rig, 'middle_01_'+side).translation-hand.translation).normalized()
        across = (world(self.rig, 'index_01_'+side).translation-world(self.rig, 'pinky_01_'+side).translation).normalized()
        palm = along.cross(across).normalized()
        for finger, factor in (('index', .82), ('middle', .95), ('ring', 1.05), ('pinky', 1.12), ('thumb', .62)):
            for segment in (1, 2, 3):
                name = f'{finger}_{segment:02d}_{side}'
                direction = (world(self.rig, name).to_3x3() @ Vector((0, 1, 0))).normalized()
                axis = direction.cross(palm)
                if axis.length < .00001:
                    continue
                axis.normalize()
                degrees = (9 if segment == 1 else 15 if segment == 2 else 11)*factor*amount + wave*.6
                rotate(self.rig, name, axis, degrees)
            if finger == 'thumb':
                rotate(self.rig, 'thumb_01_'+side, along, (1 if side == 'l' else -1)*7*amount)

    def gills(self, u, fade=1):
        for panel in range(1, 7):
            phase = -(panel-1)*.38
            wave = math.sin(2*math.pi*u+phase)-math.sin(phase)
            for segment in range(3):
                name = f'gill_{panel:02d}_{segment:02d}'
                self.rig.pose.bones[name].rotation_quaternion = Quaternion((1, 0, 0), math.radians((1+segment*.65)*wave*fade)) @ Quaternion((0, 1, 0), math.radians(.4*wave*fade))
        update()


def author():
    OUT.mkdir(parents=True, exist_ok=True)
    sources = read_sources()
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.data.bones.get('gill_01_00'))
    # The source is deliberately rig-only; the immutable complete anatomy and
    # membrane master remains available separately and its modifiers never run.
    for obj in list(bpy.data.objects):
        if obj != rig:
            bpy.data.objects.remove(obj, do_unlink=True)
    rig.animation_data_clear()
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    rig.data.pose_position = 'POSE'
    rig.hide_set(False)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = FPS, 1
    for p in rig.pose.bones:
        p.rotation_mode = 'QUATERNION'
        p.matrix_basis = Matrix.Identity(4)
    update()
    maker = Author(rig, sources)
    rest = maker.rest
    foot_anchors = {side: rest['foot_'+side].copy() for side in ('l', 'r')}
    manifest = {
        'schema': 3, 'character': 'BlindSupplicantM07', 'revision': 'MotionV03',
        'fps': FPS, 'source_saved': False, 'animation_fbx_exported': False,
        'master_reference': str(MASTER), 'source': str(OUT/'M07_Motion_V03.blend'),
        'reference_object_matrix_world': rows(rig.matrix_world),
        'reference_bones': {n: rows(m) for n, m in rest.items()},
        'reference_parents': {b.name: b.parent.name if b.parent else None for b in rig.data.bones},
        'method': 'Complete source global rotations with fixed M07 segment lengths; common navigation travel removed once; explicit anatomical elbow frame and forearm/wrist roll; original M07 choreography.',
        'source_provenance': {k: {n: v[n] for n in ('source', 'action', 'source_fps', 'source_duration', 'object_matrix_world')} for k, v in sources.items()},
        'animation_license': {
            'Walk_Idle': 'Installed Epic UE mannequin template, project-local adaptation; not CC0 and not redistributable as standalone library assets.',
            'Dizzy_Fall_GetUp_ProneGetUp': 'CC0-1.0 Mesh2Motion source, retained project-fitted Nurse references',
            'control_source_manifest': str(ROOT.parent/'HumanoidKnockdown20260926/source_manifest.json'),
            'control_license': str(ROOT.parent/'HumanoidKnockdown20260926/LICENSE-CC0.MD')},
        'gait_adaptation': {'target_leg_length_ratio': maker.leg_ratio,
            'source_common_travel_m': list(maker.walk_travel),
            'source_ball_fore_aft_range_m': maker.walk_range,
            'source_navigation_distance_m': maker.walk_navigation_distance,
            'slow_speed_cm_s': 90, 'chase_speed_cm_s': 145,
            'foot_reference': 'Ball pivot tracks and source foot/toe roll; no whole-body lowest-vertex lift'},
        'import': {'axis_forward': '-Y', 'axis_up': 'Z', 'apply_unit_scale': True,
            'apply_scale_options': 'FBX_SCALE_UNITS', 'ue_convert_scene': True,
            'ue_convert_scene_unit': True, 'ue_import_uniform_scale': 1,
            'ue_preserve_local_transform': True, 'ue_import_mesh': False,
            'ue_skeleton': '/Game/Monsters/BlindSupplicantM07/SK_M07_Skeleton'},
        'clips': {}, 'tested': False, 'rendered': False, 'cloth_simulation_played': False,
        'user_visual_acceptance': False,
        'limitations': ['M07 is a new body/weight/animation candidate; prior Witch approval does not establish M07 quality.',
            'Chase is an adapted brisk walking gait with both feet periodically supported, not a running mocap.',
            'All source actions and FBXs are authored; game animation blending, Chaos and visual quality await user testing.']}
    actions = {}
    for role, requested_duration, loop, impact in ROLES:
        count = round(requested_duration*FPS)+1
        duration = (count-1)/FPS
        scene.frame_start, scene.frame_end = 1, count
        action = bpy.data.actions.new('A_M07_'+role)
        action.use_fake_user = True
        activate(rig, action)
        actions[role] = action
        previous = {}
        foot_points = {side: [] for side in ('l', 'r')}
        contacts = {side: [] for side in ('l', 'r')}
        speed = 90 if role == 'SlowWalk' else 145 if role == 'Chase' else 0
        stride = speed/100*duration
        for i in range(count):
            scene.frame_set(i+1)
            t, u = i/FPS, i/(count-1)
            phase = 2*math.pi*u
            maker.reset()
            raw = None
            donor = sources['Idle']
            sample_phase = u
            if role in ('SlowWalk', 'Chase'):
                donor = sources['Walk']
            elif role in ('Dizzy', 'Fall', 'GetUp', 'ProneGetUp'):
                donor = sources[role]
            elif role == 'Death':
                donor = sources['Fall']
                sample_phase = ramp(t, .10, 1.26)
            raw = sample(donor, sample_phase)
            first_p = donor['samples'][0]['pelvis'].translation
            last_p = donor['samples'][-1]['pelvis'].translation
            if role in ('SlowWalk', 'Chase'):
                common = maker.walk_travel*u
                mean_inplace = maker.walk_mean_pelvis-maker.walk_travel*.5
                sway = raw['pelvis'].translation-common-mean_inplace
                pelvis = rest['pelvis'].translation+Vector((sway.x*maker.leg_ratio,
                    sway.y*maker.leg_ratio, sway.z*maker.leg_ratio)) + Vector((0, 0, -.05))
            elif role in ('Fall', 'Death', 'GetUp', 'ProneGetUp'):
                ratio = maker.chain_ratio('thigh', 'calf', 'foot', donor)
                offset = raw['pelvis'].translation-donor['rest']['pelvis'].translation
                # Preserve the source fall/recovery's anatomical motion, with
                # horizontal origin anchored to its first frame, no floor hack.
                offset.x -= first_p.x-donor['rest']['pelvis'].translation.x
                offset.y -= first_p.y-donor['rest']['pelvis'].translation.y
                pelvis = rest['pelvis'].translation+offset*ratio
                if role in ('GetUp', 'ProneGetUp'):
                    end_offset = last_p-donor['rest']['pelvis'].translation
                    pelvis.z -= end_offset.z*ratio*ramp(t, duration-.3, duration)
            else:
                offset = raw['pelvis'].translation-first_p.lerp(last_p, u)
                pelvis = rest['pelvis'].translation + offset*maker.leg_ratio + Vector((0, 0, -.035))
            maker.retarget(donor, raw, pelvis)
            if role not in ('Fall', 'Death', 'GetUp', 'ProneGetUp'):
                for n, degrees in (('spine_02', 1.5), ('spine_04', 2), ('neck_01', 3), ('head', 4)):
                    rotate(rig, n, Vector((1, 0, 0)), degrees)
            elif role in ('GetUp', 'ProneGetUp'):
                rotate(rig, 'head', Vector((1, 0, 0)), 4*ramp(t, duration-.4, duration))
            finger_amount = .9
            attack_effort = 0
            recoil = 0
            listening = 0
            if role.startswith('Melee'):
                sign = 1 if role == 'MeleeLeft' else -1
                wind = ramp(t, .07, impact-.24)
                strike = ramp(t, impact-.24, impact)
                recover = ramp(t, impact+.18, duration)
                attack_effort = wind*(1-recover)
                rotate(rig, 'spine_03', UP, sign*(8*wind-17*strike)*(1-recover))
                rotate(rig, 'spine_04', Vector((1, 0, 0)), 5*strike*(1-recover))
                p = world(rig, 'pelvis')
                p.translation += Vector((0, -.055*strike, -.022*wind))*(1-recover)
                put(rig, 'pelvis', p)
                finger_amount = .9+.9*attack_effort
            elif role == 'Hit':
                recoil = ramp(t, 0, .16)*(1-ramp(t, .29, duration))
                rotate(rig, 'spine_02', Vector((1, 0, 0)), -7*recoil)
                rotate(rig, 'spine_04', Vector((1, 0, 0)), -8*recoil)
                p = world(rig, 'pelvis')
                p.translation += Vector((0, .035, -.035))*recoil
                put(rig, 'pelvis', p)
            elif role == 'WallListen':
                listening = ramp(t, .12, .9)*(1-ramp(t, 2.4, duration))
                rotate(rig, 'spine_03', UP, -10*listening)
                rotate(rig, 'head', UP, -23*listening)
                rotate(rig, 'neck_01', Vector((0, 1, 0)), -7*listening)
            for side, sign in (('l', 1), ('r', -1)):
                if role in ('SlowWalk', 'Chase'):
                    common = maker.walk_travel*u
                    donor_ball = raw['ball_'+side].translation-common
                    meta = maker.walk_ball[side]
                    # Scale the actual common source travel to the authored
                    # clip travel. Inferring a stride from foot min/max loses
                    # support duty and makes the planted foot outrun navigation.
                    foreaft_scale = stride/max(.01, maker.walk_navigation_distance)
                    ball = rest['ball_'+side].translation.copy()
                    ball.x += (donor_ball.x-meta['mean'].x)*maker.leg_ratio
                    ball.y += (donor_ball.y-meta['mean'].y)*foreaft_scale
                    ball.z += max(0., donor_ball.z-meta['low'])*maker.leg_ratio*(.90 if role == 'SlowWalk' else 1.06)
                    dq = raw['foot_'+side].to_quaternion() @ donor['rest']['foot_'+side].to_quaternion().inverted()
                    foot_q = dq @ rest['foot_'+side].to_quaternion()
                    ankle_to_ball = rest['foot_'+side].to_quaternion().inverted() @ (rest['ball_'+side].translation-rest['foot_'+side].translation)
                    endpoint = ball-foot_q@ankle_to_ball
                    # The toe rotation is retained separately from the ankle;
                    # there is no fixed flat-foot orientation.
                    maker.leg(side, endpoint, foot_q, raw)
                    local_rest = donor['rest']['foot_'+side].to_quaternion().inverted() @ donor['rest']['ball_'+side].to_quaternion()
                    local_pose = raw['foot_'+side].to_quaternion().inverted() @ raw['ball_'+side].to_quaternion()
                    local_delta = local_pose @ local_rest.inverted()
                    rig.pose.bones['ball_'+side].rotation_quaternion = local_delta
                    contacts[side].append(1-smooth((donor_ball.z-meta['low']-.015)/.055))
                elif role not in ('Fall', 'Death', 'GetUp', 'ProneGetUp'):
                    maker.leg(side, foot_anchors[side].translation, foot_anchors[side].to_quaternion())
                    contacts[side].append(1.)
                else:
                    contacts[side].append(0.)
            out_axis, forward, up = maker.torso_axes()
            for side, sign in (('l', 1), ('r', -1)):
                shoulder = world(rig, 'upperarm_'+side).translation.copy()
                total = maker.arm[side]['l1']+maker.arm[side]['l2']
                lag = math.sin(phase+(.3 if side == 'l' else math.pi+.3))
                goal = shoulder + out_axis*(sign*.075) + forward*.065 - up*(total*.958)
                pole = shoulder+out_axis*(sign*.22)+forward*.11-up*(total*.48)
                if role in ('SlowWalk', 'Chase'):
                    src = raw['hand_'+side].translation-raw['upperarm_'+side].translation
                    src0 = donor['samples'][0]['hand_'+side].translation-donor['samples'][0]['upperarm_'+side].translation
                    src1 = donor['samples'][-1]['hand_'+side].translation-donor['samples'][-1]['upperarm_'+side].translation
                    arm_ratio = maker.chain_ratio('upperarm', 'lowerarm', 'hand', donor)
                    hand_sway = (src-src0.lerp(src1, u))*arm_ratio
                    goal += hand_sway*.38 + forward*(.045*lag)
                    pole += forward*(.025*lag)
                elif role in ('Fall', 'Death', 'GetUp', 'ProneGetUp'):
                    src_arm = raw['hand_'+side].translation-raw['upperarm_'+side].translation
                    source_length = (donor['rest']['lowerarm_'+side].translation-donor['rest']['upperarm_'+side].translation).length+(donor['rest']['hand_'+side].translation-donor['rest']['lowerarm_'+side].translation).length
                    source_goal = shoulder+src_arm*(total/source_length)
                    mix = 1-ramp(t, duration-.33, duration) if role.endswith('GetUp') else ramp(t, .04, .25)
                    goal = goal.lerp(source_goal, mix)
                    donor_elbow = raw['lowerarm_'+side].translation-raw['upperarm_'+side].translation
                    pole = pole.lerp(shoulder+donor_elbow*(total/source_length), mix*.75)
                elif role == 'Dizzy':
                    goal += forward*(.07*lag)+out_axis*(sign*.035*math.sin(phase-.4))
                    pole += forward*(.025*lag)
                elif role.startswith('Melee'):
                    active = 'l' if role == 'MeleeLeft' else 'r'
                    if side == active:
                        keys = [(0, (0,0,0)), (.16, (.05,-.03,.06)),
                            (impact-.24, (.30,-.12,.46)),
                            (impact, (-.20,1.0,.37)),
                            (impact+.14, (-.32,.94,.20)),
                            (duration-.22, (-.04,.12,.035)), (duration, (0,0,0))]
                        v = arc(t, keys)
                        goal += out_axis*(sign*v.x)+forward*v.y+up*v.z
                        pole += forward*(.26*attack_effort)+up*(.10*attack_effort)
                    else:
                        goal -= forward*(.07*attack_effort)
                elif role == 'Hit':
                    goal += out_axis*(sign*.08*recoil)+forward*.09*recoil+up*.13*recoil
                elif role == 'WallListen':
                    goal += forward*.17*listening+up*.10*listening
                else:
                    goal += forward*(.012*lag)+out_axis*(sign*.005*math.sin(phase))
                maker.arm_pose(side, goal, pole, forward, up,
                    wrist_bend=.055*attack_effort if role.startswith('Melee') else .0)
                maker.fingers(side, finger_amount, math.sin(phase+.2*sign))
            maker.gills(u if loop else t/4, 1-ramp(t,.55,1.44) if role == 'Death' else 1)
            for side in ('l', 'r'):
                foot_points[side].append(world(rig, 'ball_'+side).translation.copy())
            for p in maker.ordered:
                q = p.rotation_quaternion.copy()
                if p.name in previous and q.dot(previous[p.name]) < 0:
                    q.negate()
                    p.rotation_quaternion = q
                previous[p.name] = q
                for prop in ('location', 'rotation_quaternion', 'scale'):
                    p.keyframe_insert(data_path=prop, frame=i+1, group=p.name)
        if loop:
            scene.frame_set(1)
            opening = {p.name: p.matrix_basis.copy() for p in maker.ordered}
            scene.frame_set(count)
            for p in maker.ordered:
                p.matrix_basis = opening[p.name]
                for prop in ('location', 'rotation_quaternion', 'scale'):
                    p.keyframe_insert(data_path=prop, frame=count, group=p.name)
        scene.frame_set(1)
        destination = OUT/('A_M07_'+role+'.fbx')
        bpy.ops.export_scene.fbx(filepath=str(destination), use_selection=True,
            object_types={'ARMATURE'}, add_leaf_bones=False, use_armature_deform_only=False,
            armature_nodetype='NULL', bake_anim=True, bake_anim_use_all_bones=True,
            bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
            bake_anim_force_startend_keying=True, bake_anim_step=1,
            bake_anim_simplify_factor=0, axis_forward='-Y', axis_up='Z',
            apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS')
        curves = {}
        for side in ('l', 'r'):
            positions = foot_points[side]
            curves['FootContact_'+side] = contacts[side]
            values = []
            for j in range(count):
                lo, hi = max(0,j-1), min(count-1,j+1)
                # Navigation velocity restores the planted-foot speed domain.
                velocity = (positions[hi]-positions[lo])*FPS/max(1,hi-lo)+FORWARD*(speed/100)
                values.append(velocity.length*100)
            curves['FootSpeed_'+side] = values
        manifest['clips'][role] = {
            'file': str(destination), 'asset': '/Game/Monsters/BlindSupplicantM07/Animations/A_M07_'+role,
            'action': action.name, 'frames': count, 'fps': FPS,
            'duration': duration, 'seconds': duration, 'requested_duration': requested_duration,
            'loop': loop, 'root_motion': False, 'expected_speed_cm_s': speed,
            'stride_cm': stride*100 if speed else None,
            'step_cm': stride*50 if speed else None,
            'impact_seconds': impact, 'impact_frame_zero_based': impact*FPS if impact else None,
            'death_ragdoll_seconds': 1.44 if role == 'Death' else None,
            'bone_tracks': list(rest), 'curves': curves,
            'source': donor['source'] if role in ('SlowWalk','Chase','Dizzy','Fall','GetUp','ProneGetUp','Death') else 'Original M07 choreography using Epic idle body micro-motion and explicit hanging-arm articulation',
            'source_intent': 'Complete mature walking gait, retimed and long-limb fitted' if speed else 'Project-local control source retargeted with M07 arm correction' if role in ('Dizzy','Fall','GetUp','ProneGetUp','Death') else 'Custom M07 action; no mocap acceptance claim'}
        (OUT/'motion_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
        print('M07_V03_EXPORTED '+role+' '+str(duration)+'s',flush=True)
    activate(rig, actions['Idle'])
    scene.frame_start, scene.frame_end = 1, 121
    scene.frame_set(1)
    rig['motion_revision'] = 'V03 full-body gait and anatomical arms'
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M07_Motion_V03.blend'))
    manifest['source_saved'] = True
    manifest['animation_fbx_exported'] = True
    (OUT/'motion_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print('M07_V03_SOURCE_SAVED '+str(OUT/'M07_Motion_V03.blend'),flush=True)


if __name__ == '__main__':
    author()
