"""Run in the UE editor with the sequence's M4 actor selected.

Session-only reference prop; rerun after reopening/respawning the sequence.
Mirrors SetVerticalForegrip in M4VerticalForegrip.cpp. Never commits skeleton edits.
"""
import unreal


def main():
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    candidates = []
    for actor in actors.get_selected_level_actors():
        for comp in actor.get_components_by_class(unreal.SkeletalMeshComponent):
            mesh = comp.get_editor_property('skeletal_mesh_asset')
            if mesh and mesh.get_path_name() == '/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416.SK_M4_FoldingSights_HK416':
                candidates.append(comp)
    if len(candidates) != 1:
        raise RuntimeError('Select the M4 skeletal mesh ACTOR in World Outliner (not a finger control), then rerun.')
    comp = candidates[0]
    mesh = comp.get_editor_property('skeletal_mesh_asset')
    modifier = unreal.SkeletonModifier()
    if not modifier.set_skeletal_mesh(mesh):
        raise RuntimeError('Cannot read M4 reference skeleton.')
    for bone in ('WPN_root', 'WPN_RearSight', 'WPN_FrontSight'):
        if comp.get_bone_index(bone) < 0:
            raise RuntimeError('Missing bone: ' + bone)
    root = modifier.get_bone_transform('WPN_root', True)
    rear = modifier.get_bone_transform('WPN_RearSight', True)
    front = modifier.get_bone_transform('WPN_FrontSight', True)
    forward = (front.translation - rear.translation).normal()
    up = rear.rotation.rotate_vector(unreal.Vector(0, 0, 1))
    mount = unreal.Transform(
        location=rear.translation + forward * 27.0 - up * 8.05,
        rotation=unreal.MathLibrary.make_rot_from_xz(forward, up),
        scale=unreal.Vector(1, 1, 1))
    relative = unreal.MathLibrary.make_relative_transform(mount, root)
    grip_mesh = unreal.load_asset('/Game/Weapons/M4VerticalGripCompact75/SM_VerticalForegrip')
    if not grip_mesh:
        raise RuntimeError('Missing Compact75 grip mesh.')
    label = 'PREVIEW_VerticalGrip_ExactMount'
    previous = [a for a in actors.get_all_level_actors()
                if a.get_actor_label() == label and 'VerticalGripPreviewTool' in [str(t) for t in a.tags]]
    grip = previous[0] if previous else actors.spawn_actor_from_class(
        unreal.StaticMeshActor, unreal.Vector(), transient=True)
    grip.set_actor_label(label)
    grip.set_editor_property('tags', ['VerticalGripPreviewTool'])
    static = grip.static_mesh_component
    static.set_mobility(unreal.ComponentMobility.MOVABLE)
    static.set_static_mesh(grip_mesh)
    static.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    static.set_cast_shadow(False)
    rule = unreal.AttachmentRule.KEEP_RELATIVE
    if not grip.attach_to_component(comp, 'WPN_root', rule, rule, rule, False):
        raise RuntimeError('Grip attachment failed.')
    grip.set_actor_relative_transform(relative, False, True)
    actual = unreal.Transform(location=static.get_editor_property('relative_location'),
                              rotation=static.get_editor_property('relative_rotation'),
                              scale=static.get_editor_property('relative_scale3d'))
    error = (actual.translation - relative.translation).length()
    axes = (unreal.Vector(1, 0, 0), unreal.Vector(0, 1, 0), unreal.Vector(0, 0, 1))
    rotation_error = max((actual.rotation.rotate_vector(axis) - relative.rotation.rotate_vector(axis)).length() for axis in axes)
    scale_error = (actual.scale3d - relative.scale3d).length()
    if error > 0.0001 or rotation_error > 0.00001 or scale_error > 0.00001:
        raise RuntimeError('Relative transform readback mismatch: %s, %s, %s' % (error, rotation_error, scale_error))
    unreal.log('VERTICAL_GRIP_PREVIEW_READY parent=%s bone=WPN_root position_error_cm=%s relative=%s' %
               (comp.get_path_name(), error, relative))
    unreal.log('Session-only preview. Rerun after reopening the sequence. Animation keys are unchanged.')


main()
