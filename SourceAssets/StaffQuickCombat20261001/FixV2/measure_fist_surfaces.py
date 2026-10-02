"""Read the actual editable V7 mesh while authoring the requested fist fix.

No frame render, screenshot, UE operation, application preview or game test.
Regions use native skin weights; the reported gaps are mesh surfaces, not
nominal bone tips. The source is opened read-only and is never saved here.
"""
import bpy
import json
import itertools
import copy
import math
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion
from mathutils.bvhtree import BVHTree

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
source = ROOT / 'SourceAssets/ApprenticeStaff20260927/RightCarryV14/Staff_BowBasedGrip_V14.blend'
cases = json.loads((P / 'fist-candidates.json').read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(source))
rig = bpy.data.objects['Staff_V7_BowGrasp_V14']
mesh = bpy.data.objects['Staff_V7_Arms']
rig.animation_data_clear()
for b in rig.pose.bones:
    b.matrix_basis = Matrix.Identity(4)
mesh.data.calc_loop_triangles()
groups = {g.index: g.name for g in mesh.vertex_groups}
digits = ('thumb', 'index', 'middle', 'ring', 'pinky')
regions = {d: set() for d in (*digits, 'palm')}
tip = []
for v in mesh.data.vertices:
    weights = {groups[g.group]: g.weight for g in v.groups}
    for d in digits:
        if sum(w for n, w in weights.items() if n in [f'{d}_{k:02d}_l' for k in range(1, 4)]) > .85:
            regions[d].add(v.index)
    if sum(w for n, w in weights.items() if n == 'hand_l' or (n.endswith('_l') and 'metacarpal' in n)) > .75:
        regions['palm'].add(v.index)
    if weights.get('thumb_03_l', 0.) > .85:
        tip.append(v.index)
faces = {d: [tuple(t.vertices) for t in mesh.data.loop_triangles if all(i in ids for i in t.vertices)]
         for d, ids in regions.items()}
S = Matrix.Diagonal((1., -1., 1.))
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
parents = {b.name: b.parent.name if b.parent else None for b in rig.data.bones}
anatomy = json.loads((ROOT / 'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json').read_text(encoding='utf-8'))['anatomy']['l']
thumb_axis = next(d for d in anatomy['digits'] if d['bone'] == 'thumb_03_l')
native_digits = {d['bone']: d for d in anatomy['digits']}
pad_normal = S @ Vector(thumb_axis['dorsal'])
pad = [i for i in tip if (mesh.data.vertices[i].co - rest['thumb_03_l'].translation).dot(pad_normal) < -.003]
origin = rest['hand_l'].translation
forward = (rest['middle_01_l'].translation - origin).normalized()
radial = rest['index_01_l'].translation - rest['pinky_01_l'].translation
radial = (radial - forward * radial.dot(forward)).normalized()
palmar = forward.cross(radial).normalized()
reference = json.loads((P / 'accepted_fist_profile_reference.json').read_text(encoding='utf-8'))


def frame(forward, normal):
    x = forward.normalized()
    z = (normal - x * normal.dot(x)).normalized()
    return Matrix((x, x.cross(z), z)).transposed()


def axis_dorsal_frame(direction, dorsal):
    x = direction.normalized()
    z = (dorsal - x * dorsal.dot(x)).normalized()
    return Matrix((x, z.cross(x), z)).transposed()


def apply_profile(profile):
    normal = (rest['pinky_01_l'].translation - origin).cross(rest['index_01_l'].translation - origin).normalized()
    palm = frame(forward, normal)
    pose = {n: m.copy() for n, m in rest.items()}
    for n in rest:
        parts = n.split('_')
        if not n.endswith('_l') or parts[0] not in profile:
            continue
        parent = parents[n]
        local = rest[parent].inverted() @ rest[n]
        m = pose[parent] @ local
        if len(parts) == 3 and parts[1].isdigit():
            k = int(parts[1]) - 1
            digit = profile[parts[0]]
            nxt = f'{parts[0]}_{k + 2:02d}_l'
            direction = (rest[nxt].translation - rest[n].translation if nxt in rest else
                         rest[n].to_quaternion() @ (rest[parent].to_quaternion().inverted()
                                                   @ (rest[n].translation - rest[parent].translation)))
            angle = math.radians(digit['spread'][k])
            neutral = frame(palm @ Vector((math.cos(angle), math.sin(angle), 0.)), normal)
            target = Quaternion(neutral.col[1], math.radians(digit['flex'][k])).to_matrix() @ neutral
            q = (target @ frame(direction, normal).inverted() @ rest[n].to_3x3()).to_quaternion()
            if parts[0] == 'thumb' and profile.get('_thumb_nail_outside', False):
                native = native_digits[n]
                desired_dorsal = normal + radial * (.55, .18, 0.)[k]
                q = (axis_dorsal_frame(target.col[0], desired_dorsal)
                     @ axis_dorsal_frame(S @ Vector(native['axis']), S @ Vector(native['dorsal'])).inverted()
                     @ rest[n].to_3x3()).to_quaternion()
            m = Matrix.LocRotScale(m.translation, q, Vector((1., 1., 1.)))
        pose[n] = m
        rig.pose.bones[n].matrix_basis = local.inverted() @ (pose[parent].inverted() @ m)


