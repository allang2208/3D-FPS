"""Compare the twirl's phase between the reference frames and the animation.

The reference study recorded the pommel and guard pixel positions of all 61
native frames (ReferenceReplicaV36/reference_annotations.json), so the hilt's
image-plane direction is a measured ground truth for the phase of the twirl.
The same direction is computed for the animation by projecting the sword's own
tip and pommel through the author camera (origin, +Y forward, 75 deg vertical
FOV, 16:9), which is the camera the reference replica was fitted to.

    76.000 s of video  <->  clip 0.350 s            (V36's time mapping)

Angle sign is chosen so both sequences turn the same way, and both are
unwrapped so a full turn reads as 360 rather than collapsing through zero.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Vector

P = Path(__file__).parent
ANNOTATIONS = P.parent / 'ReferenceReplicaV36/reference_annotations.json'
SOURCES = {
    'v42': P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend',
    'v46': P / 'AzureRunesword_InspectGripArcV46.blend',
}
FPS = 120.0
CLIP = 'A_RuneSword_Inspect'
VIDEO_START = 76.0
CLIP_START = 0.350
IMAGE = (852, 480)
VERTICAL_FOV = math.radians(75.0)


def project(point):
    """Camera at the origin looking down +Y, vertical FOV given, 16:9 frame."""
    width, height = IMAGE
    depth = point.y
    if depth <= 1e-5:
        return None
    tan_v = math.tan(VERTICAL_FOV / 2.0)
    tan_h = tan_v * width / height
    x_ndc = point.x / (depth * tan_h)
    z_ndc = point.z / (depth * tan_v)
    return (width / 2.0 + x_ndc * width / 2.0, height / 2.0 - z_ndc * height / 2.0)


def unwrap(angles):
    out = []
    offset = 0.0
    previous = None
    for angle in angles:
        if previous is not None:
            while angle + offset - previous > 180.0:
                offset -= 360.0
            while angle + offset - previous < -180.0:
                offset += 360.0
        value = angle + offset
        out.append(value)
        previous = value
    return out


def read_reference():
    data = json.loads(ANNOTATIONS.read_text(encoding='utf-8'))
    rows = []
    for record in data['records']:
        guard = Vector(record['guard'] + [0.0])
        pommel = Vector(record['pommel'] + [0.0])
        direction = (pommel - guard)
        angle = math.degrees(math.atan2(-direction.y, direction.x))
        rows.append({'frame': record['frame'], 'video_seconds': record['video_seconds'],
                     'guard': record['guard'], 'pommel': record['pommel'],
                     'angle_deg': angle, 'observation': record['observation']})
    values = unwrap([row['angle_deg'] for row in rows])
    for row, value in zip(rows, values):
        row['angle_unwrapped_deg'] = round(value, 3)
    return rows


def sword_endpoints(rig, mesh):
    """Extreme points of the sword along its own long axis, in WPN_root space."""
    rest = rig.data.bones['WPN_root'].matrix_local
    inverse = rest.inverted()
    local = [inverse @ (mesh.matrix_world @ vertex.co) for vertex in mesh.data.vertices]
    spans = []
    for axis in range(3):
        values = [point[axis] for point in local]
        spans.append((max(values) - min(values), axis, min(values), max(values)))
    span, axis, low, high = max(spans)
    low_point = Vector((0.0, 0.0, 0.0))
    high_point = Vector((0.0, 0.0, 0.0))
    low_point[axis] = low
    high_point[axis] = high
    return {'span_m': round(span, 4), 'axis': axis,
            'low': [round(v, 5) for v in low_point],
            'high': [round(v, 5) for v in high_point]}


def measure_animation(path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene = bpy.context.scene
    rig = bpy.data.objects['SK_RuneSword_Rig']
    mesh = bpy.data.objects['RuneSword_Blade']
    action = bpy.data.actions[CLIP]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    ends = sword_endpoints(rig, mesh)
    low = Vector(ends['low'])
    high = Vector(ends['high'])
    rest = rig.data.bones['WPN_root'].matrix_local
    start, end = map(int, action.frame_range)
    rows = []
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        transform = rig.pose.bones['WPN_root'].matrix @ rest.inverted()
        low_point = project(transform @ low)
        high_point = project(transform @ high)
        if low_point is None or high_point is None:
            continue
        # The end nearer the hand is the pommel end of the hilt.
        hand = rig.pose.bones['hand_r'].matrix.translation
        distance_low = (transform @ low - hand).length
        distance_high = (transform @ high - hand).length
        pommel, other = (low_point, high_point) if distance_low < distance_high \
            else (high_point, low_point)
        direction = Vector((pommel[0] - other[0], other[1] - pommel[1]))
        angle = math.degrees(math.atan2(direction.y, direction.x))
        rows.append({'frame': frame, 'seconds': round(frame / FPS, 4),
                     'angle_deg': angle,
                     'pommel_px': [round(v, 1) for v in pommel],
                     'far_px': [round(v, 1) for v in other]})
    values = unwrap([row['angle_deg'] for row in rows])
    for row, value in zip(rows, values):
        row['angle_unwrapped_deg'] = round(value, 3)
    return ends, rows, start


reference = read_reference()
report = {'reference_source': str(ANNOTATIONS), 'reference': reference, 'animations': {}}
for label, path in SOURCES.items():
    ends, rows, start_frame = measure_animation(path)
    report['animations'][label] = {'source': str(path), 'sword_ends': ends, 'rows': rows}

(P / 'twirl_clock_compare.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

print('reference hilt angle, 76.0-76.7 s:')
print('%6s %8s %10s  %s' % ('frame', 'video', 'angle', 'observation'))
for row in reference[:22]:
    print('%6d %8.4f %10.1f  %s' % (row['frame'], row['video_seconds'],
                                    row['angle_unwrapped_deg'], row['observation'][:34]))
for label, entry in report['animations'].items():
    print('=== %s sword span %.4f m along local axis %d' % (
        label, entry['sword_ends']['span_m'], entry['sword_ends']['axis']))
    print('%6s %8s %10s' % ('frame', 'sec', 'angle'))
    for row in entry['rows']:
        if 0.30 <= row['seconds'] <= 0.72:
            print('%6d %8.3f %10.1f' % (row['frame'], row['seconds'],
                                        row['angle_unwrapped_deg']))
print('TWIRL_CLOCK_DONE')
