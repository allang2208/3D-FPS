"""Author only the innkeeper's AnimSequence in the isolated commandlet host."""
import json
import os
import subprocess
from pathlib import Path

import unreal as ue


FOLDER = '/Game/Characters/VillageTavernKeeper'
NAME = 'A_TavernKeeper_Idle'
WORK = Path(os.environ['TAVERN_IDLE_WORK'])


def channels(transform):
    p, q, s = transform.translation, transform.rotation, transform.scale3d
    return [p.x, p.y, p.z, q.x, q.y, q.z, q.w, s.x, s.y, s.z]


def author():
    mesh = ue.load_asset(FOLDER + '/SK_TavernKeeper')
    skeleton = ue.load_asset(FOLDER + '/SK_TavernKeeper_Skeleton')
    if not mesh or not skeleton or mesh.skeleton != skeleton:
        raise RuntimeError('The imported innkeeper and her skeleton are required')
    ref = skeleton.get_reference_pose()
    poses = ue.AnimPoseExtensions
    names = [str(n) for n in poses.get_bone_names(ref)]
    indices = {n: i for i, n in enumerate(names)}
    component = ue.new_object(ue.SkeletalMeshComponent)
    component.set_skeletal_mesh_asset(mesh)
    local = [channels(poses.get_bone_pose(ref, n, ue.AnimPoseSpaces.LOCAL)) for n in names]
    parents = [indices.get(str(component.get_parent_bone(n)), -1) for n in names]
    inputs = WORK / 'reference.json'
    outputs = WORK / 'motion.json'
    inputs.write_text(json.dumps(dict(names=names, parents=parents, reference=local)), encoding='utf-8')
    env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME')}
    subprocess.run([env['TAVERN_IDLE_PYTHON'], '-I', str(Path(__file__).with_name('retarget_idle.py')),
                    str(inputs), str(outputs)], env=env, check=True)
    motion = json.loads(outputs.read_text(encoding='utf-8'))

    factory = ue.AnimSequenceFactory()
    factory.set_editor_property('target_skeleton', skeleton)
    factory.set_editor_property('preview_skeletal_mesh', mesh)
    sequence = ue.AssetToolsHelpers.get_asset_tools().create_asset(NAME, FOLDER, ue.AnimSequence, factory)
    controller = sequence.get_editor_property('controller')
    controller.open_bracket('Retarget the relaxed standing loop to the innkeeper', False)
    try:
        controller.set_frame_rate(ue.FrameRate(motion['rate'], 1), False)
        controller.set_number_of_frames(ue.FrameNumber(motion['frame_count']), False)
        for i, bone in enumerate(names):
            keys = motion['tracks'].get(bone, [local[i]])
            controller.add_bone_curve(bone, False)
            if not controller.set_bone_track_keys(bone, [ue.Vector(*k[:3]) for k in keys],
                    [ue.Quat(*k[3:7]) for k in keys], [ue.Vector(*k[7:]) for k in keys], False):
                raise RuntimeError('Cannot write track ' + bone)
    finally:
        controller.close_bracket(False)
    sequence.set_editor_property('enable_root_motion', False)
    sequence.set_editor_property('force_root_lock', True)
    sequence.set_editor_property('root_motion_root_lock', ue.RootMotionRootLock.REF_POSE)
    sequence.set_editor_property('loop', True)
    if not ue.EditorAssetLibrary.save_loaded_asset(sequence, False):
        raise RuntimeError('Could not save the innkeeper idle')
    (WORK / 'saved.json').write_text(json.dumps(dict(asset=sequence.get_path_name(),
         skeleton=skeleton.get_path_name(), frames=motion['frame_count'], rate=motion['rate'])), encoding='utf-8')
    print('TAVERN_IDLE_SAVED', sequence.get_path_name(), flush=True)


author()