def measure(name, thumb):
    bpy.context.view_layer.update()
    evaluated = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    surface = evaluated.to_mesh()
    vertices = [evaluated.matrix_world @ v.co for v in surface.vertices]
    evaluated.to_mesh_clear()
    trees = {d: BVHTree.FromPolygons(vertices, f, all_triangles=True) for d, f in faces.items()}
    collisions = {a + '-' + b: len(trees[a].overlap(trees[b])) for a, b in itertools.combinations(trees, 2)}
    gaps, signed, pad_gaps = [], [], []
    for i in tip:
        matches = [trees[d].find_nearest(vertices[i]) for d in ('index', 'middle')]
        nearest = min((m for m in matches if m[0] is not None), key=lambda m: m[3])
        point, normal, _, distance = nearest
        gaps.append(distance * 100.)
        signed.append((vertices[i] - point).dot(normal) * 100.)
        if i in pad:
            pad_gaps.append(distance * 100.)
    gaps.sort()
    pad_gaps.sort()
    centroid = sum((vertices[i] - origin for i in tip), Vector()) / len(tip)
    return {'name': name, 'thumb': thumb, 'crossing_pairs': {k: v for k, v in collisions.items() if v},
            'thumb_tip_to_index_middle_surface_cm': {'minimum': min(gaps), 'p10': gaps[len(gaps) // 10], 'median': gaps[len(gaps) // 2]},
            'thumb_pad_to_index_middle_surface_cm': {'minimum': min(pad_gaps), 'p10': pad_gaps[len(pad_gaps) // 10], 'median': pad_gaps[len(pad_gaps) // 2]},
            'thumb_tip_nearest_surface_signed_cm': {'minimum': min(signed), 'maximum': max(signed)},
            'thumb_tip_centroid_palm_cm': [centroid.dot(v) * 100. for v in (forward, radial, palmar)]}


def convert(m):
    m = Matrix(m)
    out = (S @ m.to_3x3() @ S).to_4x4()
    out.translation = S @ m.translation * .01
    return out


records = []
for case in cases:
    for n, local in case['local'].items():
        b = rig.pose.bones[n]
        r = rig.data.bones[n]
        native = r.parent.matrix_local.inverted() @ r.matrix_local
        b.matrix_basis = native.inverted() @ convert(local)
    records.append(measure(case['name'], case['profile']['thumb']))

# The target is the real distal thumb pad over the exterior of index/middle,
# with positive clearance. Bone-tip proximity alone produced the V1 failure.
def objective(record, profile):
    gap = record['thumb_pad_to_index_middle_surface_cm']
    centroid = record['thumb_tip_centroid_palm_cm']
    change = sum((a - b) ** 2 for channel in ('flex', 'spread')
                 for a, b in zip(profile['thumb'][channel], reference['thumb'][channel]))
    return (sum(record['crossing_pairs'].values()) * 10000.
            + max(0., .06 - gap['minimum']) ** 2 * 300.
            + (gap['p10'] - .22) ** 2 * 18.
            + (gap['median'] - .55) ** 2 * 6.
            + max(0., -centroid[1]) ** 2 * 8.
            + max(0., centroid[1] - 2.0) ** 2 * 8.
            + max(0., 7.3 - centroid[0]) ** 2 * 6.
            + .0008 * change)

best = copy.deepcopy(reference)
best['_thumb_nail_outside'] = True
apply_profile(best)
final = measure('Fitted', best['thumb'])
score = objective(final, best)
bounds = {'flex': [(30., 60.), (6., 42.), (-8., 28.)],
          'spread': [(-24., 8.), (20., 75.), (15., 90.)]}
history = []
for step in (4., 2., 1., .5):
    for _ in range(8):
        changed = False
        for channel in ('spread', 'flex'):
            for index in (2, 1, 0):
                for direction in (-1., 1.):
                    candidate = copy.deepcopy(best)
                    candidate['thumb'][channel][index] += step * direction
                    low, high = bounds[channel][index]
                    if not low <= candidate['thumb'][channel][index] <= high:
                        continue
                    apply_profile(candidate)
                    metric = measure('Candidate', candidate['thumb'])
                    value = objective(metric, candidate)
                    if value < score - .0001:
                        best, score, final = candidate, value, metric
                        history.append({'channel': channel, 'index': index, 'delta': step * direction, 'score': score})
                        changed = True
        if not changed:
            break
    print('V7_FIST_AUTHORING_STAGE', step, score, flush=True)
apply_profile(best)
final = measure('FinalFist', best['thumb'])
(P / 'fist-profile-v2.json').write_text(json.dumps(best, indent=2), encoding='utf-8')
(P / 'fist-authoring-result.json').write_text(json.dumps({'purpose': 'actual V7 surface-constrained authoring, not runtime acceptance',
    'reference': reference, 'profile': best, 'metrics': final, 'changes': history,
    'bone_lengths_changed': False, 'skin_changed': False, 'rendered': False, 'runtime_tested': False}, indent=2), encoding='utf-8')
(P / 'actual-v7-fist-surfaces.json').write_text(json.dumps({'purpose': 'requested repair source diagnosis and authoring',
    'mesh': mesh.name, 'rig': rig.name, 'source': str(source),
    'regions': {d: {'vertices': len(ids), 'triangles': len(faces[d])} for d, ids in regions.items()},
    'cases': records, 'rendered': False, 'runtime_tested': False}, indent=2), encoding='utf-8')
print('V7_FIST_AUTHORING_RESULT', json.dumps(final), flush=True)
