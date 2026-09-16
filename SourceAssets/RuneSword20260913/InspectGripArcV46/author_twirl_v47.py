"""Author V47: a contact-driven twirl clocked by the reference's own frames.

Three measured defects in the shipped twirl, and what this does about each:

1. No contact.  Tracking the sword in the hand's frame through V42's spin, the
   best-behaved point of the sword still wanders with 13.3 cm RMS and the hilt's
   butt end with 16.6 cm, so the sword slides through the fist instead of
   turning in it.  Here the rotation is anchored on the sword vertex that
   touches the right hand at the spin start, so the contact is exact.
2. A stalled clock.  The relative rotation holds still for 33 ms around 100 deg
   and then fires 70 deg in one frame, exactly where the reference study
   measured the hilt passing the camera at its fastest.  Here the twirl is
   resampled onto that measured curve.
3. The blade crosses the near plane.  The fitted path swings a 1.09 m blade to
   54 deg towards the camera at 0.56 s, which puts its tip 0.41 m behind the
   viewmodel camera.  Here the hilt is held close to the picture plane, so the
   blade sweeps like a propeller instead and never leaves the front.  The
   reference weapon is much shorter, so its mid-sweep tumble towards the viewer
   cannot be reproduced with this blade at this distance; that is stated rather
   than faked.

The hand, the arm, the left hand, the 0.300 s window and every other clip are
untouched, and the spin still ends exactly on the grip it started from.
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

P = Path(__file__).parent
sys.path.insert(0, str(P))
import twirl_model as model

SOURCE = P / 'AzureRunesword_InspectGripArcV46.blend'
OUT = P / 'ExportV47'
OUT.mkdir(exist_ok=True)
FPS = 120.0
CLIP = 'A_RuneSword_Inspect'
WPN = 'WPN_root'
VIEW_AXIS = Vector((0.0, 1.0, 0.0))
# How far out of the picture plane the hilt is allowed to lean while it turns.
# The blade is 1.06 m from the contact point, so this is capped at the angle
# that keeps its tip in front of the camera.
FLAT_LEAN = 0.03

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
arms = bpy.data.objects['SK_Manny_Arms_Export']
sword = bpy.data.objects['RuneSword_Blade']
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
parent = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
local_rest = {n: (rest[parent[n]].inverted() @ rest[n]) if parent[n] else rest[n]
              for n in rest}

source = bpy.data.actions[CLIP]
rig.animation_data.action = source
rig.animation_data.action_slot = source.slots[0]
start, end = map(int, source.frame_range)


def pose_at(seconds):
    frame = seconds * FPS
    scene.frame_set(int(frame), subframe=frame - int(frame))
    bpy.context.view_layer.update()
    return {b.name: b.matrix.copy() for b in rig.pose.bones}


def smoothstep(value):
    value = max(0.0, min(1.0, value))
    return value * value * value * (value * (value * 6.0 - 15.0) + 10.0)


def weight_at(seconds, rise=0.060, fall=0.060):
    """Flattening envelope: zero at both ends of the window, one in the middle."""
    t = seconds - model.SPIN[0]
    span = model.SPIN[1] - model.SPIN[0]
    return smoothstep(t / rise) * (1.0 - smoothstep((t - (span - fall)) / fall))


# --- contact point: the sword vertex touching the right hand at spin start.
start_pose = pose_at(model.SPIN[0])
geometry = model.sword_geometry(rest[WPN], sword)
transform_start = start_pose[WPN] @ rest[WPN].inverted()
right_groups = {group.index for group in arms.vertex_groups
                if group.name.endswith('_r')}
hand_vertices = [vertex.index for vertex in arms.data.vertices
                 if any(group.group in right_groups and group.weight > 0.5
                        for group in vertex.groups)]
depsgraph = bpy.context.evaluated_depsgraph_get()
posed_arms = arms.evaluated_get(depsgraph).to_mesh()
posed_sword = sword.evaluated_get(depsgraph).to_mesh()
arm_points = [arms.matrix_world @ posed_arms.vertices[index].co
              for index in hand_vertices]
sword_points = [sword.matrix_world @ vertex.co for vertex in posed_sword.vertices]
arms.evaluated_get(depsgraph).to_mesh_clear()
sword.evaluated_get(depsgraph).to_mesh_clear()

contact = None
for arm_point in arm_points[::7]:
    for sword_point in sword_points[::3]:
        distance = (arm_point - sword_point).length
        if contact is None or distance < contact[0]:
            contact = (distance, arm_point, sword_point)
contact_distance, contact_arm, contact_sword = contact
contact_hand_local = start_pose['hand_r'].inverted() @ contact_sword
contact_sword_local = transform_start.inverted() @ contact_sword
grip0 = start_pose['hand_r'].inverted() @ start_pose[WPN]
# The hilt direction has to live in the weapon bone's own space, because the
# rotation that is authored here is the bone's rotation.
hilt_local = (rest[WPN].to_3x3().inverted()
              @ (geometry['low'] - geometry['high'])).normalized()
# The contact point in the weapon bone's own space: the grip has to put it back
# on the palm every frame.
contact_bone_local = rest[WPN].inverted() @ contact_sword_local

# --- clock: the reference's measured hilt direction, scaled to one full turn.
reference = model.reference_profile()
reference_points = [(model.clip_seconds(row), row['angle_unwrapped_deg'])
                    for row in reference]
reference_span = reference_points[-1][1] - reference_points[0][1]

# --- sample the source, then rewrite only the weapon bone.
spin_frames = list(range(int(model.SPIN[0] * FPS), int(model.SPIN[1] * FPS) + 1))
poses = {frame: pose_at(frame / FPS) for frame in spin_frames}

baseline = []
for frame in spin_frames:
    pose = poses[frame]
    base_rotation = pose['hand_r'].to_quaternion() @ grip0.to_quaternion()
    direction = base_rotation @ hilt_local
    baseline.append({'seconds': frame / FPS, 'base': base_rotation,
                     'direction': direction,
                     'screen_deg': model.image_angle(direction)})

start_screen = baseline[0]['screen_deg']
end_screen = baseline[-1]['screen_deg']
# The clock has to close on the grip, so the screen sweep is one whole turn;
# the reference's own shape is kept and only its span is scaled.
clock_scale = (end_screen - start_screen - 360.0) / reference_span
clock_points = [(seconds, (angle - reference_points[0][1]) * clock_scale)
                for seconds, angle in reference_points]


def target_screen(seconds):
    return start_screen + model.monotone_cubic(clock_points, seconds)


source.name = 'RETAINED_V46_' + CLIP
source.use_fake_user = True
action = source.copy()
action.name = CLIP
action.use_fake_user = True
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]


def weapon_curves(curve):
    return curve.data_path.startswith('pose.bones["' + WPN + '"].')


# Only the keys inside the spin window are replaced.  Dropping the curves
# outright would leave the weapon frozen at the last spin key for the rest of
# the clip, because an F-curve holds its last value past its end.
window_start, window_end = spin_frames[0], spin_frames[-1]
for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:
                if not weapon_curves(curve):
                    continue
                for key in [point for point in curve.keyframe_points
                            if window_start <= point.co.x <= window_end]:
                    curve.keyframe_points.remove(key)

rows = []
previous_quat = None
for index, frame in enumerate(spin_frames):
    seconds = frame / FPS
    pose = poses[frame]
    entry = baseline[index]
    weight = weight_at(seconds)

    # Hold the hilt near the picture plane: keep its screen direction, remove
    # most of its depth component, and blend that in over the window so the
    # joins with the idle grip stay bit-exact.
    direction = entry['direction']
    flattened = Vector((direction.x, direction.y * (1.0 - weight) + FLAT_LEAN * weight,
                        direction.z))
    if flattened.length < 1e-6:
        flattened = Vector((direction.x, 0.0, direction.z))
    flattened.normalize()
    orient = direction.rotation_difference(flattened) @ entry['base']

    # Screen angle the hand alone produces after flattening, then add the spin.
    screen_now = model.image_angle(orient @ hilt_local)
    if screen_now is None:
        screen_now = target_screen(seconds)
    # A positive rotation about the camera axis lowers the screen angle, so the
    # spin that has to be added is the gap from the target up to the baseline.
    spin = screen_now - target_screen(seconds)
    sword_rotation = Quaternion(VIEW_AXIS, math.radians(spin)) @ orient

    hand_rotation = pose['hand_r'].to_quaternion()
    grip_rotation = hand_rotation.inverted() @ sword_rotation
    grip_translation = (contact_hand_local
                        - grip_rotation @ contact_bone_local)
    grip = Matrix.LocRotScale(grip_translation, grip_rotation, grip0.decompose()[2])
    world = pose['hand_r'] @ grip
    parent_matrix = pose[parent[WPN]]
    local = parent_matrix.inverted() @ world
    loc, quat, scale_value = (local_rest[WPN].inverted() @ local).decompose()
    if previous_quat is not None and quat.dot(previous_quat) < 0:
        quat.negate()
    previous_quat = quat.copy()
    bone = rig.pose.bones[WPN]
    bone.rotation_mode = 'QUATERNION'
    bone.location = loc
    bone.rotation_quaternion = quat
    bone.scale = scale_value
    for channel in ('location', 'rotation_quaternion', 'scale'):
        bone.keyframe_insert(channel, frame=frame, group=WPN)

    if frame % 2 == 0:
        full = world @ rest[WPN].inverted()
        pommel_world = full @ geometry['low']
        tip_world = full @ geometry['high']
        contact_now = pose['hand_r'].inverted() @ (full @ contact_sword_local)
        actual_screen = model.image_angle((pommel_world - tip_world).normalized())
        rows.append({
            'frame': frame, 'seconds': round(seconds, 4), 'weight': round(weight, 3),
            'spin_deg': round(spin, 2),
            'target_screen_deg': round(target_screen(seconds), 2),
            'actual_screen_deg': None if actual_screen is None else round(actual_screen, 2),
            'reference_deg': round(reference_points[0][1] + (
                target_screen(seconds) - start_screen) / clock_scale, 2),
            'tip_depth_m': round(tip_world.y, 4),
            'pommel_depth_m': round(pommel_world.y, 4),
            'contact_drift_m': round((contact_now - contact_hand_local).length, 6),
        })

for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:
                if weapon_curves(curve):
                    for key in curve.keyframe_points:
                        key.interpolation = 'LINEAR'

scene.render.fps = int(FPS)
scene.render.fps_base = 1.0
scene.frame_start, scene.frame_end = start, end
scene.frame_set(start)
bpy.ops.object.select_all(action='DESELECT')
rig.hide_set(False)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.fbx(
    filepath=str(OUT / (CLIP + '.fbx')),
    use_selection=True, object_types={'ARMATURE'},
    axis_forward='-Y', axis_up='Z', add_leaf_bones=False,
    bake_anim=True, bake_anim_use_all_actions=False,
    bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0)

report = {
    'revision': 'InspectTwirlV47',
    'source': str(SOURCE),
    'clip': CLIP, 'seconds': (end - start) / FPS,
    'spin_window_seconds': list(model.SPIN),
    'flat_lean': FLAT_LEAN,
    'contact': {
        'distance_m_at_start': round(contact_distance, 5),
        'arm_point': [round(v, 4) for v in contact_arm],
        'sword_point': [round(v, 4) for v in contact_sword],
        'contact_hand_local': [round(v, 4) for v in contact_hand_local],
        'contact_sword_local': [round(v, 4) for v in contact_sword_local],
    },
    'reference_profile': reference,
    'reference_sweep_deg': round(reference_span, 2),
    'clock_scale': round(clock_scale, 6),
    'samples': rows,
    'max_contact_drift_m': max(row['contact_drift_m'] for row in rows),
    'min_tip_depth_m': min(row['tip_depth_m'] for row in rows),
    'min_pommel_depth_m': min(row['pommel_depth_m'] for row in rows),
    'max_screen_error_deg': max(
        abs((row['actual_screen_deg'] - row['target_screen_deg'] + 540.0) % 360.0 - 180.0)
        for row in rows if row['actual_screen_deg'] is not None),
    'method': ('The twirl is rebuilt as one rotation about the sword vertex that '
               'touches the right hand at the spin start, so the contact is exact. Its '
               'clock is the hilt direction the reference study measured on all ten '
               'native frames of 76.000-76.300 s, scaled so the spin closes on the grip '
               'it started from. The hilt is held near the picture plane (a small lean '
               'is kept) so a 1.09 m blade sweeps instead of crossing the camera; the '
               'reference weapon is much shorter, so its mid-sweep tumble towards the '
               'viewer is not reproduced. Hand, arm, left hand, timing window and every '
               'other clip are untouched.'),
    'testing': 'No gameplay, PIE or acceptance run; user tests.',
}
(P / 'authoring_v47.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'AzureRunesword_InspectTwirlV47.blend'))

print('V47 contact distance at start %.5f m' % contact_distance)
print('V47 contact drift max         %.6f m' % report['max_contact_drift_m'])
print('V47 screen error max          %.2f deg' % report['max_screen_error_deg'])
print('V47 min depth tip %.4f m  pommel %.4f m'
      % (report['min_tip_depth_m'], report['min_pommel_depth_m']))
print('V47 clock scale %.5f (reference sweep %.1f deg)'
      % (clock_scale, reference_span))
print('INSPECT_TWIRL_V47_AUTHORED')
