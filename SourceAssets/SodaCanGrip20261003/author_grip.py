"""Author a tight can grasp against accepted V7 skin, without gameplay or renders."""
import copy
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = Path(__file__).resolve().parent
V7 = ROOT / 'SourceAssets/ModularOutfit20260925/BarePalmV7'
source = json.loads((V7 / 'M4_original.json').read_text(encoding='utf-8-sig'))
skin = json.loads((V7 / 'Authored/M4.json').read_text(encoding='utf-8-sig'))
bones = source['bones']
names = {bone['index']: name for name, bone in bones.items()}
parent = {name: names.get(bone['parent']) for name, bone in bones.items()}
order = sorted(bones, key=lambda name: bones[name]['index'])

def frame(x, z):
    x = x.normalized()
    z = (z - x * z.dot(x)).normalized()
    return Matrix((x, z.cross(x), z)).transposed()

rest = {}
for name, bone in bones.items():
    matrix = Matrix([Vector(axis).normalized() for axis in bone['axes']]).transposed().to_4x4()
    matrix.translation = Vector(bone['position'])
    rest[name] = matrix
inverse = {name: matrix.inverted() for name, matrix in rest.items()}
local = {name: inverse[parent[name]] @ matrix if parent[name] else matrix
         for name, matrix in rest.items()}
wrist = rest['hand_l'].translation
palm = frame(rest['middle_01_l'].translation - wrist,
    (rest['index_01_l'].translation - wrist).cross(rest['pinky_01_l'].translation - wrist))
hand = (palm.inverted() @ rest['hand_l'].to_3x3()).to_4x4()

def hand_child(name):
    while name:
        if name == 'hand_l':
            return True
        name = parent[name]
    return False

children = [name for name in order if hand_child(name)]
digits = ('index', 'middle', 'ring', 'pinky', 'thumb')
correction, patches = {}, {}
for digit in digits:
    for segment in range(3):
        name = f'{digit}_{segment + 1:02}_l'
        nxt = f'{digit}_{segment + 2:02}_l'
        direction = rest[nxt].translation - rest[name].translation if nxt in rest else (
            rest[name].to_3x3() @ rest[parent[name]].to_3x3().inverted() @
            (rest[name].translation - rest[parent[name]].translation))
        reference = frame(direction, palm.col[2])
        correction[name] = reference.inverted() @ rest[name].to_3x3()
        candidates = []
        for position, weights in zip(skin['positions'], skin['weights']):
            if weights.get(name, 0) < .55 or sum(weights.get(n, 0) for n in children) < .995:
                continue
            point = Vector(position)
            delta = point - rest[name].translation
            along = delta.dot(direction.normalized()) / direction.length
            if .2 < along < .8:
                candidates.append((delta.dot(reference.col[2]), point, weights))
        candidates.sort(key=lambda entry: entry[0], reverse=True)
        patches[name] = [(point, weights) for _, point, weights in candidates[:8]]

parameters = {
    'index': {'spread': [-3, -3, -3], 'flex': [38, 94, 136]},
    'middle': {'spread': [-1, -1, -1], 'flex': [40, 96, 138]},
    'ring': {'spread': [-2, -2, -2], 'flex': [36, 90, 132]},
    'pinky': {'spread': [-3, -3, -3], 'flex': [32, 85, 127]},
    'thumb': {'spread': [-30, -24, -18], 'flex': [14, 42, 70]},
}
baseline = copy.deepcopy(parameters)

def pose():
    goal = {}
    for name in children:
        if name == 'hand_l':
            goal[name] = hand.copy()
            continue
        matrix = goal[parent[name]] @ local[name]
        if name in correction:
            digit, number, _ = name.split('_')
            segment = int(number) - 1
            rotation = (Matrix.Rotation(math.radians(parameters[digit]['spread'][segment]), 3, 'Z') @
                Matrix.Rotation(-math.radians(parameters[digit]['flex'][segment]), 3, 'Y') @ correction[name])
            position = matrix.translation.copy()
            matrix = rotation.to_4x4()
            matrix.translation = position
        goal[name] = matrix
    return {name: matrix @ inverse[name] for name, matrix in goal.items()}

neutral_hand = hand @ inverse['hand_l']
# Palmar skin patches support the can too; fitting finger tips alone can leave
# an apparently closed fist several centimeters away from the actual can.
palm_bins = {}
for position, weights in zip(skin['positions'], skin['weights']):
    if weights.get('hand_l', 0) < .9:
        continue
    point = neutral_hand @ Vector(position)
    if 4.5 < point.x < 8.5 and -2.0 < point.y < 2.0:
        key = (int(point.x * 2), int(point.y * 2))
        if key not in palm_bins or point.z > palm_bins[key].z:
            palm_bins[key] = point
palm_patches = list(palm_bins.values())

bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'SourceAssets/SodaCan20261003/SodaCan_Authored.blend'))
can = bpy.data.objects['SM_SodaCan']
points = [can.matrix_world @ vertex.co * 100 for vertex in can.data.vertices]
low = Vector(tuple(min(point[i] for point in points) for i in range(3)))
high = Vector(tuple(max(point[i] for point in points) for i in range(3)))
contact = (low + high) * .5
object_to_palm = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))
center = Vector((9.0, 0.0, 4.0))
faces = [tuple(polygon.vertices) for polygon in can.data.polygons]

def surface_at():
    return BVHTree.FromPolygons([object_to_palm @ (point - contact) + center for point in points], faces)

surface = surface_at()

def clearance_cost(point, target=.025):
    nearest, normal, _, distance = surface.find_nearest(point)
    signed = (point - nearest).dot(normal)
    return (distance - target)**2 + 24 * min(0, signed - .01)**2

def cost(only=None):
    transforms = pose()
    score = 0.0
    for digit in ((only,) if only else digits):
        for segment in range(3):
            name = f'{digit}_{segment + 1:02}_l'
            samples = patches[name]
            if not samples:
                continue
            for position, weights in samples:
                # Excluded arm weights cannot shrink the sampled finger pad.
                weight_sum = sum(weights.get(n, 0) for n in transforms)
                point = sum((transforms[n] @ position * w for n, w in weights.items()
                             if n in transforms), Vector()) / weight_sum
                score += clearance_cost(point)
        score += .0008 * sum((a - b)**2 for a, b in
            zip(parameters[digit]['flex'], baseline[digit]['flex']))
    if only is None and palm_patches:
        # A palm has curvature; its nearest pad cluster seats on the cylinder
        # without forcing the entire broad, flat palm through the shell.
        pad_costs = sorted(clearance_cost(point) for point in palm_patches)
        score += 4 * sum(pad_costs[:8])
        score += .3 * center.y**2
    return score

def bounded(digit):
    a, b, c = parameters[digit]['flex']
    if digit == 'thumb':
        return 5 <= a <= 40 and 10 <= b - a <= 55 and 10 <= c - b <= 40 and c <= 115
    return 25 <= a <= 75 and 30 <= b - a <= 72 and 10 <= c - b <= 43 and c <= 175

# This is deterministic grip production. No runtime search, gameplay probe,
# skeleton scaling, or tests are added to the use component.
for step in (10., 6., 3., 1.5, .75):
    for _ in range(3):
        for digit in digits:
            for field in ('flex', 'spread'):
                if field == 'spread' and digit != 'thumb':
                    continue
                for segment in range(3):
                    original = parameters[digit][field][segment]
                    best, value = original, cost(digit)
                    for delta in (-step, step):
                        parameters[digit][field][segment] = original + delta
                        spread = parameters[digit]['spread']
                        valid = bounded(digit) if field == 'flex' else (
                            -55 <= original + delta <= 5 and
                            abs(spread[1] - spread[0]) <= 12 and abs(spread[2] - spread[1]) <= 12)
                        if valid:
                            candidate = cost(digit)
                            if candidate < value:
                                best, value = original + delta, candidate
                    parameters[digit][field][segment] = best
        for axis in (0, 2, 1):
            original = center[axis]
            best, value = original, cost()
            for delta in (-step * .025, step * .025):
                center[axis] = original + delta
                if not (6.5 <= center.x <= 10.5 and -.9 <= center.y <= .9 and 2.8 <= center.z <= 4.8):
                    continue
                surface = surface_at()
                candidate = cost()
                if candidate < value:
                    best, value = center[axis], candidate
            center[axis] = best
            surface = surface_at()

profile = {
    'grip_height': round(contact.z, 4),
    'grip_in_palm': [round(value, 4) for value in center],
    'digits': parameters, 'recover_at_release': True,
    'authoring': 'Independent can-body wrap against accepted V7 palmar skin; cumulative phalanx flex angles.',
    'source_hand': str(V7 / 'Authored/M4.json'),
    'source_can': str(ROOT / 'SourceAssets/SodaCan20261003/SodaCan_Authored.blend'),
    'can_dimensions_cm': list(high - low), 'runtime_tested': False,
}
(OUT / 'grip_profile.json').write_text(json.dumps(profile, indent=2) + '\n', encoding='utf-8')
# Read the latest shared data just before publication, updating only this family.
path = ROOT / 'Content/ColdSteelData/potion_use_motion.json'
motion = json.loads(path.read_text(encoding='utf-8-sig'))
family = motion['soda_can']
for field in ('grip_height', 'grip_in_palm', 'digits', 'authoring'):
    family[field] = copy.deepcopy(profile[field])
family['times']['recover'] = family['times']['release']
path.write_text(json.dumps(motion, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('SODA_GRIP_AUTHORED_AND_PUBLISHED ' + json.dumps({field: profile[field]
      for field in ('grip_in_palm', 'digits')}))
