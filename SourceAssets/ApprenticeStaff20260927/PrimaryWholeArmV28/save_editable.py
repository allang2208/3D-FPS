"""Save four editable V7 staff smash takes in background Blender; no rendering."""
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

P = Path(__file__).resolve().parent
base = json.loads((P.parent / 'ArmSupportV13/full-pose.json').read_text())
attack = json.loads((P / 'full-pose.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(P.parent / 'ArmSupportV13/Staff_BowBasedGrip_V13.blend'))
bpy.context.preferences.filepaths.save_version = 0
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
scene = bpy.context.scene
FPS = 120
scene.render.fps = FPS
rest = {n: Matrix(m) for n, m in base['rest'].items()}
parent = dict(base['parent'])
names = list(rest)
parent['staff_grip'] = 'hand_r'
names.append('staff_grip')
S = Matrix.Diagonal((1, -1, 1))

def mat(q, p):
    m = q.to_4x4()
    m.translation = Vector(p)
    return m

def convert(m):
    return mat(S @ m.to_3x3() @ S, S @ m.translation * .01)

def mix(a, b, u):
    return mat(a.to_quaternion().slerp(b.to_quaternion(), u).to_matrix(), a.translation.lerp(b.translation, u))

def alpha(segment, t):
    t = max(0., min(1., t))
    if segment == 2:
        return t*t*(2-t)
    if segment == 3:
        return 1-(1-t)**3
    return t*t*t*(t*(t*6-15)+10)

def pose(variant, t):
    clips = [base['poses'][variant][0], *attack['poses'][variant], base['poses'][variant][0]]
    times = [0., *[c['time'] for c in attack['poses'][variant]], 1.]
    segment = next((i for i in range(6) if t <= times[i+1]), 5)
    u = alpha(segment, (t-times[segment])/(times[segment+1]-times[segment]))
    a, b = clips[segment], clips[segment+1]
    world = {n: m.copy() for n, m in rest.items()}
    for n in base['order']:
        lead = .16 if n == 'clavicle_r' else .12 if n == 'upperarm_r' else -.06 if n == 'lowerarm_r' else 0.
        # Match StaffGripPose::BlendLocal, including the inverse mix order when
        # returning to the lower-index carry clip at the end of the action.
        amount = u if segment == 0 else -(1-u) if segment == 5 else 1.
        bone_u = u + lead*amount*math.sin(math.pi*u)
        world[n] = world[parent[n]] @ mix(Matrix(a['local'][n]), Matrix(b['local'][n]), bone_u)
    hand = Matrix(base['variants'][variant]['hand'])
    # Entry/exit correct only the carry presentation offset. Primary contact
    # otherwise comes from the actual articulated arm, with no hand-pivot turn.
    presentation = Vector((0, 4, 0)) * ((1-u) if segment == 0 else u if segment == 5 else 0.)
    for n in base['order']:
        if n.endswith('_r'):
            world[n].translation += presentation
    world['staff_grip'] = world['hand_r'] @ hand.inverted()
    return world

def key_pose(frame, world, previous):
    for n in names:
        bone = rig.pose.bones[n]
        par = parent[n]
        relative = convert(world[par]).inverted() @ convert(world[n]) if par else convert(world[n])
        rest_local = rig.data.bones[par].matrix_local.inverted() @ rig.data.bones[n].matrix_local if par else rig.data.bones[n].matrix_local
        bone.rotation_mode = 'QUATERNION'
        bone.matrix_basis = rest_local.inverted() @ relative
        if n in previous and bone.rotation_quaternion.dot(previous[n]) < 0:
            bone.rotation_quaternion.negate()
        previous[n] = bone.rotation_quaternion.copy()
        for prop in ('location', 'rotation_quaternion', 'scale'):
            bone.keyframe_insert(prop, frame=frame)

actions = []
for variant in attack['poses']:
    action = bpy.data.actions.new('A_Staff_PrimarySmash_V28_' + variant)
    action.use_fake_user = True
    rig.animation_data.action = action
    previous = {}
    for frame in range(61):
        key_pose(frame, pose(variant, frame/60.), previous)
    for layer in action.layers:
        for strip in layer.strips:
            for slot in action.slots:
                channelbag = strip.channelbag(slot)
                if channelbag:
                    for curve in channelbag.fcurves:
                        for key in curve.keyframe_points:
                            key.interpolation = 'LINEAR'
    actions.append(action.name)

# Use the current closed bark/crystal geometry as the editable reference.
mount = bpy.data.objects.get('Staff_Contact')
for obj in list(mount.children):
    bpy.data.objects.remove(obj, do_unlink=True)
with bpy.data.libraries.load(str(P.parent / 'BarkRebuildV21/Staff_NaturalBark_V21.blend'), link=False) as (source, target):
    target.objects = [n for n in source.objects if n in ('SM_Staff_Body', 'SM_Staff_head_crystal_false', 'SM_Staff_grip_lining_false')]
for obj in target.objects:
    scene.collection.objects.link(obj)
    obj.parent = mount
    for vertex in obj.data.vertices:
        vertex.co = (vertex.co - Vector((0, 0, 32))) * .01
rig.animation_data.action = bpy.data.actions[actions[0]]
scene.frame_start, scene.frame_end = 0, 60
scene.timeline_markers.clear()
for name, frame in [('Carry', 0), ('Withdraw_offscreen', 13), ('Behind_shoulder', 24), ('Drive_down', 36), ('Full_follow', 42), ('Elbow_recovery', 49), ('Carry_return', 60)]:
    scene.timeline_markers.new(name, frame=frame)
scene.frame_set(0)
output = P / 'Staff_PrimarySmash_V28.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(output))
(P / 'editable-source.json').write_text(json.dumps({
    'source': output.name, 'actions': actions, 'fps': FPS, 'duration_seconds': .5,
    'runtime': 'StaffGripPose::BlendLocal drives bones; staff contact derived from the same shoulder/elbow FK',
    'dynamic_feedback': 'Actual contact adds 35ms flesh / 45ms world pause and camera impulse at runtime.',
    'ue_import_required': False, 'rendered': False, 'runtime_tested': False,
}, indent=2), encoding='utf-8')
print('STAFF_PRIMARY_V28_EDITABLE_SAVED', str(output), flush=True)
