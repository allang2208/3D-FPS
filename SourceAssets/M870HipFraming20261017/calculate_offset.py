"""Bake a rigid M870 hip offset from the current saved SUPER90 idle reference."""
import json
import math
from pathlib import Path

root = Path(__file__).parent
inputs = json.loads((root / 'calibration_inputs.json').read_text(encoding='utf-8'))

def add(a, b): return [x + y for x, y in zip(a, b)]
def sub(a, b): return [x - y for x, y in zip(a, b)]
def mul(a, s): return [x * s for x in a]
def dot(a, b): return sum(x * y for x, y in zip(a, b))
def cross(a, b): return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
def norm(a): return mul(a, 1 / math.sqrt(dot(a, a)))
def rotate(q, p):
    t = mul(cross(q[:3], p), 2)
    return add(p, add(mul(t, q[3]), cross(q[:3], t)))
def yaw90(p): return [-p[1], p[0], p[2]]
def frame(bones, up):
    x = norm(sub(bones['WPN_FrontSight']['p'], bones['WPN_RearSight']['p']))
    y = norm(cross(rotate(bones['WPN_root']['q_xyzw'], up), x))
    return [x, y, cross(x, y)]

bones = {k: v['bones'] for k, v in inputs['clips'].items()}
target_axes = [yaw90(a) for a in frame(bones['m4'], [0, 0, 1])]
target_hand = add(add([0, 7, -7], yaw90(bones['m4']['hand_r']['p'])), [6, 0, 0])

def rear_in_camera(name):
    axes = frame(bones[name], [0, -1, 0])
    local = sub(bones[name]['WPN_RearSight']['p'], bones[name]['hand_r']['p'])
    offset = [sum(target_axes[i][j] * dot(axes[i], local) for i in range(3)) for j in range(3)]
    return add(target_hand, offset)

reference, previous = rear_in_camera('super90'), rear_in_camera('m870')
delta = sub(reference, previous)
record = {
    'weapon': 'ue_m870', 'reference_weapon': 'ue_super90',
    'method': 'Align rear sight position with SUPER90; both already share the M4-derived gun-axis frame.',
    'source': 'saved compressed idle at time zero, scale 1, no grip profile',
    'camera_space': 'centimeters: X forward, Y right, Z up',
    'previous_presentation_offset_cm': [6, 0, 0],
    'delta_cm': delta,
    'presentation_offset_cm': add([6, 0, 0], delta),
    'super90_rear_camera_cm': reference,
    'm870_previous_rear_camera_cm': previous,
    'm870_candidate_rear_camera_cm': add(previous, delta),
    'rigid_assembly': 'weapon, arms and attached parts move together; authored bone poses unchanged',
    'ads': 'existing independent sight calibration and interpolation retained',
    'runtime_tested': False, 'user_visual_accepted': False,
}
(root / 'hip-calibration.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print(json.dumps(record, indent=2))
