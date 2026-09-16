"""Evaluate the twirl model at several sweep-plane tilts before authoring.

Reports, per tilt: how far the blade can get from the camera (a negative depth
means the blade crosses the near plane and would be clipped away), how much the
hilt foreshortens, and how well the model's screen sweep can follow the
reference's measured profile.
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

P = Path(__file__).parent
sys.path.insert(0, str(P))
import twirl_model as model

SOURCE = P / 'AzureRunesword_InspectGripArcV46.blend'
FPS = 120.0
CLIP = 'A_RuneSword_Inspect'
TILTS = (0.0, 15.0, 30.0, 45.0, 60.0)

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
mesh = bpy.data.objects['RuneSword_Blade']
action = bpy.data.actions[CLIP]
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]

rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
WPN = 'WPN_root'

geometry = model.sword_geometry(rest[WPN], mesh)
low_point = geometry['low']
high_point = geometry['high']
span = geometry['length']


def pose_at(seconds):
    frame = seconds * FPS
    scene.frame_set(int(frame), subframe=frame - int(frame))
    bpy.context.view_layer.update()
    return {b.name: b.matrix.copy() for b in rig.pose.bones}


start_pose = pose_at(model.SPIN[0])
hand = start_pose['hand_r']
weapon = start_pose[WPN]
grip0 = hand.inverted() @ weapon

# Pick the end nearer the hand as the pommel, then the contact point on the
# real hilt segment nearest the hand's origin.
transform = weapon @ rest[WPN].inverted()
world_low = transform @ low_point
world_high = transform @ high_point
palm = (hand @ Vector((0.0, 0.055, 0.0)))
if (world_low - palm).length <= (world_high - palm).length:
    pommel_local, tip_local = low_point, high_point
else:
    pommel_local, tip_local = high_point, low_point
world_pommel = transform @ pommel_local
world_tip = transform @ tip_local
contact_world, contact_t = model.nearest_on_segment(world_pommel, world_tip, palm)
contact_sword_local = transform.inverted() @ contact_world
contact_hand_local = hand.inverted() @ contact_world

rows = model.reference_profile()
start_direction = (world_pommel - world_tip).normalized()
reference_screen = [row['angle_unwrapped_deg'] for row in rows]

report = {'source': str(SOURCE), 'sword_span_m': round(span, 4),
          'contact_hand_local': [round(v, 4) for v in contact_hand_local],
          'contact_distance_from_palm_m': round(
              (contact_world - palm).length, 4),
          'contact_position_along_sword': round(contact_t, 4),
          'tip_depth_at_start_m': round(world_tip.y, 4),
          'pommel_depth_at_start_m': round(world_pommel.y, 4),
          'reference_profile': rows, 'tilts': {}}

for tilt in TILTS:
    axis_world = model.sweep_axis(tilt, rows)
    axis_hand = (start_pose['hand_r'].to_quaternion().inverted() @ axis_world).normalized()
    table = model.screen_sweep(axis_world, start_direction)
    forward = table[-1][1] > table[0][1]
    sweep = table[-1][1] - table[0][1]
    entry = {'axis_world': [round(v, 4) for v in axis_world],
             'screen_sweep_deg': round(sweep, 1),
             'screen_forward': forward,
             'min_depth_m': None, 'min_depth_seconds': None,
             'foreshorten_min': None, 'follow_error_deg_max': None}
    frames = []
    if abs(sweep) > 1.0:
        for row in rows:
            seconds = model.clip_seconds(row)
            target = row['angle_unwrapped_deg']
            psi = model.psi_for_screen(table, target, not forward)
            frames.append((seconds, psi))
        errors = []
        depths = []
        ratios = []
        for index in range(int(model.SPIN[0] * FPS), int(model.SPIN[1] * FPS) + 1):
            seconds = index / FPS
            if frames:
                xs = [f[0] for f in frames]
                ys = [f[1] for f in frames]
                psi = model.monotone_cubic(list(zip(xs, ys)), seconds)
            else:
                psi = 0.0
            pose = pose_at(seconds)
            hand_matrix = pose['hand_r']
            grip = model.rotation_about(contact_hand_local, axis_hand, psi) @ grip0
            world = hand_matrix @ grip
            full = world @ rest[WPN].inverted()
            pommel_world = full @ pommel_local
            tip_world = full @ tip_local
            depths.append(min(pommel_world.y, tip_world.y))
            view = pommel_world - tip_world
            projected = math.sqrt(max(0.0, view.length_squared - view.y * view.y))
            ratios.append(projected / span)
            direction = view.normalized()
            screen = model.image_angle(direction)
            if screen is not None:
                target = model.target_screen_angle(rows, seconds)
                delta = (screen - target + 180.0) % 360.0 - 180.0
                errors.append(abs(delta))
        entry['min_depth_m'] = round(min(depths), 4)
        entry['min_depth_seconds'] = round(
            (int(model.SPIN[0] * FPS) + depths.index(min(depths))) / FPS, 4)
        entry['foreshorten_min'] = round(min(ratios), 3)
        entry['follow_error_deg_max'] = round(max(errors), 2) if errors else None
    report['tilts'][str(tilt)] = entry
    print('tilt %5.1f  sweep %7.1f deg  min_depth %s m at %s s  '
          'foreshorten_min %s  follow_error %s'
          % (tilt, entry['screen_sweep_deg'], entry['min_depth_m'],
             entry['min_depth_seconds'], entry['foreshorten_min'],
             entry['follow_error_deg_max']))

(P / 'probe_twirl_model.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('sword span %.4f m, contact point in hand frame %s'
      % (span, [round(v, 4) for v in contact_hand_local]))
print('contact is %.4f m from the palm; tip depth %.4f m, pommel depth %.4f m'
      % (report['contact_distance_from_palm_m'], report['tip_depth_at_start_m'],
         report['pommel_depth_at_start_m']))
print('PROBE_TWIRL_MODEL_DONE')

