"""Read the requested death-sinking inputs without playback or asset mutation."""
import json
from pathlib import Path
import unreal as u

OUT = Path(__file__).resolve().parent
MESH = '/Game/Monsters/HundredEyedSlag/ArticulationV12/SK_HundredEyedSlag_V12'
PA = '/Game/Monsters/HundredEyedSlag/RagdollGroundV16/PA_HundredEyedSlag_Ground_V16'
mesh = u.load_asset(MESH)
physics = u.load_asset(PA)
clip = u.load_asset('/Game/Monsters/HundredEyedSlag/PolishV2/Animations/A_HundredEyedSlag_Death_V2')
if not all((mesh, physics, clip)):
    raise RuntimeError('Required death assets are unavailable')
api = u.get_default_object(u.PhysicsAssetToolset)
options = u.AnimPoseEvaluationOptions()
options.evaluation_type = u.AnimDataEvalType.SOURCE
options.optional_skeletal_mesh = mesh
options.should_retarget = False
options.extract_root_motion = False

def transform(t):
    return {'position': [t.translation.x, t.translation.y, t.translation.z],
            'rotation': [t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w],
            'scale': [t.scale3d.x, t.scale3d.y, t.scale3d.z]}

rows = {'project': str(Path(u.Paths.project_dir()).resolve()), 'mesh': mesh.get_path_name(),
        'physics': physics.get_path_name(), 'poses': [], 'bodies': [], 'constraints': []}
for time in (0., .42):
    pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, time, options)
    names = u.AnimPoseExtensions.get_bone_names(pose)
    for name in names:
        rows['poses'].append({'time': time, 'bone': str(name),
            'local': transform(u.AnimPoseExtensions.get_bone_pose(pose, name, u.AnimPoseSpaces.LOCAL)),
            'world': transform(u.AnimPoseExtensions.get_bone_pose(pose, name, u.AnimPoseSpaces.WORLD))})
for name in api.call_method('GetBodyNames', (physics,)):
    rows['bodies'].append({'bone': str(name),
        'shapes': [s.export_text() for s in api.call_method('GetBodyShapes', (physics, name))]})
for i in range(30):
    body = u.load_object(None, physics.get_path_name() + ':SkeletalBodySetup_' + str(i))
    if body:
        rows['bodies'].append({'index': i, 'bone': str(body.get_editor_property('bone_name')),
            'physics_type': str(body.get_editor_property('physics_type')),
            'instance': str(body.get_editor_property('default_instance'))})
rows['constraints'] = [c.export_text() for c in api.call_method('GetConstraints', (physics,))]
(OUT / 'death_physics_inputs.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
print('SLAG_V17_INPUTS_READ bones=' + str(len(names)) + ' bodies=' +
      str(len(api.call_method('GetBodyNames', (physics,)))), flush=True)
