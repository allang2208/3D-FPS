"""Move one house out of village-wide instance batches while retaining its original appearance."""
import re

import unreal as ue

from layout_geometry import rotate


def transfer_ruin(current, site, expected, shape, *, prefix, loose_furniture=()):
    """A mesh may have several material variants. Transfer its actual saved instances."""
    subs = ue.get_engine_subsystem(ue.SubobjectDataSubsystem)
    helpers = ue.SubobjectDataBlueprintFunctionLibrary
    parent = subs.k2_gather_subobject_data_for_instance(site)[0]
    transfers = []
    for actor in current:
        if not re.match(r'^Village_\d{3,}_', actor.get_actor_label()):
            continue
        for component in actor.get_components_by_class(ue.InstancedStaticMeshComponent):
            mesh = component.static_mesh
            if not mesh:
                continue
            path = mesh.get_path_name().split('.')[0]
            coordinates = expected.get(path, [])
            if not coordinates and path not in loose_furniture:
                continue
            bounds = mesh.get_bounding_box()
            center = (bounds.min+bounds.max)*.5
            selected = []
            for index in reversed(range(component.get_instance_count())):
                pose = component.get_instance_transform(index, True)
                match = next((i for i, point in enumerate(coordinates)
                              if (point - pose.translation).length() < .65), None)
                if match is not None:
                    coordinates.pop(match)
                    selected.append((index, pose))
                elif path in loose_furniture:
                    where = ue.MathLibrary.transform_location(pose, center)
                    dx, dy = rotate(where.x/100-shape['center'][0], where.y/100-shape['center'][1],
                                    -shape['angle'])
                    if abs(dx)<shape['half'][0] and abs(dy)<shape['half'][1] and -15<where.z<315:
                        selected.append((index, pose))
            if selected:
                transfers.append((actor, component, selected))
    missing = {mesh: len(points) for mesh, points in expected.items() if points}
    if missing:
        raise RuntimeError(site.get_actor_label()+' differs from the village source: '+str(missing))

    for actor, original, selected in transfers:
        handle, error = subs.add_new_subobject(ue.AddNewSubobjectParams(
            parent_handle=parent, new_class=ue.HierarchicalInstancedStaticMeshComponent))
        copy = helpers.get_associated_object(helpers.get_data(handle))
        if not copy:
            raise RuntimeError(str(error))
        copy.set_mobility(ue.ComponentMobility.STATIC)
        copy.set_relative_transform(ue.Transform(), False, True)
        copy.set_static_mesh(original.static_mesh)
        for index, mat in enumerate(original.get_materials()):
            if mat:
                copy.set_material(index, mat)
        copy.set_collision_profile_name(original.get_collision_profile_name())
        copy.set_collision_enabled(original.get_collision_enabled())
        copy.set_editor_property('receives_decals', original.get_editor_property('receives_decals'))
        tags = list(original.get_editor_property('component_tags')) + [prefix+'.Ruin']
        if original.get_collision_enabled() != ue.CollisionEnabled.NO_COLLISION:
            tags.extend([prefix+'.Solid', 'HillsStaticSupport'])
        copy.set_editor_property('component_tags', tags)
        copy.add_instances([transform for _, transform in selected], False, True, False)
        actor.modify()
        original.modify()
        for index, _ in selected:
            if not original.remove_instance(index):
                raise RuntimeError('Could not transfer instance ' + actor.get_actor_label())
    return sum(len(rows) for _, _, rows in transfers)
