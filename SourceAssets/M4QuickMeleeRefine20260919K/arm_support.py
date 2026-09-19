"""Author a connected shoulder/elbow/wrist chain around an unchanged grip.

The shoulder anchors stay behind the camera. Grip reach is solved by moving
the gun and both hands together. Upper and lower segments use a single elbow
hinge plane; only residual forearm pronation is distributed over twist bones. This file produces animation; it does not perform acceptance.
"""
import math
import statistics

import bpy
from mathutils import Matrix, Quaternion, Vector


def closest_angle(angle, reference):
    return angle + 2 * math.pi * round((reference - angle) / (2 * math.pi))


def axial_angle(rotation, axis, reference=0.0):
    angle = 2 * math.atan2(Vector((rotation.x, rotation.y, rotation.z)).dot(axis), rotation.w)
    return closest_angle(angle, reference)


def safe_direction(vector, fallback):
    return vector.normalized() if vector.length > 1e-7 else fallback.normalized()


class ArmSupport:
    def __init__(self, rig, idle):
        self.rig = rig
        self.idle = idle
        self.previous = {side: {'shoulder_roll': 0.0, 'forearm_roll': 0.0, 'pole': 0.0}
                         for side in ('r', 'l')}
        self.stations = self.skin_stations()
        self.parameters = {
            'shoulder_anchors_m': {'r': [0.12, -0.12, -0.14], 'l': [-0.28, -0.14, -0.16]},
            'reach_fraction': {'r': 0.91, 'l': 0.91},
            'maximum_additional_group_retreat_m': 0.0,
            'maximum_additional_group_translation_m': 0.0,
        }
        self.hand_bones = {
            side: {'hand_' + side} | {bone.name for bone in rig.data.bones['hand_' + side].children_recursive}
            for side in ('r', 'l')
        }

    def skin_stations(self):
        """Read the existing mesh's dominant skin regions for authoring."""
        source = {bone.name: bone.matrix.copy() for bone in self.rig.pose.bones}
        segments = {}
        samples = {}
        for side in ('r', 'l'):
            for start, end in (('upperarm', 'lowerarm'), ('lowerarm', 'hand')):
                origin = source[start + '_' + side].translation
                axis = source[end + '_' + side].translation - origin
                for suffix in ('01', '02'):
                    name = f'{start}_twist_{suffix}_{side}'
                    segments[name] = (origin, axis, axis.length_squared)
                    samples[name] = []
        graph = bpy.context.evaluated_depsgraph_get()
        for obj in bpy.data.objects:
            if obj.type != 'MESH' or not any(m.type == 'ARMATURE' and m.object == self.rig for m in obj.modifiers):
                continue
            groups = {g.index: g.name for g in obj.vertex_groups}
            evaluated = obj.evaluated_get(graph)
            mesh = evaluated.to_mesh()
            to_rig = self.rig.matrix_world.inverted() @ evaluated.matrix_world
            try:
                for vertex in mesh.vertices:
                    if not vertex.groups:
                        continue
                    name = groups[max(vertex.groups, key=lambda g: g.weight).group]
                    if name not in segments:
                        continue
                    origin, axis, length_squared = segments[name]
                    samples[name].append((to_rig @ vertex.co - origin).dot(axis) / length_squared)
            finally:
                evaluated.to_mesh_clear()
        stations = {}
        for name, values in samples.items():
            origin, axis, length_squared = segments[name]
            fallback = (source[name].translation - origin).dot(axis) / length_squared
            stations[name] = max(0.05, min(0.97, statistics.median(values) if values else fallback))
        return stations

    def shoulder(self, side, weight):
        start = self.idle['upperarm_' + side].translation
        return start.lerp(Vector(self.parameters['shoulder_anchors_m'][side]), weight)

    def fit_group(self, delta, weight):
        """Project the rigid gun/hand group into both shoulder reach spheres.

        Shoulder positions are inputs, never extended forward to chase the gun.
        Dykstra projection keeps the correction near the authored group pose.
        """
        if weight <= 0:
            return delta
        spheres = []
        for side in ('r', 'l'):
            sh, el, wr = [self.idle[n + '_' + side].translation
                          for n in ('upperarm', 'lowerarm', 'hand')]
            arm_length = (el - sh).length + (wr - el).length
            radius = ((wr - sh).length * (1 - weight)
                      + arm_length * self.parameters['reach_fraction'][side] * weight)
            target = (delta @ self.idle['hand_' + side]).translation
            spheres.append((self.shoulder(side, weight) - target, radius))
        correction = Vector((0, 0, 0))
        residuals = [Vector((0, 0, 0)), Vector((0, 0, 0))]
        for _ in range(32):
            for i, (center, radius) in enumerate(spheres):
                trial = correction + residuals[i]
                relative = trial - center
                projected = center + relative.normalized() * radius if relative.length > radius else trial
                residuals[i] = trial - projected
                correction = projected
        result = delta.copy()
        result.translation += correction
        self.parameters['maximum_additional_group_retreat_m'] = max(
            self.parameters['maximum_additional_group_retreat_m'], -correction.y)
        self.parameters['maximum_additional_group_translation_m'] = max(
            self.parameters['maximum_additional_group_translation_m'], correction.length)
        return result

    @staticmethod
    def segment_frame(axis, normal):
        normal = normal - axis * normal.dot(axis)
        normal.normalize()
        tangent = normal.cross(axis).normalized()
        return Matrix((axis, tangent, normal)).transposed().to_quaternion()

    def apply(self, pose, side, target, weight):
        idle = self.idle
        previous = self.previous[side]
        un, fn, hn, cn = [part + '_' + side for part in ('upperarm', 'lowerarm', 'hand', 'clavicle')]
        sh, el, wr = [idle[name].translation for name in (un, fn, hn)]
        upper_length, lower_length = (el - sh).length, (wr - el).length
        old_upper, old_fore = (el - sh).normalized(), (wr - el).normalized()
        old_normal = old_upper.cross(old_fore).normalized()
        old_upper_frame = self.segment_frame(old_upper, old_normal)
        old_fore_frame = self.segment_frame(old_fore, old_normal)
        shoulder = self.shoulder(side, weight)
        wrist = target.translation
        hand_delta = target @ idle[hn].inverted()
        grip_rotation = hand_delta.to_quaternion()
        desired_fore = grip_rotation @ old_fore
        axis = (wrist - shoulder).normalized()
        distance = max(abs(upper_length - lower_length) + 1e-6, (wrist - shoulder).length)
        along = (upper_length ** 2 - lower_length ** 2 + distance ** 2) / (2 * distance)
        radius = math.sqrt(max(0, upper_length ** 2 - along ** 2))

        # A bounded elbow circle search, with no accumulating pole winding.
        # Start at the source bend, then encourage a low, outward support.
        pole = el - sh
        pole -= axis * pole.dot(axis)
        outside = Vector((1 if side == 'r' else -1, -0.15, -1))
        outside -= axis * outside.dot(axis)
        pole = safe_direction(pole, outside)
        outside = safe_direction(outside, pole)
        base_pole = safe_direction(pole * (1 - 0.65 * weight) + outside * (0.65 * weight), pole)
        cap = math.radians(65) * weight

        def candidate(angle):
            point = shoulder + axis * along + (Quaternion(axis, angle) @ base_pole) * radius
            upper_axis = (point - shoulder).normalized()
            fore_axis = (wrist - point).normalized()
            normal = upper_axis.cross(fore_axis).normalized()
            upper_delta = self.segment_frame(upper_axis, normal) @ old_upper_frame.inverted()
            fore_delta = self.segment_frame(fore_axis, normal) @ old_fore_frame.inverted()
            target_delta = desired_fore.rotation_difference(fore_axis) @ grip_rotation
            twist = axial_angle(target_delta @ fore_delta.inverted(), fore_axis, previous['forearm_roll'])
            wrist_bend = math.acos(max(-1, min(1, desired_fore.dot(fore_axis))))
            # Penalize folding the elbow across its shoulder toward screen
            # center, and encourage continuity during rapid entry/recovery.
            crossing = max(0, (shoulder.x - point.x) * (1 if side == 'r' else -1) - 0.035)
            cost = (wrist_bend ** 2 + 0.65 * twist ** 2 + 0.65 * angle ** 2
                    + 0.20 * (angle - previous['pole']) ** 2 + 45 * crossing ** 2)
            return cost, point, upper_axis, fore_axis, upper_delta, fore_delta, twist

        angles = [-cap + 2 * cap * i / 52 for i in range(53)]
        angle = min(angles, key=lambda a: candidate(a)[0])
        step = cap / 26
        for _ in range(4):
            angle = min((max(-cap, angle - step), angle, min(cap, angle + step)),
                        key=lambda a: candidate(a)[0])
            step *= 0.5
        _, elbow, upper_axis, fore_axis, upper_delta, fore_delta, twist = candidate(angle)
        previous['pole'] = angle
        previous['forearm_roll'] = twist

        # Clavicle and shoulder root remain a rear support. The upper arm is
        # a complete segment with a coherent bend plane (no partial roll).
        pose[cn] = idle[cn].copy()
        pose[cn].translation += shoulder - sh
        pose[un] = Matrix.LocRotScale(shoulder, upper_delta @ idle[un].to_quaternion(), idle[un].to_scale())
        pose[fn] = Matrix.LocRotScale(elbow, fore_delta @ idle[fn].to_quaternion(), idle[fn].to_scale())
        for main, position, delta_rotation, segment_axis, residual in (
                (un, shoulder, upper_delta, upper_axis, 0.0),
                (fn, elbow, fore_delta, fore_axis, twist)):
            part = main.rsplit('_', 1)[0]
            for suffix in ('01', '02'):
                name = f'{part}_twist_{suffix}_{side}'
                location = position + delta_rotation @ (idle[name].translation - idle[main].translation)
                rotation = (Quaternion(segment_axis, residual * self.stations[name])
                            @ delta_rotation @ idle[name].to_quaternion())
                pose[name] = Matrix.LocRotScale(location, rotation, idle[name].to_scale())
        for name in self.hand_bones[side]:
            pose[name] = hand_delta @ idle[name]
        if 'ik_hand_' + side in pose:
            pose['ik_hand_' + side] = target.copy()
