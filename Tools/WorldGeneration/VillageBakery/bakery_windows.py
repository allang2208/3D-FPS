"""Install the bakery casements using the same replicated interaction as the smithy."""
import unreal as ue

from bakery_shell import window_fittings


def install_windows(actors, site, current, require):
    tag = 'VillageBakery.Window'
    existing = {a.get_actor_label(): a for a in current if tag in map(str,a.tags)}
    keep = ue.AttachmentRule.KEEP_WORLD
    count = 0
    for index, bay in enumerate(window_fittings(), start=1):
        label = 'Village_06_Bakery_Window_%02d' % index
        local = ue.Transform(location=bay['center'],rotation=ue.Rotator(yaw=bay['yaw']),scale=bay['scale'])
        world = ue.MathLibrary.compose_transforms(local,site.get_actor_transform())
        window = existing.pop(label,None)
        if not window:
            window = actors.spawn_actor_from_class(ue.ColdSteelWindow,world.translation,world.rotation.rotator())
            window.set_actor_label(label)
        window.modify()
        window.tags = [tag]
        window.attach_to_actor(site,'None',keep,keep,keep,False)
        window.set_actor_transform(world,False,True)
        window.set_editor_property('use_authored_hinges',True)
        window.set_editor_property('authored_left_hinge',ue.Vector(*bay['left_hinge']))
        window.set_editor_property('authored_right_hinge',ue.Vector(*bay['right_hinge']))
        window.set_editor_property('fixed_swing_direction',1)
        window.set_editor_property('open_angle_degrees',bay['angle'])
        window.set_editor_property('open_seconds',.85)
        meshes = {c.get_name(): c for c in window.get_components_by_class(ue.StaticMeshComponent)}
        for name, part in [('WindowFrame','frame'),('WindowLeafLeft','left'),('WindowLeafRight','right')]:
            meshes[name].modify()
            meshes[name].set_static_mesh(require(bay[part]))
            meshes[name].set_editor_property('receives_decals',False)
        window.call_method('RefreshAuthoredGeometry')
        window.set_actor_hidden_in_game(True)
        window.set_actor_enable_collision(False)
        count += 1
    for retired in existing.values():
        actors.destroy_actor(retired)
    return count
