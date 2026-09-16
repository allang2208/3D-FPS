"""A contact-driven model of the reference twirl, in rig space.

The reference study measured the hilt's image-plane direction on every native
frame, so the twirl's *phase* is known rather than guessed:

    76.000 s  -97.4 deg ... 76.200 s  -285.0 deg ... 76.300 s  -475.8 deg

That is a 378 deg screen sweep in 0.300 s, fastest while the hilt passes close
to the camera (the study called it "剑柄向右上近镜头通过"), and the hilt's
projected length shortens to about half there, so the sweep plane is tilted
out of the image plane instead of being flat against it.

The model therefore rotates the sword about one axis, fixed in the hand's
frame, that is tilted by ``tilt`` degrees away from the camera axis toward the
mid-sweep screen direction, pivoting on a point of the hilt that sits in the
palm.  Because the pivot is on the hilt, the hilt always passes through the
contact point; because the pivot is fixed in the hand, the sword never leaves
the hand; and because the swing stays in front of the camera, the blade cannot
cross the near plane the way a flat in-image rotation with a long blade can.

The clock is the inverse of the model's own projection: ``psi(t)`` is chosen so
that the hilt's projected direction equals the reference's measured one at
every reference frame.
"""
import json, math
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

P = Path(__file__).parent
ANNOTATIONS = P.parent / 'ReferenceReplicaV36/reference_annotations.json'
CAMERA_FORWARD = Vector((0.0, 1.0, 0.0))
SPIN = (0.350, 0.650)


def reference_profile():
    """Measured hilt image direction per native frame, unwrapped."""
    data = json.loads(ANNOTATIONS.read_text(encoding='utf-8'))
    rows = []
    for record in data['records'][:10]:
        guard = record['guard']
        pommel = record['pommel']
        dx = pommel[0] - guard[0]
        dy = pommel[1] - guard[1]
        rows.append({'video_seconds': record['video_seconds'],
                     'angle_deg': math.degrees(math.atan2(-dy, dx)),
                     'length_px': math.hypot(dx, dy),
                     'observation': record['observation']})
    offset = 0.0
    previous = None
    for row in rows:
        if previous is not None:
            while row['angle_deg'] + offset - previous > 180.0:
                offset -= 360.0
            while row['angle_deg'] + offset - previous < -180.0:
                offset += 360.0
        row['angle_unwrapped_deg'] = row['angle_deg'] + offset
        previous = row['angle_unwrapped_deg']
    return rows


def clip_seconds(row):
    """Video 76.000 s maps to clip 0.350 s, one to one."""
    return SPIN[0] + (row['video_seconds'] - 76.0)


def mid_sweep_direction(rows):
    """Image-plane unit vector of the direction the hilt passes the camera at."""
    angles = [row['angle_unwrapped_deg'] for row in rows]
    middle = 0.5 * (min(angles) + max(angles))
    return Vector((math.cos(math.radians(middle)), 0.0, math.sin(math.radians(middle))))


def sweep_axis(tilt_degrees, rows):
    """Axis in world space: camera forward tilted toward the mid-sweep direction."""
    tilt = math.radians(tilt_degrees)
    direction = mid_sweep_direction(rows)
    return (math.cos(tilt) * CAMERA_FORWARD - math.sin(tilt) * direction).normalized()


def image_angle(direction):
    """Screen direction of a world vector: x right, z up, in degrees."""
    if direction.y <= 1e-9 and abs(direction.y) < 1e-9:
        return None
    return math.degrees(math.atan2(direction.z, direction.x))


def screen_sweep(axis, start_direction, steps=1440):
    """Table of (psi_deg, unwrapped screen angle) for a full turn about ``axis``."""
    table = []
    offset = 0.0
    previous = None
    for index in range(steps + 1):
        psi = 360.0 * index / steps
        direction = Quaternion(axis, math.radians(psi)) @ start_direction
        angle = image_angle(direction)
        if angle is None:
            continue
        if previous is not None:
            while angle + offset - previous > 180.0:
                offset -= 360.0
            while angle + offset - previous < -180.0:
                offset += 360.0
        value = angle + offset
        table.append((psi, value))
        previous = value
    return table


