"""Bake a ten-limb ripple gait on the retained rig, UVs and clothed mesh."""
from pathlib import Path
import json
import math
import bpy
from mathutils import Matrix, Vector, Quaternion

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT / 'SourceAssets/BoundCongregateMeshy20261006'
OUT = ROOT / 'LocomotionV2'
OUT.mkdir(exist_ok=True)
settings = json.loads((PROJECT / 'Tools/BoundCongregate/locomotion_v2.json').read_text())
recipe = json.loads((ROOT / 'Authoring/rig_recipe.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'Authoring/BoundCongregate_Clothed_Rig.blend'))
rig = next(ob for ob in bpy.context.scene.objects if ob.type == 'ARMATURE')
scene = bpy.context.scene
scene.render.fps = settings['fps']
duration = settings['duration_seconds']
stance = settings['stance_fraction']
stride = settings['stride_m']
speed_cm = stride / (duration * stance) * 100
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
pose = {}

def point(p):
    return Vector((p[0] * recipe['scale'], p[1] * recipe['scale'], (p[2] - recipe['ground_z']) * recipe['scale']))

def convert(name, matrix, inverse=False):
    bone = rig.data.bones[name]
    kwargs = dict(invert=inverse)
    if bone.parent:
        kwargs.update(parent_matrix=pose[bone.parent.name], parent_matrix_local=rest[bone.parent.name])
    return bone.convert_local_to_pose(matrix, rest[name], **kwargs)

def refresh_pose():
    # Bone collection is parent-first in this authored rig. No evaluated mesh
    # update is needed for each individual IK segment during offline baking.
    for b in rig.data.bones:
        pose[b.name] = convert(b.name, rig.pose.bones[b.name].matrix_basis)

def assign_pose(name, matrix):
    rig.pose.bones[name].matrix_basis = convert(name, matrix, inverse=True)
    pose[name] = matrix.copy()

def rotate_model_axis(name, axis, angle):
    local_axis = rest[name].to_3x3().inverted() @ Vector(axis)
    rig.pose.bones[name].rotation_quaternion = Quaternion(local_axis.normalized(), angle)

def segment(name, head, tail):
    direction = rig.data.bones[name].tail_local - rig.data.bones[name].head_local
    matrix = direction.rotation_difference(tail - head).to_matrix().to_4x4() @ rest[name]
    matrix.translation = head
    assign_pose(name, matrix)

def solve_leg(leg, goal, roll, plant_yaw):
    name = leg['name']
    upper, lower, foot = ['leg_' + name + '_' + part for part in ('upper', 'lower', 'foot')]
    hip, knee, ankle, toe = [point(p) for p in leg['points']]
    parent = rig.data.bones[upper].parent.name
    parent_delta = pose[parent] @ rest[parent].inverted()
    start, old_knee = parent_delta @ hip, parent_delta @ knee
    a, b = (knee - hip).length, (ankle - knee).length
    delta = goal - start
    distance = max(abs(a-b)+.002, min(delta.length, (a+b)*.975))
    direction = delta.normalized()
    pole = old_knee - start
    pole -= direction * pole.dot(direction)
    if pole.length < .001:
        pole = Vector((0, 0, 1)) - direction * direction.z
    x = (a*a - b*b + distance*distance) / (2*distance)
    joint = start + direction*x + pole.normalized()*math.sqrt(max(0, a*a-x*x))
    end = start + direction*distance
    segment(upper, start, joint)
    segment(lower, joint, end)
    toe_direction = Vector((toe.x-ankle.x, toe.y-ankle.y, 0)).normalized()
    axis = Vector((0, 0, 1)).cross(toe_direction)
    matrix = (Quaternion((0,0,1), plant_yaw) @ Quaternion(axis, roll)).to_matrix().to_4x4() @ rest[foot]
    matrix.translation = end
    assign_pose(foot, matrix)

def foot_cycle(phase):
    if phase < stance:
        return .5-phase/stance, 0., 0., 0.
    s = (phase-stance)/(1-stance)
    smooth = s*s*s*(10+s*(-15+6*s))
    # Match the backward stance velocity at both ends of the swing. A small
    # follow-through precedes the lifted forward recovery, with no velocity snap.
    tangent = -(1-stance)/stance
    travel = -.5 + tangent*s + (1-tangent)*smooth
    lift = math.sin(math.pi*s)**2
    return travel, lift, -.24*math.sin(math.tau*s)*math.sin(math.pi*s), s

manifest = dict(revision=settings['revision'], fps=settings['fps'], duration_seconds=duration,
                walk_speed_cm=speed_cm, turn_speed_degrees=settings['turn_speed_degrees'],
                stance_fraction=stance, leg_phase=settings['leg_phase'], clips={}, gameplay_tested=False)
for role in settings['roles']:
    name = 'A_BoundCongregate_' + role + 'V2'
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    rig.animation_data_create()
    rig.animation_data.action = action
    scene.frame_start, scene.frame_end = 1, round(duration*settings['fps'])+1
    for frame in range(scene.frame_start, scene.frame_end+1):
        scene.frame_set(frame)
        phase = (frame-1)/(scene.frame_end-scene.frame_start)
        wave = math.tau*phase
        for pb in rig.pose.bones:
            pb.rotation_mode = 'QUATERNION'
            pb.matrix_basis = Matrix.Identity(4)
        # A low, weighted torso transfers support while the planted hands stay
        # in model-space contact; front and rear masses lag one another.
        body = rig.pose.bones['body']
        offset = Vector((.013*math.sin(wave), .009*math.sin(2*wave-.4),
                         -settings['body_lowering_m']+.018*math.cos(2*wave)))
        body.location = rest['body'].to_3x3().inverted() @ offset
        rotate_model_axis('body', (0,1,0), .022*math.sin(wave-.25))
        rotate_model_axis('body_front', (1,0,0), .021*math.sin(2*wave-.55))
        rotate_model_axis('body_rear', (1,0,0), -.017*math.sin(2*wave-1.05))
        rotate_model_axis('maw', (1,0,0), .014*math.sin(wave-.9))
        for pb in rig.pose.bones:
            prefix = pb.name.split('_')[0]
            if prefix not in ('curl','feeler','scent','grasp'):
                continue
            index = int(pb.name.rsplit('_',1)[1])
            amplitude = {'curl':.025, 'feeler':.040, 'scent':.030, 'grasp':.055}[prefix]
            lag = index*.45 + {'curl':.7, 'feeler':1.1, 'scent':.25, 'grasp':.6}[prefix]
            ax = (rest[pb.name].to_3x3().inverted() @ Vector((1,0,0))).normalized()
            az = (rest[pb.name].to_3x3().inverted() @ Vector((0,0,1))).normalized()
            pb.rotation_quaternion = Quaternion(ax, amplitude*math.sin(wave-lag)) @ Quaternion(az, amplitude*.55*math.sin(2*wave-lag))
        refresh_pose()
        for index, leg in enumerate(recipe['legs']):
            cycle = (phase + settings['leg_phase'][index]) % 1
            travel, lift, roll, swing = foot_cycle(cycle)
            hip, _, ankle, _ = [point(p) for p in leg['points']]
            # Bring extended donor limbs slightly under their load before a
            # stride; keep their individual rest-height and original knee plane.
            goal = ankle + Vector((hip.x-ankle.x, hip.y-ankle.y, 0))*.18
            plant_yaw = 0.
            if role == 'Walk':
                goal.y -= travel*stride
            else:
                angle = math.radians(settings['turn_speed_degrees'])*duration*stance*travel
                if role == 'TurnRight': angle = -angle
                goal = Quaternion((0,0,1), angle) @ goal
                plant_yaw = angle
            goal.z += settings['leg_lift_m'][index]*lift
            goal.x += (-1 if index<5 else 1)*.022*lift
            solve_leg(leg, goal, roll, plant_yaw)
        for pb in rig.pose.bones:
            for channel in ('location','rotation_quaternion','scale'):
                pb.keyframe_insert(channel, frame=frame, group=pb.name)
    # Linear one-frame sampling preserves contact trajectories between the baked
    # keys. The analytic cycle above gives identical first/last poses.
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points: key.interpolation = 'LINEAR'
    scene.frame_set(1)
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    path = OUT / (name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={'ARMATURE'},
        axis_forward='-Y', axis_up='Z', apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
        add_leaf_bones=False, use_armature_deform_only=False, bake_anim=True,
        bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0,
        bake_anim_force_startend_keying=True, path_mode='STRIP')
    manifest['clips'][role] = dict(name=name, file=str(path), frames=scene.frame_end, loop=True, root_motion=False)
    print('AUTHORED', name, flush=True)

rig.animation_data.action = bpy.data.actions['A_BoundCongregate_WalkV2']
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'BoundCongregate_LocomotionV2.blend'))
(OUT/'motion_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
# The native contact solver and the baker consume the same authored schedule.
header = '''#pragma once
// Generated by Tools/BoundCongregate/author_locomotion_v2.py.
namespace BoundCongregateGait
{
inline constexpr float Stance = %.8ff;
inline constexpr float WalkSpeed = %.8ff;
inline constexpr float TurnSpeed = %.8ff;
inline constexpr float PhaseOffsets[10] = {%s};
}
''' % (stance, speed_cm, settings['turn_speed_degrees'], ', '.join('%.8ff'%p for p in settings['leg_phase']))
(PROJECT/'Source/FPSGAME/Monsters/BoundCongregateGait.h').write_text(header, encoding='utf-8')
print('LOCOMOTION_V2_EXPORTED', flush=True)
