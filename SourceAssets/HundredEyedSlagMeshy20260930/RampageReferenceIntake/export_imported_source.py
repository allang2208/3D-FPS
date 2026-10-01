"""Extract actual Rampage FBX and full joint motion from the existing editor."""
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
BASE = '/Game/ParagonRampage/Characters/Heroes/Rampage'
mesh = u.load_asset(BASE + '/Meshes/Rampage')
component = u.SkeletalMeshComponent()
component.set_skeletal_mesh_asset(mesh)
all_bones = [str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
bones = [b for b in all_bones if any(b.startswith(p) for p in
    ('root', 'pelvis', 'spine_', 'neck_', 'head', 'clavicle_', 'upperarm_', 'lowerarm_',
     'hand_', 'pec_muscle_', 'lat_muscle_', 'bicep_muscle_', 'tricep_muscle_',
     'thigh_', 'calf_', 'foot_', 'ball_', 'index_', 'pinky_', 'thumb_'))]
names = ['Idle', 'Idle_Biped', 'Jog_Quad_Fwd', 'Attack_Melee_A', 'Attack_Melee_B',
         'Attack_Melee_C', 'Attack_Biped_Melee_A', 'Attack_Biped_Melee_B',
         'Attack_Biped_Melee_C', 'Ability_RMB_Smash', 'Ability_GroundSmash_Start',
         'Ability_GroundSmash_Loop', 'Ability_GroundSmash_End']
(ROOT / 'source_fbx').mkdir(exist_ok=True)
(ROOT / 'source_motion').mkdir(exist_ok=True)

def export(asset, skeletal=False):
    task = u.AssetExportTask()
    task.object = asset
    task.filename = str(ROOT / 'source_fbx' / (asset.get_name() + '.fbx'))
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    task.exporter = u.SkeletalMeshExporterFBX() if skeletal else u.AnimSequenceExporterFBX()
    task.options = u.FbxExportOption()
    task.options.set_editor_property('export_preview_mesh', False)
    task.options.set_editor_property('level_of_detail', False)
    if not u.Exporter.run_asset_export_task(task):
        raise RuntimeError('Source export failed: ' + asset.get_path_name())
    return task.filename

def transform(t):
    return {'translation_cm': [t.translation.x, t.translation.y, t.translation.z],
            'rotation_xyzw': [t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w],
            'scale': [t.scale3d.x, t.scale3d.y, t.scale3d.z]}

options = u.AnimPoseEvaluationOptions()
options.set_editor_property('evaluation_type', u.AnimDataEvalType.RAW)
options.set_editor_property('optional_skeletal_mesh', mesh)
catalogue = []
for name in names:
    clip = u.load_asset(BASE + '/Animations/' + name)
    if not isinstance(clip, u.AnimSequence):
        continue
    if 'NONE' not in str(clip.get_editor_property('additive_anim_type')):
        continue
    seconds = clip.get_play_length()
    frames = []
    for i in range(round(seconds * 60) + 1):
        t = min(seconds, i / 60.)
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, t, options)
        frames.append({'seconds': t,
            'local': {b: transform(u.AnimPoseExtensions.get_bone_pose(pose, b, u.AnimPoseSpaces.LOCAL)) for b in bones},
            'component': {b: transform(u.AnimPoseExtensions.get_bone_pose(pose, b, u.AnimPoseSpaces.WORLD)) for b in bones}})
    motion = {'asset': clip.get_path_name(), 'mesh': mesh.get_path_name(), 'seconds': seconds,
              'sample_hz': 60, 'parents': {b: str(component.get_parent_bone(b)) for b in bones}, 'frames': frames}
    (ROOT / 'source_motion' / (name + '.json')).write_text(json.dumps(motion), encoding='utf-8')
    path = export(clip)
    catalogue.append({'name': name, 'seconds': seconds, 'fbx': path, 'source': clip.get_path_name()})
    print('RAMPAGE_SOURCE_EXPORTED ' + name, flush=True)
mesh_fbx = export(mesh, skeletal=True)
(ROOT / 'source_catalogue.json').write_text(json.dumps({'mesh': mesh.get_path_name(),
    'mesh_fbx': mesh_fbx, 'clips': catalogue, 'source_listing':
    'https://www.fab.com/listings/0807cf74-08fd-4a33-8c8d-f33c9439fb1f',
    'target_modified': False}, indent=2), encoding='utf-8')
print('RAMPAGE_IMPORTED_SOURCE_EXPORT_COMPLETE', flush=True)
