"""Adapt Blender's stripped Armature container scale to the UE root track.

MeshyV2's imported bind root contains the FBX metre-to-centimetre factor.
UE drops that container scale from animation-only FBX imports. Restore it
on the root track once; keep child translations, timing and rotations intact.
"""
import unreal as u


def match_bind_root_scale(clip, mesh):
    options = u.AnimPoseEvaluationOptions()
    options.set_editor_property('evaluation_type', u.AnimDataEvalType.SOURCE)
    options.set_editor_property('optional_skeletal_mesh', mesh)
    pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, 0., options)
    ref = u.AnimPoseExtensions.get_ref_bone_pose(pose, 'root', u.AnimPoseSpaces.LOCAL)
    first = u.AnimPoseExtensions.get_bone_pose(pose, 'root', u.AnimPoseSpaces.LOCAL)
    target = [ref.scale3d.x, ref.scale3d.y, ref.scale3d.z]
    previous = [first.scale3d.x, first.scale3d.y, first.scale3d.z]
    if min(previous) <= 0. or min(target) <= 0.:
        raise RuntimeError('Invalid Meshy bind/animation root scale')
    factors = [a / b for a, b in zip(target, previous)]
    result = {'before': previous, 'bind': target, 'factor': factors, 'changed': False}
    if max(abs(f - 1.) for f in factors) < 1e-5:
        return result
    # These authored actions are in-place and have a static root scale. A new
    # skeletal convention must not silently receive this import adapter.
    if max(abs(f - 100.) for f in factors) > .01:
        raise RuntimeError('Unexpected Meshy root unit mismatch: ' + str(factors))
    model = clip.get_editor_property('data_model_interface')
    count = model.get_number_of_keys()
    positions, rotations, scales = [], [], []
    for i in range(count):
        at = clip.get_play_length() * i / max(1, count - 1)
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, at, options)
        root = u.AnimPoseExtensions.get_bone_pose(pose, 'root', u.AnimPoseSpaces.LOCAL)
        values = [root.scale3d.x, root.scale3d.y, root.scale3d.z]
        if max(abs(a-b) for a,b in zip(values, previous)) > 1e-5:
            raise RuntimeError('Authored animated root scaling needs explicit adaptation')
        positions.append(root.translation)
        rotations.append(root.rotation)
        scales.append(u.Vector(*target))
    controller = clip.get_editor_property('controller')
    controller.open_bracket('Restore Meshy FBX root unit conversion', False)
    try:
        if not controller.set_bone_track_keys('root', positions, rotations, scales, False):
            raise RuntimeError('Could not repair root track: ' + clip.get_path_name())
    finally:
        controller.close_bracket(False)
    u.EditorAssetLibrary.set_metadata_tag(clip, 'InfectedDog.RootUnits', 'BindRootScaleV1')
    result['changed'] = True
    return result