def psi_for_screen(table, target, reverse):
    """Rotation angle whose screen angle equals ``target`` (linear search)."""
    if reverse:
        table = [(psi, -value) for psi, value in table]
        target = -target
    first = table[0][1]
    for (psi_a, value_a), (psi_b, value_b) in zip(table, table[1:]):
        if value_a <= target <= value_b and value_b > value_a:
            weight = (target - value_a) / (value_b - value_a)
            return psi_a + (psi_b - psi_a) * weight
    # Outside the sweep the model cannot reach the target; clamp to the end.
    return table[-1][0] if target > table[-1][1] else table[0][0]


def monotone_cubic(points, value):
    """Fritsch-Carlson monotone interpolation through (x, y) pairs."""
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    count = len(points)
    deltas = [(ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) for i in range(count - 1)]
    slopes = [deltas[0]] + [
        (deltas[i - 1] + deltas[i]) / 2.0 if deltas[i - 1] * deltas[i] > 0 else 0.0
        for i in range(1, count - 1)] + [deltas[-1]]
    for index in range(count - 1):
        if deltas[index] == 0.0:
            slopes[index] = slopes[index + 1] = 0.0
            continue
        alpha = slopes[index] / deltas[index]
        beta = slopes[index + 1] / deltas[index]
        if alpha < 0.0 or beta < 0.0:
            slopes[index] = slopes[index + 1] = 0.0
        elif alpha * alpha + beta * beta > 9.0:
            tau = 3.0 / math.sqrt(alpha * alpha + beta * beta)
            slopes[index] = tau * alpha * deltas[index]
            slopes[index + 1] = tau * beta * deltas[index]
    if value <= xs[0]:
        return ys[0]
    if value >= xs[-1]:
        return ys[-1]
    for index in range(count - 1):
        if xs[index] <= value <= xs[index + 1]:
            h = xs[index + 1] - xs[index]
            t = (value - xs[index]) / h
            t2 = t * t
            t3 = t2 * t
            return ((2 * t3 - 3 * t2 + 1) * ys[index]
                    + (t3 - 2 * t2 + t) * h * slopes[index]
                    + (-2 * t3 + 3 * t2) * ys[index + 1]
                    + (t3 - t2) * h * slopes[index + 1])
    return ys[-1]


def target_screen_angle(rows, seconds):
    points = [(clip_seconds(row), row['angle_unwrapped_deg']) for row in rows]
    return monotone_cubic(points, seconds)


def rotation_about(pivot, axis, degrees):
    rotation = Matrix.Rotation(math.radians(degrees), 4, axis)
    return (Matrix.Translation(pivot) @ rotation
            @ Matrix.Translation(-pivot))


def sword_geometry(rest_matrix, mesh):
    """The sword's central axis and its two real end points, in rest space.

    The extremes have to come from the actual vertices: the mesh is not centred
    on its own local origin, so sampling the local axes would return points
    that are not on the sword at all.
    """
    inverse = rest_matrix.inverted()
    points = [inverse @ (mesh.matrix_world @ vertex.co) for vertex in mesh.data.vertices]
    centre = sum(points, Vector()) / len(points)
    centred = [point - centre for point in points]
    spans = []
    for axis in range(3):
        values = [point[axis] for point in centred]
        spans.append(max(values) - min(values))
    axis_index = spans.index(max(spans))
    direction = Vector((0.0, 0.0, 0.0))
    direction[axis_index] = 1.0
    projections = [point.dot(direction) for point in points]
    low = points[projections.index(min(projections))]
    high = points[projections.index(max(projections))]
    return {'low': low, 'high': high, 'length': (high - low).length,
            'axis': (high - low).normalized(), 'axis_index': axis_index,
            'centre': centre}


def nearest_on_segment(a, b, point):
    """Closest point of segment a-b to ``point``, clamped to the segment."""
    direction = b - a
    length_squared = direction.length_squared
    if length_squared <= 1e-12:
        return a.copy(), 0.0
    t = max(0.0, min(1.0, (point - a).dot(direction) / length_squared))
    return a + direction * t, t
