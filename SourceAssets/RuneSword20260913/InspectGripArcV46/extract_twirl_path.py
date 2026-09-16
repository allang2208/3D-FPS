"""Extract the shipped twirl as a path plus its clock.

``G(t) = inverse(hand_r) x WPN_root`` is the sword as seen from the palm, and
``dG(t) = inverse(G(0.350)) x G(t)`` is the twirl itself: identity before the
spin, identity again after it (the clip returns to the same grip), and one full
turn in between.

Splitting ``dG`` into

    path(u)   the geometric route, u = accumulated spin / 360
    u(t)      the clock that says when each part of the route happens

lets the route that was fitted to the reference be kept while the clock is
rebuilt from the reference's own phase list.  The written JSON is the input for
the V47 authoring step.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

P = Path(__file__).parent
SOURCE = P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend'
FPS = 120.0
CLIP = 'A_RuneSword_Inspect'
SPIN = (0.350, 0.650)

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
action = bpy.data.actions[CLIP]
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]


def sample(frame):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    hand = rig.pose.bones['hand_r'].matrix
    weapon = rig.pose.bones['WPN_root'].matrix
    return hand, weapon, hand.inverted() @ weapon


start = int(SPIN[0] * FPS)
end = int(SPIN[1] * FPS)
_, _, grip0 = sample(start)

frames = list(range(start, end + 1))
deltas = {}
for frame in frames:
    _, _, relative = sample(frame)
    deltas[frame] = grip0.inverted() @ relative

# Unwrap the spin with incremental rotations, so an axis that swings during the
# move cannot flip the sign of the accumulation.
axis_reference = None
mid = frames[len(frames) // 2]
axis_reference = deltas[mid].to_quaternion().to_axis_angle()[0].normalized()
accumulated = 0.0
angles = {start: 0.0}
previous = deltas[start].to_quaternion()
for frame in frames[1:]:
    current = deltas[frame].to_quaternion()
    step = current @ previous.inverted()
    axis, angle = step.to_axis_angle()
    sign = 1.0 if axis.dot(axis_reference) >= 0.0 else -1.0
    accumulated += sign * math.degrees(angle)
    angles[frame] = accumulated
    previous = current

raw = [angles[frame] for frame in frames]
monotone = all(b >= a - 1e-9 for a, b in zip(raw, raw[1:]))
floor_value = -1e9
fixed = []
for value in raw:
    floor_value = max(floor_value, value)
    fixed.append(floor_value)
total = fixed[-1]

entry = {
    'source': str(SOURCE),
    'spin_window_seconds': list(SPIN),
    'fps': FPS,
    'total_spin_deg': round(total, 3),
    'monotone_raw': monotone,
    'max_backstep_deg': round(max(0.0, max(a - b for a, b in zip(raw, raw[1:]))), 3),
    'samples': [],
}
for index, frame in enumerate(frames):
    delta = deltas[frame]
    translation, rotation, _ = delta.decompose()
    if index and rotation.dot(Quaternion(entry['samples'][-1]['q'])) < 0:
        rotation.negate()
    entry['samples'].append({
        'frame': frame,
        'seconds': round(frame / FPS, 6),
        'u': round(fixed[index] / total, 6) if total else 0.0,
        'spin_deg': round(fixed[index], 4),
        'q': [round(v, 8) for v in rotation],
        't': [round(v, 8) for v in translation],
    })

(P / 'twirl_path.json').write_text(json.dumps(entry, indent=2), encoding='utf-8')

print('spin window %.3f-%.3f s, frames %d-%d' % (SPIN[0], SPIN[1], start, end))
print('total spin %.2f deg, monotone raw=%s, max backstep %.3f deg'
      % (total, monotone, entry['max_backstep_deg']))
print('%7s %7s %8s %8s %-26s %-34s' % ('frame', 'sec', 'spin', 'u', 'q (axis*angle)',
                                        't (translation, m)'))
for sample_row in entry['samples']:
    if sample_row['frame'] % 2 == 0:
        print('%7d %7.3f %8.1f %8.3f %-26s %-34s'
              % (sample_row['frame'], sample_row['seconds'], sample_row['spin_deg'],
                 sample_row['u'], sample_row['q'], sample_row['t']))
print('EXTRACT_TWIRL_PATH_DONE')
