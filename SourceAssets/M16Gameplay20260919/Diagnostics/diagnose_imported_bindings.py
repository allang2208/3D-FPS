"""Read the imported M16 reference/animation poses for the reported part rotation defect."""
import json
import math
from pathlib import Path
import unreal as u

directory = Path(__file__).parent
imported = json.loads((directory.parent / 'import_result.json').read_text())
mesh = u.load_asset(imported['mesh'])
extension = u.AnimPoseExtensions
reference = extension.get_reference_pose(mesh.skeleton)
new_bones = ['WPN_ChargingHandleLatch', 'WPN_MagazineRelease', 'WPN_EjectionPortCover',
             'WPN_M16Stock', 'WPN_M16Grip', 'WPN_M16Handguard', 'WPN_M16Muzzle']
fixed_bones = new_bones[3:]
bone_names = {str(name) for name in extension.get_bone_names(reference)}
missing = set(new_bones) - bone_names
if missing:
    raise RuntimeError('Missing M16 bones: ' + str(missing))

def transform_data(transform):
    p, q, s = transform.translation, transform.rotation, transform.scale3d
    return {'translation': [p.x, p.y, p.z], 'rotation': [q.x, q.y, q.z, q.w],
            'scale': [s.x, s.y, s.z]}

def angle(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    length = math.sqrt(sum(x*x for x in a) * sum(x*x for x in b))
    return math.degrees(2 * math.acos(min(1.0, abs(dot / length))))

result = {'mesh': mesh.get_path_name(), 'skeleton': mesh.skeleton.get_path_name(),
          'reference_local': {}, 'clips': {}}
for name in new_bones:
    data = transform_data(extension.get_bone_pose(reference, name, u.AnimPoseSpaces.LOCAL))
    data['rotation_from_identity_degrees'] = angle(data['rotation'], [0, 0, 0, 1])
    result['reference_local'][name] = data

options = u.AnimPoseEvaluationOptions()
options.optional_skeletal_mesh = mesh
options.evaluation_type = u.AnimDataEvalType.COMPRESSED
for name, clip in imported['clips'].items():
    animation = u.load_asset(clip['path'])
    samples = []
    for time in [0.0, animation.get_play_length() * 0.5, animation.get_play_length()]:
        pose = extension.get_anim_pose_at_time(animation, time, options)
        sample = {'time': time, 'fixed_parts': {}}
        for bone in fixed_bones:
            actual = transform_data(extension.get_bone_pose(pose, bone, u.AnimPoseSpaces.LOCAL))
            expected = transform_data(extension.get_ref_bone_pose(pose, bone, u.AnimPoseSpaces.LOCAL))
            sample['fixed_parts'][bone] = {
                'rotation_error_degrees': angle(actual['rotation'], expected['rotation']),
                'translation_error_local': math.dist(actual['translation'], expected['translation']),
                'scale_error': max(abs(a-b) for a,b in zip(actual['scale'], expected['scale']))}
        samples.append(sample)
    result['clips'][name] = samples
result['max_reference_rotation_degrees'] = max(v['rotation_from_identity_degrees'] for v in result['reference_local'].values())
parts = [p for samples in result['clips'].values() for sample in samples for p in sample['fixed_parts'].values()]
result['max_fixed_part_rotation_error_degrees'] = max(p['rotation_error_degrees'] for p in parts)
result['max_fixed_part_translation_error_local'] = max(p['translation_error_local'] for p in parts)
(directory / 'imported-binding-after.json').write_text(json.dumps(result, indent=2))
u.log('M16_IMPORTED_BINDINGS ' + json.dumps({k:v for k,v in result.items() if k.startswith('max_')}))
